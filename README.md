# Meeting Room Booking System

A student group project for managing meeting rooms, employees, and room bookings.

This project is under development. The repository has a single Flask app entry point, shared API error handling, and a service layer for the agreed business rules. The complete API and browser workflows are still in progress.

## Stack and architecture

- Python 3.9+ and Flask for the backend
- SQLite for storage
- Jinja templates with HTML/CSS for server-rendered pages
- pytest for automated tests

The application has one Flask entry point: `app.py`. Start it with `python app.py`.

## Office timezone

The office policy timezone is `Asia/Jakarta` (WIB, UTC+07:00). API timestamps without an offset are office-local wall times in this zone. Services use this timezone for their default clock; an injected `office_now` value is a timezone-naive datetime representing Asia/Jakarta local time.

## Initial setup

1. Accept the repository invitation and clone the repository.
2. Open the repository folder in VS Code.
3. Install Python and the Microsoft Python extension if needed.
4. Open the Command Palette and select **Python: Create Environment**.
5. Choose **Venv** and your installed Python interpreter.
6. When prompted, select `requirements.txt` to install the dependencies.
7. Ensure VS Code uses the project's `.venv` interpreter.

Each teammate creates their own virtual environment. The `.venv` folder is excluded from Git; `requirements.txt` records the required libraries.

## Run the application

From the repository root, in a terminal with the project's virtual environment activated:

```bash
python app.py
```

Open:

http://127.0.0.1:5000/health

Expected response:

```json
{"status": "ok"}
```

Alternatively, open `app.py` in VS Code and select **Run Python File in Terminal** with `.venv` selected.

Stop the server with **Ctrl+C** in its terminal.

## Run the tests

From the repository root, using the project's virtual environment:

```bash
python -m pytest
```

Alternatively, select **Python: Configure Tests** in VS Code, choose **pytest** and the **tests** folder, then run the tests from the Testing panel.

The current tests check:

- Invalid input returns HTTP 400 and the expected JSON message.
- Missing records return HTTP 404 and the expected JSON message.
- Business-rule violations return HTTP 409 and the expected JSON message.
- Unknown `/api/` endpoints return a JSON 404 response.
- Unknown non-API pages retain an HTML 404 response.

## Shared error handling

Application code can raise these shared exceptions:

| Exception | Status | Purpose |
|---|---|---|
| `InvalidInputError` | 400 | Invalid or missing input |
| `NotFoundError` | 404 | A requested record does not exist |
| `RuleViolationError` | 409 | An action breaks a business rule |

Example JSON error:

```json
{"error": "Room not found."}
```

Flask-generated HTTP errors under `/api/` also use this JSON error format.

HTML page handlers should catch shared business errors and display them using the shared frontend message component.

## Team responsibilities

| Teammate | Ownership |
|---|---|
| A (Alex) | Rooms and database setup |
| B (Angad) | Employees and shared page UI |
| C (Dyllon) | Bookings and Reports |

## Collaboration

- Work on feature branches rather than committing directly to `main`.
- Open small pull requests explaining what changed, why, and how it was tested.
- Obtain at least one approving teammate review before merging.
- Include manual test steps in PRs that change pages.
- Disclose significant AI-generated code in the PR description.
- Keep the API contract in `docs/api.md` aligned with agreed behaviour.

## Current limitations

The shared service layer in `backend/services.py` contains validation, database access, and booking/report rules. The complete API and browser workflows are still under development; `app.py` currently wires the health check, home redirect, and initial Rooms page. Database initialization, sample-data seeding, and the remaining acceptance flow still need to be completed.

The `/health` endpoint is a setup check. It is not the finished homepage.

Repository protection must be configured separately in GitHub; these written workflow rules do not enforce it automatically.