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

The current suite contains six focused shared-error tests in `tests/test_errors.py`. It checks the 400/404/409 exceptions, API 404 and page 404 behavior on the real app, and preservation of the `Allow` header on a 405 response. The exception and 405 checks use small test apps. Tests for the database, feature routes, and business rules still need to be added.

## API contract and errors

The authoritative endpoint, request, response, schema, validation, and status-code contract is [`docs/api.md`](docs/api.md). JSON errors use one envelope:

```json
{"error": "Human-readable message."}
```

The shared exceptions in `errors.py` map invalid input to 400, missing resources to 404, and business-rule conflicts to 409. `app.py` registers the handlers, so Flask-generated API errors use the same JSON envelope while ordinary page errors remain HTML. The feature API routes are still to be wired.

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
| Flask app | `app.py` registers shared error handlers, serves `/health`, redirects `/` to `/rooms`, and renders the placeholder Rooms page. | Wire the feature routes into this app. |
| Service layer | `backend/services.py` has shared create/list/detail, booking, cancellation, and report functions. | Integrate them with routes and add automated coverage for their rules. |
| API | The contract is documented in `docs/api.md`. | The ten required API operations are not wired to Flask routes yet. |
| Database | The SQLite schema is documented in `docs/api.md`. | Add runnable connection/initialization support, enable foreign keys on each connection, and add a seed script. |
| Pages | A base template, stylesheet, and placeholder Rooms page exist. | Implement Rooms, Employees, and Bookings pages. The base template's notice class names do not currently match the stylesheet, so message styling also needs repair. |
| Tests | Six focused shared-error tests cover exception statuses, real-app API/page 404s, and the 405 `Allow` header. | Add database, feature-route, and business-rule tests. |

The SQL schema in `docs/api.md` is the shared starting point for database setup. Write services own their transactions and expect an SQLite connection with no active transaction. See the contract for booking rules and report semantics.

## Known limitations

A clean clone cannot yet complete the browser acceptance flow. Runnable database setup and seed data, the required API routes, and the feature pages are still missing. The base template's notice classes also need to be matched with the stylesheet. GitHub branch protection must be configured separately; the written workflow rules do not enforce it.
