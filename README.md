# Meeting Room Booking System

A student team project for managing meeting rooms, employees, and room bookings. The core booking, employee, and room features are implemented and merged; final integration checks and fresh-clone/browser verification remain.

## Stack and architecture

- Python 3.9+ and Flask.
- SQLite for storage.
- Jinja templates with HTML/CSS.
- pytest for automated tests.

The application entry point is `app.py`. Business rules and database operations belong in `backend/services.py`. API and HTML routes use the shared services rather than duplicating validation.

## Office timezone

The office timezone is `Asia/Jakarta` (WIB, UTC+07:00). API timestamps use office-local `YYYY-MM-DDTHH:MM` values. The service clock uses `ZoneInfo("Asia/Jakarta")`; injected `office_now` values must be timezone-naive Jakarta wall times. The `tzdata` dependency supplies timezone data on Windows.

## Setup

1. Clone the repository and open its folder in VS Code.
2. From the repository root, create a virtual environment:

   ```sh
   python3 -m venv .venv
   ```

3. Activate it:

   - **macOS/Linux:**
     ```sh
     source .venv/bin/activate
     ```

   - **Windows:**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```

4. Install dependencies:

   ```sh
   python -m pip install -r requirements.txt
   ```

Each teammate uses their own virtual environment. The `.venv` directory should be excluded from Git. 

## Environment settings

Flask uses `SECRET_KEY` for sessions and flash messages. Copy `.env.example` to `.env`, then set a generated secret key:

```sh
python -c "import secrets; print(secrets.token_hex(32))"
```

Put the generated value in `.env` on this line, replacing the example text with your key:

```dotenv
SECRET_KEY=paste-your-generated-key-here
```

Do not commit `.env` or a real secret key. Tests set a test-only key.

## Database setup

The local SQLite database is `instance/meeting_rooms.sqlite3`. Running `python app.py` initializes missing tables. To initialize the database and add sample rooms and employees, run:

```sh
python seed.py
```

The seed script preserves existing records and skips duplicate sample room names and employee emails.

## Run the application

From the project root, with the virtual environment active:

```sh
python app.py
```

Open <http://127.0.0.1:5000/>. The home page redirects to `/rooms`; `/health` returns `{"status":"ok"}`.

Available pages:

- `/rooms`: room list, current availability, and room creation.
- `/employees`: employee directory and employee creation.
- `/employees/{id}`: employee details and upcoming active bookings.
- `/rooms/{id}`: room details and bookings for a chosen date.
- `/bookings`: booking list and filters, booking creation and cancellation, and the Top 5 rooms report.


## Run the tests

From the project root:

```sh
python -m pytest
```

On Windows, if pytest cannot use its default temporary directory, set an external temporary directory:

```powershell
$env:SECRET_KEY = "dev-only"
$env:PYTHONDONTWRITEBYTECODE = "1"
$testBase = Join-Path $env:TEMP ("meeting-room-pytest-" + $PID)

.\.venv\Scripts\python.exe -m pytest `
  -p no:cacheprovider `
  --basetemp $testBase
```

Latest full-suite result reported by Student A on 2026-10-04: **136 passed**. This is a local test result; the repository currently has no GitHub Actions workflow runs.

The suite covers room and employee features, booking and cancellation rules, reports, database setup and seeding, shared API errors, and timezone behavior.

## API contract and errors

The authoritative request, response, schema, validation, and status-code contract is in [`docs/api.md`](docs/api.md). JSON errors use:

```json
{"error": "Human-readable message."}
```

Shared errors map invalid input to 400, missing resources to 404, and business-rule conflicts to 409. API 404/405 responses use the JSON envelope; ordinary page errors remain HTML.

Implemented API operations:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/rooms` | List rooms and current availability |
| POST | `/api/rooms` | Create a room |
| GET | `/api/rooms/{id}` | Return one room and its bookings for a date |
| GET | `/api/employees` | List employees |
| POST | `/api/employees` | Create an employee |
| GET | `/api/employees/{id}` | Return employee details and upcoming bookings |
| POST | `/api/bookings` | Create a booking |
| GET | `/api/bookings` | List and filter active bookings |
| POST | `/api/bookings/{id}/cancel` | Cancel an upcoming booking |
| GET | `/api/reports/top-rooms` | Rank rooms by active booking count |


## Team responsibilities

| Student | Ownership |
|---|---|
| A — Angad | Rooms and database setup |
| B — Dyllon | Employees and shared page UI |
| C — Alex/Chung | Bookings and Reports |

## Current status and remaining work

| Area | Status |
|---|---|
| Bookings and Reports | Booking rules, create/list/cancel APIs and page flows, and Top Rooms report |
| Employees | Listing, creation, and detail API/pages are implemented |
| Rooms | Listing, availability, creation, and room-detail API/page are implemented and merged to main |
| Automated tests | 136 passed in the latest reported local run; no CI workflow is configured |
| Database | Schema, foreign keys, initialization, and repeatable sample seeding are implemented |
| Final integration | The complete browser acceptance sequence and fresh-clone verification still need to be recorded |

Remaining final browser checks:

1. Add or seed a room and employee.
2. Create a booking for tomorrow.
3. Reject an overlapping booking and accept a back-to-back booking.
4. Reject over-capacity and out-of-hours bookings.
5. Cancel a booking, confirm it leaves the active list, and rebook the released slot.
6. Confirm a second or stale cancellation shows a clear error.
7. Confirm Top Rooms excludes cancelled bookings and sorts ties alphabetically.
8. Record the actual clicks and observed results on the merged `main`.

The repository has an active `main` ruleset, but it currently does not require a pull request approval or status checks. The repository administrator should confirm and configure the agreed review protection.

## Known limitations

The app uses a local SQLite database and Flask’s development server; production deployment is not configured. GitHub currently does not require PR approval or status checks, so repository protection must be configured separately if the team requires it.
