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

The home route redirects to `/rooms`, which lists rooms and their current availability. The employee directory at `/employees` supports employee creation and links to individual detail pages showing upcoming active bookings. The Bookings page at `/bookings` supports listing, filtering, and creating bookings.

## Run the tests

From the repository root:

```bash
python -m pytest
```

The suite covers shared API errors, the Asia/Jakarta clock, database initialization and seeding, room listing, booking routes, and employee listing, creation, and details. Employee tests cover validation, duplicate emails through both API and form submissions, retained form inputs, HTML missing-employee errors, and upcoming-booking filtering and ordering.

Latest reported local run for the employee-detail branch on 2026-10-01: **98 passed in 2.22s**. This is local verification, not a GitHub workflow result. On Windows, if pytest cannot access its default temporary directory, run `python -m pytest -q --basetemp=.pytest_tmp_b2`; this temporary directory must remain ignored by Git.

## API contract and errors

The authoritative endpoint, request, response, schema, validation, and status-code contract is [`docs/api.md`](docs/api.md). JSON errors use one envelope:

```json
{"error": "Human-readable message."}
```

The shared exceptions in `errors.py` map invalid input to 400, missing resources to 404, and business-rule conflicts to 409. Employee APIs support `GET /api/employees`, `POST /api/employees`, and `GET /api/employees/{id}`. Missing employees return JSON errors through the API and an HTML error notice with status 404 through the detail page. Room listing and booking listing/creation APIs are also implemented.

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
| Employees | List and creation APIs/page; detail API/page; upcoming bookings ordered by start; HTML and JSON missing-employee handling; automated and browser checks. | Final integrated acceptance checks. |
| Rooms | Room list API/page with current availability. | Room creation changes are in Angad's separate PR; detail routes still need integration. |
| Bookings | Listing/filtering and creation APIs/page using shared services. | Cancellation and reports route integration, plus final acceptance checks. |
| Shared UI | Base layout, navigation, categorized success/error notices. | Coordinate consistent form and table styling after the Rooms PR merges. |
| Database | SQLite schema, foreign keys, repeatable initialization, and sample seeding. | Final fresh-clone verification. |
| Tests | Employee features, room listing, booking routes, shared errors, timezone, database, seeding, and flash messages. | Extend coverage as remaining features land and rerun the full suite. |

The SQL schema in `docs/api.md` is the shared starting point for database setup. Write services own their transactions and expect an SQLite connection with no active transaction. See the contract for booking rules and report semantics.

## Known limitations

The full browser acceptance flow still requires remaining Rooms, cancellation, and reporting work, shared UI checks, and fresh-clone verification. Employee listing, creation, and details are implemented. GitHub branch protection and workflow configuration must be checked separately; written collaboration rules do not enforce them.

