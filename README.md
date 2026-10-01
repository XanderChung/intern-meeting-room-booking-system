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

## Environment Setup

The app uses a Flask secret key to support session-based flash messages.

1. Copy `.env.example` to create the local file `.env`.
2. Generate a secret key:
Write the following command into your terminal to generate a random secret key: 
```sh
   python3 -c "import secrets; print(secrets.token_hex(32))"
```
3. Place this generated value directly after the "SECRET_KEY=" in the .env file 
4. Do not put your real key in the README or `.env.example`

## Database setup

The app uses a local SQLite database at `instance/meeting_rooms.sqlite3`. When the app starts, it creates the database and tables if they do not already exist.

To add the sample rooms and employees, run this from the project folder with your virtual environment active:

```sh
python seed.py
```
You can run the seed script more than once. It won’t duplicate sample rooms or employees, and it preserves custom records already in the database


## Run the application

From the repository root, with the virtual environment active:

```bash
python app.py
```

Open <http://127.0.0.1:5000/health>. The expected response is:

```json
{"status": "ok"}
```

The home route redirects to `/rooms`. The Rooms page displays each room's name, floor, capacity, and current availability, and includes a form for adding a room. A successful submission adds the room to the list; invalid input or a duplicate room name displays an error message. The employee directory is available at `/employees`. Its page includes a form for adding employees, and the API supports listing and creating employees at `/api/employees`.

## Run the tests

From the repository root:

```bash
python -m pytest
```
Latest full-suite run on 2026-10-01: **108 passed**.

The suite covers shared API errors, timezone behavior, database initialization and seeding, employee and room list routes, flash messages, and booking behavior. Additional tests are still needed for features that have not yet been implemented.

## API contract and errors

The authoritative endpoint, request, response, schema, validation, and status-code contract is [`docs/api.md`](docs/api.md). JSON errors use one envelope:

```json
{"error": "Human-readable message."}
```

The shared exceptions in `errors.py` map invalid input to 400, missing resources to 404, and business-rule conflicts to 409. `app.py` registers the handlers, so Flask-generated API errors use the same JSON envelope while ordinary page errors remain HTML. The room-list and room-creation APIs (`GET /api/rooms` and `POST /api/rooms`) and the employee-list API (`GET /api/employees`) are implemented. Room detail, employee creation and detail, and booking and report routes are still to be completed.

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
| Flask app | `app.py` registers shared error handlers, serves `/health`, redirects `/` to `/rooms`, and serves the Rooms and employee list routes. | Add room detail, remaining employee, booking, and report routes. |
| API | The contract is documented in `docs/api.md`; `GET /api/rooms`, `POST /api/rooms`, and `GET /api/employees` are implemented. | Add room detail, employee creation/detail, and Bookings/Reports endpoints. |
| Pages | A base template, stylesheet, Rooms list and creation form, and employee directory page are present. | Add room detail, employee creation/detail, and Bookings pages. |
| Tests | Shared errors, timezone handling, database setup/seeding, room and employee routes, flash messages, and booking behavior have coverage. | Add tests for remaining routes and business-rule edge cases as those features are implemented. |
| Service layer | `backend/services.py` has shared create/list/detail, booking, cancellation, and report functions. | Integrate them with routes and add automated coverage for their rules. |
| Database | SQLite schema, per-connection foreign keys, repeatable initialization, and sample seeding are implemented. | None for the shared database foundation. |


The SQL schema in `docs/api.md` is the shared starting point for database setup. Write services own their transactions and expect an SQLite connection with no active transaction. See the contract for booking rules and report semantics.

## Known limitations

A clean clone cannot yet complete the full browser acceptance flow. Room detail, employee creation and detail, and the booking and reporting features are still in progress. Some route and business-rule tests remain to be added as those features are implemented. GitHub branch protection must be configured separately; the written workflow rules do not enforce it.
