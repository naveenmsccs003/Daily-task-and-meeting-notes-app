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

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit SECRET_KEY for real deployments
python init_db.py               # creates instance/database.db + admin user
python app.py                   # runs on http://127.0.0.1:5000
```

Default login after `init_db.py`:

- **Username:** `admin`
- **Password:** `admin123`

**Change this password immediately in any real deployment.**

### Optional: sample data

```bash
python seed_data.py
```

Adds a handful of tasks and meetings across different dates/statuses so the
dashboard and reports are immediately testable. Do not run this against a
production database.

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

## Future Improvements (not implemented in v1, by design)

Email/push notifications, calendar integrations (Google/Outlook/Teams/Slack),
a public REST API, multi-user role-based administration, and PostgreSQL
migration are intentionally out of scope for this version but the
architecture (service layer, `user_id` columns, centralized date utilities)
leaves room to add them later without a rewrite.
