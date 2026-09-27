import os
import sqlite3

from flask import current_app, g


def get_db():
    """Return a request-scoped SQLite connection with row access by column name."""
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


TABLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    color TEXT NOT NULL DEFAULT '#4f46e5',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    task_date TEXT NOT NULL,
    task_time TEXT,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL DEFAULT 'MEDIUM',
    status TEXT NOT NULL DEFAULT 'TODO',
    due_date TEXT,
    notes TEXT,
    estimated_hours REAL,
    time_spent_hours REAL,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    meeting_date TEXT NOT NULL,
    meeting_time TEXT,
    title TEXT NOT NULL,
    my_points TEXT,
    meeting_points TEXT,
    decisions TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS email_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    frequency TEXT NOT NULL,
    recipients TEXT NOT NULL DEFAULT '',
    include_status INTEGER NOT NULL DEFAULT 1,
    include_tasks INTEGER NOT NULL DEFAULT 1,
    include_meetings INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 0,
    last_sent_key TEXT,
    last_sent_at TEXT,
    last_attempt_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, frequency),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    recipients TEXT NOT NULL,
    success INTEGER NOT NULL,
    error TEXT,
    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
"""

# Kept separate from TABLES_SCHEMA and applied *after* _migrate(): an index
# on a column added by migration (project_id, time_spent_hours) would fail
# with "no such column" if created in the same pass as CREATE TABLE for a
# database where that table already existed pre-migration.
INDEXES_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_tasks_task_date ON tasks (task_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks (project_id);
CREATE INDEX IF NOT EXISTS idx_meetings_meeting_date ON meetings (meeting_date);
CREATE INDEX IF NOT EXISTS idx_meetings_user_id ON meetings (user_id);
CREATE INDEX IF NOT EXISTS idx_meetings_project_id ON meetings (project_id);
CREATE INDEX IF NOT EXISTS idx_email_log_user_id ON email_log (user_id, sent_at);
"""


def _migrate(conn):
    """Add columns introduced after the initial release, for databases that
    already exist on disk. CREATE TABLE IF NOT EXISTS above never touches an
    existing table, so new columns have to be added explicitly. Safe to
    re-run: each ALTER is guarded by a check against the current schema.
    """
    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "role" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        # The first user created by init_db.py is the original admin login;
        # promote it so an upgraded database still has at least one admin.
        conn.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")

    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "project_id" not in task_columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER REFERENCES projects (id) ON DELETE SET NULL")
    if "time_spent_hours" not in task_columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN time_spent_hours REAL")
    if "estimated_hours" not in task_columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN estimated_hours REAL")

    meeting_columns = {row["name"] for row in conn.execute("PRAGMA table_info(meetings)")}
    if "project_id" not in meeting_columns:
        conn.execute("ALTER TABLE meetings ADD COLUMN project_id INTEGER REFERENCES projects (id) ON DELETE SET NULL")

    conn.commit()


def init_db(app):
    """Create tables/indexes if they do not already exist. Never drops data."""
    db_path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(TABLES_SCHEMA)
        conn.commit()
        _migrate(conn)
        conn.executescript(INDEXES_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)
