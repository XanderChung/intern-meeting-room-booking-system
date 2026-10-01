# Meeting Room Booking System

A student team project for managing meeting rooms, employees, and room bookings. The project is still under development.

## Stack and architecture

- Python 3.9+ and Flask.
- SQLite for storage.
- Jinja templates with HTML/CSS.
- pytest for automated tests.

The application entry point is `app.py`. Business rules and database operations belong in `backend/services.py`. API and HTML routes call these shared services rather than duplicating validation rules.

## Office timezone

The office timezone is `Asia/Jakarta` (WIB, UTC+07:00).

API timestamps use office-local time in `YYYY-MM-DDTHH:MM` format. Services use `ZoneInfo("Asia/Jakarta")` for the default clock. Injected `office_now` values must be timezone-naive datetimes representing Jakarta time.

The `tzdata` dependency supplies timezone data on Windows.

## Setup

1. Clone the repository and open the project folder in VS Code.
2. Create a virtual environment:

   ```sh
   python -m venv .venv
   ```

   On Windows, you can use `py -m venv .venv`.

3. Activate the environment.

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```sh
   source .venv/bin/activate
   ```

4. Install dependencies:

   ```sh
   python -m pip install -r requirements.txt
   ```

Each teammate uses their own virtual environment. Do not commit `.venv`.

If PowerShell blocks activation, you can use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Environment settings

Flask uses a secret key to sign sessions and support flash messages.

1. Copy `.env.example` to a local file named `.env`.
2. Generate a key:

   ```sh
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   On Windows without an active environment, use `py` instead of `python`.

3. Set the generated value in `.env`:

   ```dotenv
   SECRET_KEY=your-generated-value
   ```

Do not commit `.env` or a real secret key. Tests use a separate test-only key.

## Database setup

The local SQLite database is stored at `instance/meeting_rooms.sqlite3`.

Running `python app.py` initializes missing tables. To initialize the database and add sample rooms and employees, run:

```sh
python seed.py
```

The seed script preserves existing records and skips duplicate sample room names and employee emails.

## Run the application

From the project root, with the virtual environment active:

```sh
python app.py
```

Open http://127.0.0.1:5000/.

The home page redirects to `/rooms`. The health endpoint at `/health` returns:

```json
{"status": "ok"}
```

Available pages:

- `/rooms`: room list, current availability, and room creation.
- `/employees`: employee directory and employee creation.
- `/employees/{id}`: employee details and upcoming active bookings.
- `/bookings`: booking list, date/room filters, and booking creation.

Employee names in the directory link to their detail pages.

Upcoming employee bookings are ordered by start time and exclude cancelled bookings and bookings that have already started.

For development on port 5001, initialize the database first, then run:

```sh
python -m flask --app app run --port 5001
```

Open http://127.0.0.1:5001/ when using that command.

## Run the tests

From the project root:

```sh
python -m pytest
```

If pytest cannot access its default temporary folder on Windows, use:

```sh
python -m pytest -q --basetemp=.pytest_tmp_b2
```

Keep `.pytest_tmp_b2/` excluded from Git. This directory is reserved for temporary test files; pytest may clear it between runs.

Local full-suite verification for this branch: **98 passed in 2.15s**.

Command used:

```sh
python -m pytest -q --basetemp=.pytest_tmp_b2
```

This is a local test result, not a GitHub workflow result.

Tests cover shared errors, timezone handling, database initialization and seeding, flash messages, room routes, booking routes, and employee features.

Employee tests include:

- Successful creation and persistence.
- Required fields, invalid types, and invalid email input.
- Duplicate emails through API and form submissions.
- Retained form values when submission fails.
- Employee detail API and HTML page.
- Missing-employee JSON and HTML responses.
- Upcoming-booking ordering and filtering.
- Directory and detail-page navigation links.

## Browser verification

The following checks were performed during employee and shared UI development:

- Created an employee and observed the success notice and new directory entry.
- Submitted a duplicate email and observed the error notice with inputs retained.
- Opened employee detail pages from directory links.
- Checked the employee detail API and its missing-employee JSON response.
- Opened a missing employee's HTML page and observed the shared layout, error notice, and status 404.
- Created a future booking and confirmed its room, title, start/end times, and attendees appeared on the selected employee's detail page.
- Opened Rooms and Employees and confirmed matching form widths, spacing, blue buttons, and shared table styling.

Screenshots and observed results belong in the relevant PR descriptions. These checks do not replace final integrated acceptance testing.

## API contract and errors

The endpoint, request, response, database, and validation contract is documented in [`docs/api.md`](docs/api.md).

Implemented API routes include:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/rooms` | List rooms and current availability |
| POST | `/api/rooms` | Create a room |
| GET | `/api/employees` | List employees |
| POST | `/api/employees` | Create an employee |
| GET | `/api/employees/{id}` | Return employee details and upcoming bookings |
| GET | `/api/bookings` | List and filter active bookings |
| POST | `/api/bookings` | Create a booking |

JSON errors use this format:

```json
{"error": "Human-readable message."}
```

Shared exceptions map invalid input to 400, missing resources to 404, and business-rule conflicts to 409.

A missing employee returns a JSON error through the API. The HTML employee-detail route renders the shared layout with an error notice while preserving status 404.

## Team responsibilities

| Student | Ownership |
|---|---|
| A — Angad | Rooms and database setup |
| B — Dyllon | Employees and shared page UI |
| C — Alex/Chung | Bookings and Reports |

Each student owns their feature's services, API, pages, and tests. Coordinate changes to shared files such as `app.py`, `backend/services.py`, `docs/api.md`, `static/styles.css`, and this README.

## Collaboration

- Start features from updated `main` using a `feature/<area>-<short-name>` branch.
- Do not commit feature work directly to `main`.
- Keep PRs focused, targeting roughly 200 changed lines where practical.
- Explain what changed and how it was checked.
- Obtain at least one approving teammate review before merging.
- Authors do not approve or merge their own work.
- Include browser steps and observed results for page changes.
- Disclose significant AI assistance in PR descriptions.
- Post brief done / next / blocked updates.
- Keep the API contract aligned with implementation.

## Current implementation status

| Area | Implemented | Remaining |
|---|---|---|
| Employees | Listing, creation, and details through API and HTML; upcoming bookings; validation and missing-employee handling; automated and browser checks | Final integrated acceptance checks |
| Rooms | Listing, current availability, creation, validation, and retained inputs on form errors | Room detail route integration |
| Bookings | Listing, filtering, and creation through API and HTML | Cancellation and report route integration; final acceptance checks |
| Shared UI | Base layout, navigation, notices, and shared tables; this branch aligns employee form styling with existing room classes | Review and merge of this branch; remaining UI checks |
| Database | Schema, foreign keys, repeatable initialization, and sample seeding | Fresh-clone verification |
| Services | Shared room, employee, booking, cancellation, and report functions | Integrate remaining routes and extend checks |
| Tests | Coverage for implemented routes, employee rules, shared errors, timezone, database, seeding, and flash messages | Extend coverage as remaining features land |

Write services own their transactions and require a SQLite connection with no active transaction.

## Known limitations

The full acceptance flow still requires room details, cancellation, reporting, remaining UI checks, and fresh-clone verification.

Employee listing, creation, and details are implemented. The Bookings form was not restyled in this shared UI PR.

GitHub workflow runs and branch protection must be checked separately. Written collaboration rules do not enforce repository settings.