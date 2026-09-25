# Meeting Room Booking API Contract

This document is the shared contract for the Flask JSON API and the HTML pages.
Both route layers call the same functions in `backend/services.py`; templates
only render data and messages. Route handlers are responsible for HTTP parsing,
status codes, and JSON or HTML responses, while service functions own validation,
database access, and booking rules.

## Conventions

- Base path: `/api`.
- Request and response bodies use `application/json`.
- IDs and attendee counts are positive JSON integers. Boolean values are not integers.
- Text fields are trimmed before storage. Room names and employee emails are unique
  without regard to letter case.
- API timestamps are office-local values in exactly `YYYY-MM-DDTHH:MM` format,
  such as `2026-10-01T10:00`. They have no timezone suffix. The server must use
  the office timezone, or inject the office-local clock into services.
- Date query parameters use `YYYY-MM-DD`. An omitted or empty date defaults to
  the current date in the office timezone.
- Active booking lists and counts exclude rows where `cancelled_at` is not null.
- JSON errors have one shape: `{"error": "Human-readable message."}`.
- Invalid or missing request data returns `400`; missing resources return `404`;
  conflicts with business rules return `409`.

## Database schema

SQLite schema. Enable foreign keys for every connection with
`PRAGMA foreign_keys = ON;`.

```sql
CREATE TABLE rooms (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL COLLATE NOCASE UNIQUE,
    floor    TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity >= 1)
);

CREATE TABLE employees (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL COLLATE NOCASE UNIQUE,
    department TEXT NOT NULL
);

CREATE TABLE bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id      INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    employee_id  INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    title        TEXT NOT NULL,
    start_at     TEXT NOT NULL,
    end_at       TEXT NOT NULL,
    attendees    INTEGER NOT NULL CHECK (attendees >= 1),
    cancelled_at TEXT NULL,
    CHECK (start_at < end_at)
);

CREATE INDEX bookings_room_time_idx
    ON bookings (room_id, start_at, end_at);
CREATE INDEX bookings_employee_time_idx
    ON bookings (employee_id, start_at);
```

The timestamp strings are stored in one fixed-width format so SQLite text
comparisons follow chronological order. Service validation enforces the
four-hour maximum, same-day limit, office hours, future-start requirement,
room capacity, and no-overlap rule. Booking writes must use
`services.create_booking`, which takes a SQLite `BEGIN IMMEDIATE` write lock
before checking overlap and inserting. Write service functions own their
transaction and require a connection with no active transaction.

`cancelled_at` is null for an active booking; a cancellation stores an
office-local ISO timestamp with seconds, such as `2026-10-01T09:30:00`.

## Rooms

### `GET /api/rooms`

List all rooms, ordered by name. `available_now` is true when no active booking
for that room contains the current office-local time.

**Response `200`:**

```json
{
  "rooms": [
    {"id": 1, "name": "Boardroom", "floor": "2", "capacity": 12, "available_now": true}
  ]
}
```

Service: `services.list_rooms(db_connection, office_now=None)`.

### `GET /api/rooms/{id}?date=YYYY-MM-DD`

Return one room and its active bookings starting on the requested date, sorted
by start time. `date` is optional and defaults to office today. A missing room
returns `404`.

**Response `200`:**

```json
{
  "room": {"id": 1, "name": "Boardroom", "floor": "2", "capacity": 12},
  "date": "2026-10-01",
  "bookings": [
    {
      "id": 31,
      "room_id": 1,
      "employee_id": 7,
      "employee_name": "Alex Lee",
      "title": "Planning",
      "start_at": "2026-10-01T10:00",
      "end_at": "2026-10-01T11:00",
      "attendees": 6
    }
  ]
}
```

Service: `services.get_room_for_date(room_id, db_connection, date_value=None, office_now=None)`.

### `POST /api/rooms`

Create a room. All fields are required; `capacity` must be a positive integer.
Names are trimmed and unique case-insensitively.

**Request:**

```json
{"name": "Boardroom", "floor": "2", "capacity": 12}
```

**Response `201`:**

```json
{"room": {"id": 1, "name": "Boardroom", "floor": "2", "capacity": 12}}
```

Errors: `400` for missing/invalid fields; `409` if the room name already exists.

Service: `services.create_room(name, floor, capacity, db_connection)`.

## Employees

### `GET /api/employees`

List all employees, ordered by name.

**Response `200`:**

```json
{
  "employees": [
    {"id": 7, "name": "Alex Lee", "email": "alex@example.com", "department": "Operations"}
  ]
}
```

Service: `services.list_employees(db_connection)`.

### `GET /api/employees/{id}`

Return one employee and their upcoming active bookings, ordered by start time.
Each booking includes its room ID and room name. A missing employee returns
`404`.

**Response `200`:**

```json
{
  "employee": {"id": 7, "name": "Alex Lee", "email": "alex@example.com", "department": "Operations"},
  "bookings": [
    {
      "id": 31,
      "room_id": 1,
      "room_name": "Boardroom",
      "title": "Planning",
      "start_at": "2026-10-01T10:00",
      "end_at": "2026-10-01T11:00",
      "attendees": 6
    }
  ]
}
```

“Upcoming” means `start_at` is later than the current office-local time.
Service: `services.get_employee_with_upcoming_bookings(employee_id, db_connection, office_now=None)`.

### `POST /api/employees`

Create an employee. `name`, `email`, and `department` are required. Email
validation follows the project brief: it must contain `@`; email uniqueness is
case-insensitive.

**Request:**

```json
{"name": "Alex Lee", "email": "alex@example.com", "department": "Operations"}
```

**Response `201`:**

```json
{"employee": {"id": 7, "name": "Alex Lee", "email": "alex@example.com", "department": "Operations"}}
```

Errors: `400` for missing fields or an email without `@`; `409` for a duplicate
email.

Service: `services.create_employee(name, email, department, db_connection)`.

## Bookings

### `POST /api/bookings`

Create an active booking. `room_id`, `employee_id`, `title`, `start_at`,
`end_at`, and `attendees` are required.

**Request:**

```json
{
  "room_id": 1,
  "employee_id": 7,
  "title": "Planning",
  "start_at": "2026-10-01T10:00",
  "end_at": "2026-10-01T11:00",
  "attendees": 6
}
```

**Response `201`:**

```json
{
  "booking": {
    "id": 31,
    "room_id": 1,
    "employee_id": 7,
    "title": "Planning",
    "start_at": "2026-10-01T10:00",
    "end_at": "2026-10-01T11:00",
    "attendees": 6,
    "cancelled_at": null
  }
}
```

Validation and errors:

- `400`: missing fields, malformed timestamps, start not before end, or duration
  longer than four hours.
- `404`: the room or employee ID does not exist.
- `409`: attendees exceed room capacity; the booking is not on one day, outside
  08:00–18:00, starts in the past/current minute, or overlaps an active booking.
- End time 18:00 is allowed. Back-to-back bookings are allowed; cancelled
  bookings do not block a slot.

`services.validate_booking(...)` is the single orchestration point for the
booking rules. The write route calls `services.create_booking(...)`, which
validates and inserts atomically.

### `GET /api/bookings?date=YYYY-MM-DD&room_id=1`

List active bookings that start on the date, ordered by start time. `date` is
optional and defaults to office today. `room_id` is optional. A syntactically
valid but unknown room filter returns an empty list.

**Response `200`:**

```json
{
  "bookings": [
    {
      "id": 31,
      "room_id": 1,
      "room_name": "Boardroom",
      "employee_id": 7,
      "employee_name": "Alex Lee",
      "title": "Planning",
      "start_at": "2026-10-01T10:00",
      "end_at": "2026-10-01T11:00",
      "attendees": 6
    }
  ]
}
```

Errors: `400` for an invalid date or room ID query value.
Service: `services.list_bookings(db_connection, date_value=None, room_id=None, office_now=None)`.

### `POST /api/bookings/{id}/cancel`

Cancel an active booking before its start time. The request body is empty.

**Response `200`:**

```json
{
  "booking": {
    "id": 31,
    "room_id": 1,
    "room_name": "Boardroom",
    "employee_id": 7,
    "employee_name": "Alex Lee",
    "title": "Planning",
    "start_at": "2026-10-01T10:00",
    "end_at": "2026-10-01T11:00",
    "attendees": 6,
    "cancelled_at": "2026-10-01T09:30:00"
  }
}
```

Errors: `404` if the booking does not exist; `409` if it is already cancelled
or has already started. Service: `services.cancel_booking(booking_id,
db_connection, office_now=None)`.

## Reports

### `GET /api/reports/top-rooms?n=5`

Return up to `n` rooms ranked by the count of bookings that are not cancelled.
`n` defaults to 5 and must be a positive integer. All rooms are eligible,
including rooms with zero bookings. Ties sort by room name A→Z.

**Response `200`:**

```json
{
  "rooms": [
    {"id": 1, "name": "Boardroom", "floor": "2", "capacity": 12, "booking_count": 14}
  ]
}
```

Error: `400` if `n` is not a positive integer.
Service: `services.get_top_rooms(db_connection, n=5)`.

## Shared error examples

```json
{"error": "Room name is required."}
```

| Status | Meaning | Example |
|---|---|---|
| `400` | Invalid or missing request data | `{"error":"Date must use YYYY-MM-DD format."}` |
| `404` | Unknown API route or requested record | `{"error":"Room 99 does not exist."}` |
| `409` | Business-rule or uniqueness conflict | `{"error":"Room 1 is already booked for that time slot."}` |
| `405` | Method is not supported on the API route | `{"error":"Method not allowed for this API endpoint."}` |

## Shared service architecture

Flask JSON route handlers and HTML route handlers call these same service
functions. HTML routes catch `APIError` subclasses from `errors.py` and display
the message through the shared page message component; JSON routes let the
registered Flask error handler serialize the exception. Templates do not
contain validation or booking rules.

| Concern | Shared service functions |
|---|---|
| Room validation, creation, listing, date detail | `validate_room`, `create_room`, `list_rooms`, `get_room_for_date` |
| Employee validation, creation, listing, upcoming bookings | `validate_employee`, `validate_employee_email`, `create_employee`, `list_employees`, `get_employee_with_upcoming_bookings` |
| Booking field/reference/capacity/time/office-hours/future/overlap rules | `validate_booking_fields`, `validate_booking_references`, `check_capacity`, `check_time_range`, `check_office_hours`, `check_future_booking`, `check_booking_overlap`, `validate_booking` |
| Booking creation, listing, cancellation | `create_booking`, `list_bookings`, `check_cancel_validity`, `cancel_booking` |
| Top rooms report | `get_top_rooms` |

`errors.py` defines the shared `InvalidInputError` (400), `NotFoundError` (404),
and `RuleViolationError` (409) exceptions and Flask handlers. The service layer
raises these classes rather than defining a second set of exceptions.
