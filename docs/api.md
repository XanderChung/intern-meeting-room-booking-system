# Meeting Room Booking System — API & Data Contract

This document defines the API data model, endpoints, booking rules, and error handling for the Meeting Room Booking application.

## 1. Global Standards & Data Model

### Date & time format

All dates and times use the office's local time and ISO 8601 format:

- **Format:** `YYYY-MM-DDTHH:MM` (e.g., `2026-10-01T10:00`)

### Data model

```text
rooms(id, name, floor, capacity)
employees(id, name, email, department)
bookings(id, room_id, employee_id, title, start_at, end_at, attendees, cancelled_at)
```

### Shared business rules

Each business rule (including no overlap, capacity, office hours, and unique email) must be written in one place as a function or service. API endpoints and HTML pages use those functions; rules must not be copied into a page.

### Error response format and status codes

API errors use one shared JSON format with a clear description:

```json
{
  "error": "Clear description of the error"
}
```

| Status | Use |
| --- | --- |
| `200 OK` | Request succeeded. |
| `400 Bad Request` | Missing required fields or invalid input. |
| `404 Not Found` | Requested resource does not exist. |
| `409 Conflict` | Business rule violation, such as an overlapping booking. |

## 2. API Endpoints

### A. Rooms

#### `GET /api/rooms`

Lists all rooms. Each room includes an **available now** flag, represented as yes/no or a boolean.

**Response (200 OK):**

```json
[
  {
    "id": 1,
    "name": "Boardroom A",
    "floor": 2,
    "capacity": 8,
    "available_now": true
  }
]
```

#### `GET /api/rooms/{id}?date=YYYY-MM-DD`

Returns one room with its bookings for the requested date. If `date` is omitted, use today's date. Return the bookings in time order.

**Response (200 OK):**

```json
{
  "id": 1,
  "name": "Boardroom A",
  "floor": 2,
  "capacity": 8,
  "date": "2026-10-01",
  "bookings": [
    {
      "id": 10,
      "title": "Sprint Planning",
      "start_at": "2026-10-01T10:00",
      "end_at": "2026-10-01T11:00",
      "attendees": 5
    }
  ]
}
```

**Errors:** `400 Bad Request` for invalid input; `404 Not Found` if the room does not exist.

#### `POST /api/rooms`

Adds a room. `name`, `floor`, and `capacity` are required; `name` must be unique and `capacity` must be at least 1.

**Request body:**

```json
{
  "name": "Focus Pod 1",
  "floor": 1,
  "capacity": 4
}
```

**Success response (200 OK), example:**

```json
{
  "id": 2,
  "name": "Focus Pod 1",
  "floor": 1,
  "capacity": 4
}
```

**Error responses:**

- `400 Bad Request` if a required field is missing or input is invalid, including `capacity` less than 1.
- `409 Conflict` if the room name is already in use.

### B. Employees

#### `GET /api/employees`

Lists all employees.

**Response (200 OK):**

```json
[
  {
    "id": 1,
    "name": "Alex Chung",
    "email": "alex@company.com",
    "department": "Engineering"
  }
]
```

#### `GET /api/employees/{id}`

Returns one employee with their **upcoming** bookings. The booking details provide the room, date, and time for the Employee detail page.

**Response (200 OK):**

```json
{
  "id": 1,
  "name": "Alex Chung",
  "email": "alex@company.com",
  "department": "Engineering",
  "upcoming_bookings": [
    {
      "id": 12,
      "room_name": "Innovation Lab",
      "title": "Architecture Sync",
      "start_at": "2026-10-02T14:00",
      "end_at": "2026-10-02T15:00"
    }
  ]
}
```

**Errors:** `400 Bad Request` for invalid input; `404 Not Found` if the employee does not exist.

#### `POST /api/employees`

Adds an employee. `name`, `email`, and `department` are required. The email must contain `@` and be unique.

**Request body:**

```json
{
  "name": "Angad S.",
  "email": "angad@company.com",
  "department": "Product"
}
```

**Success response (200 OK), example:**

```json
{
  "id": 2,
  "name": "Angad S.",
  "email": "angad@company.com",
  "department": "Product"
}
```

**Error responses:**

- `400 Bad Request` if a required field is missing or the email is invalid.
- `409 Conflict` if the email is already in use.

### C. Bookings & Reports

#### `POST /api/bookings`

Books a room. The request includes `room_id`, `employee_id`, `title`, `start_at`, `end_at`, and `attendees`.

**Request body:**

```json
{
  "room_id": 1,
  "employee_id": 1,
  "title": "Project Review",
  "start_at": "2026-10-01T10:00",
  "end_at": "2026-10-01T11:00",
  "attendees": 4
}
```

**Rules enforced:**

1. **No overlap:** A room cannot have two bookings at the same time that are not cancelled. Back-to-back bookings (e.g., 10:00–11:00 and 11:00–12:00) are allowed.
2. **Capacity:** `attendees` must be between 1 and the room's capacity.
3. **Valid time range:** `start_at` must be before `end_at`, and a booking may last at most 4 hours.
4. **Office hours:** A booking must start and end on the same day, between 08:00 and 18:00.
5. **No past bookings:** `start_at` must be in the future.

**Success response (200 OK), example:**

```json
{
  "id": 11,
  "room_id": 1,
  "employee_id": 1,
  "title": "Project Review",
  "start_at": "2026-10-01T10:00",
  "end_at": "2026-10-01T11:00",
  "attendees": 4,
  "cancelled_at": null
}
```

**Error responses:**

- `400 Bad Request` if a required field is missing or input is invalid, including an invalid time range.
- `404 Not Found` if the requested room or employee does not exist.
- `409 Conflict` for a booking rule violation, including overlap, capacity, office hours, or a start time in the past.

#### `POST /api/bookings/{id}/cancel`

Cancels a booking. Cancelling twice, or cancelling a booking that has already started, is rejected.

**Success response (200 OK):**

```json
{
  "message": "Booking cancelled successfully",
  "id": 10,
  "cancelled_at": "2026-09-25T10:15"
}
```

**Error responses:**

- `404 Not Found` if the booking does not exist.
- `409 Conflict` if the booking has already started or has already been cancelled.

#### `GET /api/bookings?date=YYYY-MM-DD&room_id=`

Lists bookings that are not cancelled for the specified date. `room_id` is an optional filter.

**Response (200 OK):**

```json
[
  {
    "id": 10,
    "room_id": 1,
    "room_name": "Innovation Lab",
    "employee_name": "Alex Chung",
    "title": "Sprint Planning",
    "start_at": "2026-10-01T10:00",
    "end_at": "2026-10-01T11:00",
    "attendees": 5
  }
]
```

#### `GET /api/reports/top-rooms?n=5`

Returns the `n` rooms with the most bookings that were not cancelled. Ties are sorted by room name A→Z.

**Response (200 OK):**

```json
[
  {
    "room_id": 1,
    "room_name": "Innovation Lab",
    "total_bookings": 14
  },
  {
    "room_id": 2,
    "room_name": "Zeus Boardroom",
    "total_bookings": 14
  }
]
```

## 3. Related Project Requirements

This API is used by the required HTML pages and shared frontend elements:

- `/rooms`: room table with name, floor, capacity, and available-now status; includes an Add room form.
- `/rooms/{id}`: room bookings for a chosen date, in time order.
- `/employees`: employee table and Add employee form.
- `/employees/{id}`: upcoming bookings with room, date, and time.
- `/bookings`: booking form with room and employee dropdowns, title, date, start time, end time, and attendees; booking list for a chosen date with a Cancel button on each upcoming booking; Top 5 rooms table.
- `/` redirects to `/rooms`.
- Shared base layout and navigation links **Rooms · Employees · Bookings**, one CSS file, and one shared way to display success and error messages.
- Invalid input, duplicate or invalid email, and booking rule violations display a clear error on the page.
- The API and pages use the same business-rule functions or service.
- The wider project also requires a seed script with sample rooms and employees, automated tests for every rule, and a README with one command to run the app and one command to run the tests.
