# Daily Task & Meeting Tracker

A lightweight, self-hosted web application that replaces an Excel-based daily
task and meeting tracker. Built with Flask and SQLite — fast, simple, and
easy to maintain.

## Features

- **Authentication** — session-based login with hashed passwords (Flask-Login + Werkzeug)
- **Dashboard** — today's summary cards, today's tasks/meetings, task status chart, global date filter
- **Tasks** — full CRUD, priority (Low/Medium/High/Urgent), status (Todo/In Progress/On Hold/Completed/Cancelled), due dates, quick inline status updates (AJAX, no page reload)
- **Meetings** — full CRUD, tracked separately from tasks, with distinct fields for My Points / Meeting Points / Decisions / Notes
- **Search** — partial-match search across titles, descriptions, notes, meeting points, and decisions
- **Date filtering** — reusable presets (Today, This Week, This Month, Last 3/6 Months, This Year, Custom) shared across Dashboard, Tasks, Meetings, and Reports
- **Reports** — summary statistics, task/meeting tables, status chart, for any date range
- **Exports** — Excel (.xlsx, multi-sheet with formatting), CSV (zipped tasks.csv + meetings.csv), PDF (paginated, professionally formatted)
- **Security** — CSRF protection, password hashing, parameterized SQL, output escaping, safe filenames, no stack traces shown to users
- **Responsive UI** — dark sidebar / light content, Bootstrap 5, works on desktop, tablet, and mobile
- **Onboarding tour** — a short guided tour auto-plays on a user's first Dashboard visit; replay anytime via "Take a Tour" in the sidebar
- **Multi-user & roles** — admins can create/deactivate user accounts from a Users page and get read-only oversight of everyone's tasks/meetings/reports; regular users only ever see and edit their own data (see **Multi-user & Roles** below)
- **Projects** — a shared, taggable project list; tag any task or meeting with a project, then filter/report by project everywhere (Tasks, Meetings, Reports, exports)
- **Time tracking** — log hours spent per task; totaled in Reports and included in every export
- **Light/dark theme** — a sidebar toggle switches the whole app (via Bootstrap 5.3's built-in dark mode); the choice is remembered per browser and applied instantly on load with no flash of the wrong theme

## Technology Stack

- **Backend:** Python 3, Flask, Flask-Login, Flask-WTF (CSRF), Werkzeug
- **Database:** SQLite (raw `sqlite3`, no ORM — see Architecture below)
- **Frontend:** HTML5, Bootstrap 5 (CDN), vanilla JavaScript
- **Charts:** Chart.js (CDN)
- **Exports:** openpyxl (Excel), Python `csv` (CSV), ReportLab (PDF)

## Architecture

```
Browser → Flask Routes (routes/) → Service Layer (services/) → SQLite (database.py)
```

- **routes/** — thin controllers: parse the request, call a service, render a template or return JSON
- **services/** — all business logic and SQL lives here (task_service, meeting_service, dashboard_service, report_service, export_service)
- **utils/** — shared helpers: date/period logic (`date_utils.py`), server-side validation (`validators.py`), JSON/response helpers (`helpers.py`)
- **models.py** — `User` (Flask-Login integration) plus the priority/status enums
- **database.py** — connection management + schema (tables, indexes)

Dates are stored as `YYYY-MM-DD` strings, times as `HH:MM`, and "today" is
always computed in the configured timezone (`Asia/Kolkata` by default, see
`utils/date_utils.py`) rather than the server's local time.

Records include a `user_id` so the schema is ready for multiple users, but
the app ships as a single-admin-user tool (see `init_db.py`).

## Project Structure

```
app.py                 Application factory, error handlers, CLI
config.py              Configuration (env-driven)
database.py            SQLite connection + schema
models.py              User model, priority/status constants
init_db.py             Create tables + default admin user
seed_data.py           Optional dev sample data
routes/                auth, dashboard, tasks, meetings, reports
services/               task/meeting/dashboard/report/export logic
utils/                  date_utils, validators, helpers, decorators
templates/              Jinja2 templates (base + per-module)
static/css, static/js   Styles and vanilla JS
tests/                  pytest suite
```

## Running the Application — Step-by-Step Guide

This walks through everything from a bare checkout to a logged-in dashboard.
Every command is run from a terminal, from inside the project folder
(the folder this README is in).

### Step 0: Prerequisites

You need **Python 3.9 or newer**. Check what you have:

```bash
python3 --version
```

If that prints `Python 3.9.x` or higher, you're set. If it's missing or too
old, install Python from [python.org](https://www.python.org/downloads/) (on
Windows, tick "Add Python to PATH" during install) and re-open your
terminal. `pip` (Python's package installer) comes bundled with Python 3.4+,
so you shouldn't need to install it separately.

### Step 1: Open a terminal in the project folder

- **macOS/Linux:** `cd` into the folder, e.g. `cd ~/path/to/daily-tracker`
- **Windows:** open the folder in File Explorer, then right-click inside it
  and choose "Open in Terminal" (or open PowerShell/cmd and `cd` there)

Confirm you're in the right place — you should see `app.py` and
`requirements.txt` when you list the folder (`ls` on macOS/Linux, `dir` on
Windows).

### Step 2: Create a virtual environment

A virtual environment keeps this project's Python packages separate from
everything else on your machine.

```bash
python3 -m venv venv
```

This creates a `venv/` folder inside the project. It only needs to be done
once.

### Step 3: Activate the virtual environment

You need to do this **every time you open a new terminal** to work on the
project (but not again within the same terminal session).

| Platform | Command |
|---|---|
| macOS / Linux (bash/zsh) | `source venv/bin/activate` |
| Windows (Command Prompt) | `venv\Scripts\activate.bat` |
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |

You'll know it worked because your terminal prompt now starts with
`(venv)`. If PowerShell refuses to run the activation script with a
"running scripts is disabled" error, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask and everything else listed in `requirements.txt`
(Flask-Login, Flask-WTF, openpyxl, ReportLab, etc.) into the virtual
environment. It takes a minute or two the first time.

### Step 5: Configure environment variables

```bash
cp .env.example .env            # Windows: copy .env.example .env
```

Open the new `.env` file in any text editor. For trying the app out
locally, the defaults work as-is. Before deploying anywhere real, change
`SECRET_KEY` to a long random value (it signs login sessions and CSRF
tokens) — see the **Configuration** section below for what each variable
does.

### Step 6: Initialize the database

```bash
python init_db.py
```

This creates `instance/database.db`, sets up all the tables and indexes,
and — the first time only — creates a default login:

- **Username:** `admin`
- **Password:** `admin123`

You'll see console output confirming this. The command is **safe to run
again later** (e.g. after pulling an update that adds a new column) — it
never drops or overwrites existing data, it only adds what's missing.

**Change the `admin` password before using this anywhere but your own
machine** — once logged in, go to **Users → edit your own account** and
set a new password there (see **Multi-user & Roles** below).

### Step 7 (optional): Load sample data

```bash
python seed_data.py
```

Adds about 10 sample tasks and 10 sample meetings across different dates,
priorities, and statuses, so the Dashboard, Reports, and charts have
something to show immediately. Skip this if you're setting up for real use
— **never run it against a database you care about**, since it's meant for
trying the app out, not for merging with real records.

### Step 8: Start the application

```bash
python app.py
```

You should see output ending in something like:

```
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

Leave this terminal window open — it's running your server. Closing it (or
pressing `Ctrl+C` in it) stops the application.

### Step 9: Open it in your browser

Go to **http://127.0.0.1:5000** in any modern browser (Chrome, Firefox,
Edge, Safari). You should land on the login page. Sign in with the
`admin` / `admin123` credentials from Step 6.

On your first visit to the Dashboard, a short guided tour highlights the
main areas of the app — you can skip it or replay it anytime via
**"Take a Tour"** at the bottom of the sidebar.

### Step 10: Stop the server when you're done

Go back to the terminal running `python app.py` and press `Ctrl+C`.

### Running it again later

Every time after the first setup, starting the app is just two commands
from the project folder:

```bash
source venv/bin/activate   # Windows: venv\Scripts\activate
python app.py
```

There's no need to repeat Steps 2, 4, 5, or 6 — the virtual environment,
installed packages, `.env` file, and database all persist between runs.

## Configuration

Set via environment variables or `.env` (see `.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session/CSRF signing key | `change-this-value` |
| `DATABASE_PATH` | SQLite file location | `instance/database.db` |
| `TIMEZONE` | IANA timezone for "today" calculations | `Asia/Kolkata` |
| `DEBUG` | Flask debug mode | `True` |
| `MAX_CONTENT_LENGTH` | Max request body size (bytes) | `2097152` (2 MB) |

## Multi-user & Roles

Every user has a `role` of `user` (default) or `admin`. The bootstrap account
created by `init_db.py` is always `admin`; running `init_db.py` against an
existing database also upgrades its schema and promotes the `admin` username
in place, so no data is lost.

- **Regular users** only ever see, search, filter, and export their own
  tasks and meetings. There is no way to reach another user's data.
- **Admins** get an extra **Users** section in the sidebar to create new
  accounts, edit full name/email/role, reset a password, and
  activate/deactivate a login. Deactivated users can no longer log in but
  their historical data is kept (never hard-deleted, since tasks/meetings
  cascade-delete with their owner).
- **Admin oversight is read-only.** On the Tasks, Meetings, and Reports
  pages, admins get an extra "Owner" filter (My Data / All Users / a
  specific person) that adds an Owner column and includes it in exports.
  Viewing another user's record works from any admin session, but editing,
  deleting, or changing its status is still restricted to that record's
  owner — an admin viewing someone else's task/meeting sees a read-only
  detail page with no Edit/Delete controls.
- **Safety guards:** an admin can never deactivate or demote their own
  account (to avoid self-lockout), and the last remaining active admin
  cannot be deactivated or demoted by anyone.

## Projects & Time Tracking

Projects are a **shared taxonomy**, not per-user private data: any logged-in
user can create, edit, and archive a project from the **Projects** page, and
any user can tag their own tasks or meetings with any active project. This
is a deliberate simplicity choice — projects behave like a shared label
list (e.g. "Website Redesign", "Q4 Launch") rather than requiring an admin
to provision them first. Archiving a project (instead of deleting it) keeps
historical tasks/meetings intact; deleting a project outright would need to
either block on existing references or silently detach them, which the
"soft delete" pattern avoids.

Tasks also carry an optional **Time Spent (hours)** field. It's a simple
actual-hours-logged number (not a start/stop timer or an estimate-vs-actual
split) — enter it when you complete or update a task. Reports show a
**Hours Logged** total for the selected date range/project/user scope, and
every export (Excel, CSV, PDF) includes the Project and Hours columns.

### Assigning a task to another user

Admins get an **Assign To** dropdown on the task create/edit form (regular
users never see it — their tasks are always their own). Assigning a task
transfers it completely: it disappears from the assigner's own task list
and appears in the assignee's, fully editable there, exactly like any task
they created themselves. The assigner can still find it afterward through
admin oversight (the "All Users" owner filter on Tasks/Reports), but only
to view it — not to edit it back, since editing stays restricted to the
current owner. The `assigned_user_id` field is validated server-side
against the real user list on every request, so a non-admin cannot assign
a task to someone else by tampering with the form.

### Estimated time and inline time tracking

Tasks have two separate hours fields: **Estimated Time** (set once, on the
create/edit form — a plan) and **Time Spent** (the actual hours logged).
Time Spent can also be updated directly from the Tasks list table via an
inline input next to the status dropdown — no need to open the edit form
for a quick update. Reports show both an "Hours Estimated" and an "Hours
Logged" total, and every export includes both columns.

## Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

The suite covers authentication, task/meeting CRUD, validation, search,
filters, quick status updates, report date-range logic, and all three
export formats.

## Backup

The entire application state lives in one file: `instance/database.db`.
To back up, simply copy that file elsewhere while the app is stopped (or
accept the small risk of copying a live SQLite file — SQLite handles this
safely in WAL-off mode used here). The app never overwrites an existing
backup copy automatically; that is a manual step.

## Troubleshooting

- **"no such table" errors** — run `python init_db.py`; it's safe to re-run and never drops data.
- **Login fails immediately after installation** — confirm you ran `init_db.py`, which creates the `admin` user.
- **CSRF errors on forms** — make sure `SECRET_KEY` is set and stable across requests (it's read from `.env`; don't change it while a session is active).
- **Exports fail or produce empty files** — check the Flask log; export generation runs entirely in memory and any failure is logged server-side rather than shown to the user.

## Future Improvements (not implemented, by design)

Email/push notifications, calendar integrations (Google/Outlook/Teams/Slack),
a public REST API, and PostgreSQL migration are intentionally out of scope
for this project, but the architecture (service layer, `user_id`/`project_id`
columns, centralized date utilities) leaves room to add them later without
a rewrite. Multi-user accounts, roles, and admin oversight are already
implemented — see **Multi-user & Roles** above.
