# Meeting Room Booking System

A student group project for managing meeting rooms, employees, and room bookings.

This project is under development. The current backend foundation provides a health-check endpoint and shared API error handling.

## Stack

- Python and Flask for the backend
- pytest for automated tests
- Planned: SQLite for storage and Jinja templates with HTML/CSS for pages

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

| Team member | Phase 1 responsibility |
|---|---|
| Alex | API contract and architecture |
| Angad | Backend foundation, Git environment, shared API errors, and README setup |
| Dyllon | Shared HTML layout, CSS, frontend messages, and homepage redirect |

Phase 2 ownership of Rooms, Employees, and Bookings & Reports will be recorded here once finalised.

## Collaboration

- Work on feature branches rather than committing directly to `main`.
- Open small pull requests explaining what changed, why, and how it was tested.
- Obtain at least one approving teammate review before merging.
- Include manual test steps in PRs that change pages.
- Disclose significant AI-generated code in the PR description.
- Keep the API contract in `docs/api.md` aligned with agreed behaviour.

## Current limitations

This branch currently contains the backend foundation. Room, employee, and booking features, database setup, sample-data seeding, and the complete browser acceptance flow are not implemented here yet.

The `/health` endpoint is a setup check. It is not the finished homepage.

Repository protection must be configured separately in GitHub; these written workflow rules do not enforce it automatically.