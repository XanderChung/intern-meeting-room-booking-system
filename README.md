# Meeting Room Booking System

A student team project for managing meeting rooms, employees, and room bookings. The project is still under development.

## Agreed stack and architecture

- Python 3.9+ and Flask for the backend.
- SQLite for storage.
- Jinja templates with HTML/CSS for server-rendered pages.
- pytest for automated tests.

The single Flask application entry point is `app.py`. Business rules and database operations belong in shared functions in `backend/services.py`; JSON and HTML routes should call those functions instead of duplicating rules. Templates display data and messages but do not implement business rules.

## Office timezone

The office policy timezone is `Asia/Jakarta` (WIB, UTC+07:00). API timestamps without an offset represent office-local time in `YYYY-MM-DDTHH:MM` format. Services use `ZoneInfo("Asia/Jakarta")` for their default clock. An injected `office_now` value must be a timezone-naive datetime representing Jakarta wall time, not computer-local or UTC-naive time. The `tzdata` dependency supplies IANA timezone data on Windows.

## Setup

1. Clone the repository and open it in VS Code.
2. Use Python 3.9 or newer and create a project virtual environment.
3. Install the dependencies from `requirements.txt`:
   ```bash
   python -m pip install -r requirements.txt
   ```

Each teammate uses their own virtual environment. The `.venv` directory is excluded from Git.

## Run the application

From the repository root, with the virtual environment active:

```bash
python app.py
```

Open <http://127.0.0.1:5000/health>. The expected response is:

```json
{"status": "ok"}
```

The home route redirects to `/rooms`, which is currently a placeholder page.

## Run the tests

From the repository root:

```bash
python -m pytest
```

The current suite contains five shared-error tests in `tests/test_errors.py`. They register the handlers on temporary Flask test apps; they do not verify that the real app in `app.py` registers those handlers. Tests for the database and Rooms, Employees, Bookings, Reports, and their business rules still need to be added.

## API contract and errors

The authoritative endpoint, request, response, schema, validation, and status-code contract is [`docs/api.md`](docs/api.md). JSON errors use one envelope:

```json
{"error": "Human-readable message."}
```

The shared exceptions in `errors.py` map invalid input to 400, missing resources to 404, and business-rule conflicts to 409. Flask-generated API errors should use the same JSON envelope; ordinary page errors should remain HTML. The handlers exist, but `app.py` does not yet register them.

## Team responsibilities

| Student | Ownership |
|---|---|
| A (Angad) | Rooms and database setup |
| B (Dyllon) | Employees and shared page UI |
| C (Alex/Chung) | Bookings and Reports |

Each student owns their feature end to end: service rules, API, page, and tests. Coordinate changes to shared files such as `app.py`, `backend/services.py`, `docs/api.md`, and this README.

## Collaboration

- Start each feature from updated `main` on a branch named `feature/<area>-<short-name>`. Do not commit feature work directly to `main`.
- Keep pull requests small (about 200 changed lines or fewer) and describe what changed, why, and how it was checked.
- Obtain at least one approving teammate review before merging. Authors do not approve or merge their own work.
- Page-changing PRs include manual test steps with the clicks and observed results.
- Disclose significant AI-generated code in the PR description.
- Post a short done / next / blocked team update when starting, finishing, or blocked.
- Keep `docs/api.md` aligned with implemented behavior.

## Current implementation status

| Area | Present | Still needed |
|---|---|---|
| Flask app | `app.py` serves `/health`, redirects `/` to `/rooms`, and renders the placeholder Rooms page. | Register shared error handlers and wire the feature routes into this app. |
| Service layer | `backend/services.py` has shared create/list/detail, booking, cancellation, and report functions. | Integrate them with routes and add automated coverage for their rules. |
| API | The contract is documented in `docs/api.md`. | The ten required API operations are not wired to Flask routes yet. |
| Database | The SQLite schema is documented in `docs/api.md`. | Add runnable connection/initialization support, enable foreign keys on each connection, and add a seed script. |
| Pages | A base template, stylesheet, and placeholder Rooms page exist. | Implement Rooms, Employees, and Bookings pages. The base template's notice class names do not currently match the stylesheet, so message styling also needs repair. |
| Tests | Five isolated shared-error-handler tests exist. | Test the real app's error handling, database setup, every required business rule, and API behavior. |

The SQL schema in `docs/api.md` is the shared starting point for database setup. Write services own their transactions and expect an SQLite connection with no active transaction. See the contract for booking rules and report semantics.

## Known limitations

A clean clone cannot yet complete the browser acceptance flow. The app has no registered shared error handlers, runnable database setup, or seed data; the required API routes and feature pages are still being integrated. GitHub branch protection must also be configured separately; the written workflow rules do not enforce it.
