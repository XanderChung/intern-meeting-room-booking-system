"""Shared data and business services for the Flask API and HTML routes.

Route handlers should translate requests into calls to these functions. They
should not reimplement validation, booking rules, or database queries.
Write services own their transaction and require an idle SQLite connection.
"""

import re
import sqlite3
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from errors import InvalidInputError, NotFoundError, RuleViolationError


_DATETIME_FORMAT = "%Y-%m-%dT%H:%M"
_DATETIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z")
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
OFFICE_TIMEZONE = ZoneInfo("Asia/Jakarta")


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _now(office_now: datetime = None) -> datetime:
    """Return a naive datetime representing Asia/Jakarta office-local time.

    The default clock is derived from the configured IANA timezone rather than
    the computer's local timezone. Injected values are naive Asia/Jakarta wall
    times so callers can freeze the clock in tests.
    """
    value = (
        datetime.now(OFFICE_TIMEZONE).replace(tzinfo=None)
        if office_now is None
        else office_now
    )
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise InvalidInputError(
            "Office time must be a timezone-naive Asia/Jakarta datetime."
        )
    return value


def _parse_datetime(value: str) -> datetime:
    """Parse the contract's exact YYYY-MM-DDTHH:MM local-time format."""
    if not isinstance(value, str) or not _DATETIME_PATTERN.fullmatch(value):
        raise InvalidInputError("Date and time must use YYYY-MM-DDTHH:MM format.")
    try:
        return datetime.strptime(value, _DATETIME_FORMAT)
    except ValueError as exc:
        raise InvalidInputError(
            "Date and time must be a valid YYYY-MM-DDTHH:MM value."
        ) from exc


def _parse_date(value: str, *, office_now: datetime = None) -> date:
    """Parse a YYYY-MM-DD date, defaulting an omitted value to office today."""
    if value is None or value == "":
        return _now(office_now).date()
    if not isinstance(value, str) or not _DATE_PATTERN.fullmatch(value):
        raise InvalidInputError("Date must use YYYY-MM-DD format.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidInputError("Date must be a valid YYYY-MM-DD value.") from exc


def _positive_integer(value, field_name: str, *, allow_query_string=False) -> int:
    """Validate a positive integer, optionally accepting a URL query string."""
    if allow_query_string and isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidInputError(f"{field_name} must be a positive integer.")
    return value


def _dict_from_row(cursor, row):
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def _dicts_from_cursor(cursor):
    return [_dict_from_row(cursor, row) for row in cursor.fetchall()]


def _begin_write(db_connection) -> None:
    """Acquire SQLite's write lock before checking a write-time business rule."""
    if getattr(db_connection, "in_transaction", False):
        raise RuntimeError(
            "Write services require a SQLite connection with no active transaction."
        )
    db_connection.execute("BEGIN IMMEDIATE")


def _rollback(db_connection) -> None:
    if getattr(db_connection, "in_transaction", False):
        db_connection.rollback()


def _finish_write(db_connection) -> None:
    db_connection.commit()


# ---------------------------------------------------------------------------
# Room rules and services
# ---------------------------------------------------------------------------

def validate_room(name: str, floor, capacity: int, db_connection) -> bool:
    """Require a unique nonblank name, floor, and positive integer capacity.

    Room names are trimmed and compared case-insensitively, matching the
    database schema in docs/api.md.
    """
    if not isinstance(name, str) or not name.strip():
        raise InvalidInputError("Room name is required.")
    if not isinstance(floor, str) or not floor.strip():
        raise InvalidInputError("Room floor is required.")
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise InvalidInputError("Room capacity must be an integer of at least 1.")

    cursor = db_connection.execute(
        "SELECT id FROM rooms WHERE name = ? COLLATE NOCASE", (name.strip(),)
    )
    if cursor.fetchone():
        raise RuleViolationError(f"A room named '{name.strip()}' already exists.")
    return True


def list_rooms(db_connection, office_now: datetime = None) -> list[dict]:
    """List rooms with an availability flag evaluated at office-local now."""
    now_text = _now(office_now).strftime(_DATETIME_FORMAT)
    cursor = db_connection.execute(
        """
        SELECT r.id, r.name, r.floor, r.capacity,
               CASE WHEN EXISTS (
                   SELECT 1 FROM bookings b
                   WHERE b.room_id = r.id
                     AND b.cancelled_at IS NULL
                     AND b.start_at <= ?
                     AND b.end_at > ?
               ) THEN 0 ELSE 1 END AS available_now
        FROM rooms r
        ORDER BY r.name COLLATE NOCASE, r.name
        """,
        (now_text, now_text),
    )
    rooms = _dicts_from_cursor(cursor)
    for room in rooms:
        room["available_now"] = bool(room["available_now"])
    return rooms


def get_room_for_date(
    room_id: int, db_connection, date_value: str = None, office_now: datetime = None
) -> dict:
    """Return one room and its active bookings for a date, ordered by start."""
    room_id = _positive_integer(room_id, "room_id")
    chosen_date = _parse_date(date_value, office_now=office_now)
    day_start = f"{chosen_date.isoformat()}T00:00"
    next_day = f"{(chosen_date + timedelta(days=1)).isoformat()}T00:00"

    cursor = db_connection.execute(
        "SELECT id, name, floor, capacity FROM rooms WHERE id = ?", (room_id,)
    )
    row = cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Room {room_id} does not exist.")
    room = _dict_from_row(cursor, row)

    bookings_cursor = db_connection.execute(
        """
        SELECT b.id, b.room_id, b.employee_id, e.name AS employee_name,
               b.title, b.start_at, b.end_at, b.attendees
        FROM bookings b
        JOIN employees e ON e.id = b.employee_id
        WHERE b.room_id = ?
          AND b.cancelled_at IS NULL
          AND b.start_at >= ?
          AND b.start_at < ?
        ORDER BY b.start_at, b.id
        """,
        (room_id, day_start, next_day),
    )
    return {
        "room": room,
        "date": chosen_date.isoformat(),
        "bookings": _dicts_from_cursor(bookings_cursor),
    }


def create_room(name: str, floor, capacity: int, db_connection) -> dict:
    """Validate and insert a room as one serialized SQLite write."""
    _begin_write(db_connection)
    try:
        clean_name = name.strip() if isinstance(name, str) else name
        clean_floor = floor.strip() if isinstance(floor, str) else floor
        validate_room(clean_name, clean_floor, capacity, db_connection)
        cursor = db_connection.execute(
            "INSERT INTO rooms (name, floor, capacity) VALUES (?, ?, ?)",
            (clean_name, clean_floor, capacity),
        )
        room = {
            "id": cursor.lastrowid,
            "name": clean_name,
            "floor": clean_floor,
            "capacity": capacity,
        }
        _finish_write(db_connection)
        return room
    except sqlite3.IntegrityError as exc:
        _rollback(db_connection)
        raise RuleViolationError("Room name must be unique and capacity at least 1.") from exc
    except Exception:
        _rollback(db_connection)
        raise


# ---------------------------------------------------------------------------
# Employee rules and services
# ---------------------------------------------------------------------------

def validate_employee(name: str, email: str, department: str, db_connection) -> bool:
    """Require employee fields and a unique email containing '@'."""
    if not isinstance(name, str) or not name.strip():
        raise InvalidInputError("Employee name is required.")
    if not isinstance(department, str) or not department.strip():
        raise InvalidInputError("Employee department is required.")
    return validate_employee_email(email, db_connection)


def validate_employee_email(email: str, db_connection) -> bool:
    """Require an email containing '@' and enforce case-insensitive uniqueness."""
    if not isinstance(email, str) or not email.strip() or "@" not in email.strip():
        raise InvalidInputError("Invalid email format: must contain '@'.")
    clean_email = email.strip()
    cursor = db_connection.execute(
        "SELECT id FROM employees WHERE email = ? COLLATE NOCASE", (clean_email,)
    )
    if cursor.fetchone():
        raise RuleViolationError(f"An employee with email '{clean_email}' already exists.")
    return True


def list_employees(db_connection) -> list[dict]:
    """List all employees in name order."""
    cursor = db_connection.execute(
        "SELECT id, name, email, department FROM employees "
        "ORDER BY name COLLATE NOCASE, name, id"
    )
    return _dicts_from_cursor(cursor)


def get_employee_with_upcoming_bookings(
    employee_id: int, db_connection, office_now: datetime = None
) -> dict:
    """Return an employee and their active bookings whose start is in future."""
    employee_id = _positive_integer(employee_id, "employee_id")
    now_text = _now(office_now).strftime(_DATETIME_FORMAT)
    cursor = db_connection.execute(
        "SELECT id, name, email, department FROM employees WHERE id = ?",
        (employee_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Employee {employee_id} does not exist.")
    employee = _dict_from_row(cursor, row)

    bookings_cursor = db_connection.execute(
        """
        SELECT b.id, b.room_id, r.name AS room_name, b.title,
               b.start_at, b.end_at, b.attendees
        FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        WHERE b.employee_id = ?
          AND b.cancelled_at IS NULL
          AND b.start_at > ?
        ORDER BY b.start_at, b.id
        """,
        (employee_id, now_text),
    )
    return {"employee": employee, "bookings": _dicts_from_cursor(bookings_cursor)}


def create_employee(name: str, email: str, department: str, db_connection) -> dict:
    """Validate and insert an employee as one serialized SQLite write."""
    _begin_write(db_connection)
    try:
        clean_name = name.strip() if isinstance(name, str) else name
        clean_email = email.strip() if isinstance(email, str) else email
        clean_department = department.strip() if isinstance(department, str) else department
        validate_employee(clean_name, clean_email, clean_department, db_connection)
        cursor = db_connection.execute(
            "INSERT INTO employees (name, email, department) VALUES (?, ?, ?)",
            (clean_name, clean_email, clean_department),
        )
        employee = {
            "id": cursor.lastrowid,
            "name": clean_name,
            "email": clean_email,
            "department": clean_department,
        }
        _finish_write(db_connection)
        return employee
    except sqlite3.IntegrityError as exc:
        _rollback(db_connection)
        raise RuleViolationError("Employee email must be unique.") from exc
    except Exception:
        _rollback(db_connection)
        raise


# ---------------------------------------------------------------------------
# Booking rules and services
# ---------------------------------------------------------------------------

def validate_booking_fields(
    room_id, employee_id, title, start_at, end_at, attendees
) -> bool:
    """Validate required booking fields and their primitive types."""
    required = {
        "room_id": room_id,
        "employee_id": employee_id,
        "title": title,
        "start_at": start_at,
        "end_at": end_at,
        "attendees": attendees,
    }
    missing = [field for field, value in required.items() if _is_blank(value)]
    if missing:
        raise InvalidInputError(f"Missing required booking fields: {', '.join(missing)}.")
    _positive_integer(room_id, "room_id")
    _positive_integer(employee_id, "employee_id")
    if not isinstance(title, str):
        raise InvalidInputError("Booking title must be text.")
    if not isinstance(start_at, str) or not isinstance(end_at, str):
        raise InvalidInputError("Booking start_at and end_at must be text timestamps.")
    if isinstance(attendees, bool) or not isinstance(attendees, int):
        raise InvalidInputError("Attendees must be an integer.")
    return True


def validate_booking_references(room_id: int, employee_id: int, db_connection) -> bool:
    """Ensure the room and employee referenced by a booking exist."""
    room_id = _positive_integer(room_id, "room_id")
    employee_id = _positive_integer(employee_id, "employee_id")
    if db_connection.execute("SELECT 1 FROM rooms WHERE id = ?", (room_id,)).fetchone() is None:
        raise NotFoundError(f"Room {room_id} does not exist.")
    if (
        db_connection.execute("SELECT 1 FROM employees WHERE id = ?", (employee_id,)).fetchone()
        is None
    ):
        raise NotFoundError(f"Employee {employee_id} does not exist.")
    return True


def check_capacity(attendees: int, room_capacity: int) -> bool:
    """Require attendee count between one and the room's capacity."""
    if isinstance(attendees, bool) or not isinstance(attendees, int) or attendees < 1:
        raise InvalidInputError("Attendees must be an integer of at least 1.")
    if isinstance(room_capacity, bool) or not isinstance(room_capacity, int) or room_capacity < 1:
        raise InvalidInputError("Room capacity must be an integer of at least 1.")
    if attendees > room_capacity:
        raise RuleViolationError(
            f"Attendee count ({attendees}) exceeds room capacity ({room_capacity})."
        )
    return True


def check_time_range(start_at: str, end_at: str) -> bool:
    """Require start before end and a duration of no more than four hours."""
    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at)
    if start_dt >= end_dt:
        raise InvalidInputError("Booking start time must be before end time.")
    if (end_dt - start_dt) > timedelta(hours=4):
        raise InvalidInputError("Booking duration cannot exceed 4 hours.")
    return True


def check_office_hours(start_at: str, end_at: str) -> bool:
    """Require a same-day booking between 08:00 and 18:00, inclusive."""
    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at)
    if start_dt.date() != end_dt.date():
        raise RuleViolationError("Bookings must start and end on the same day.")
    if start_dt.time() < time(8, 0) or end_dt.time() > time(18, 0):
        raise RuleViolationError("Bookings must be within office hours (08:00–18:00).")
    return True


def check_future_booking(start_at: str, office_now: datetime = None) -> bool:
    """Require a future booking start using the office's local clock."""
    start_dt = _parse_datetime(start_at)
    if start_dt <= _now(office_now):
        raise RuleViolationError("Booking start time must be in the future.")
    return True


def check_booking_overlap(
    room_id: int, start_at: str, end_at: str, db_connection
) -> bool:
    """Reject overlapping active bookings; half-open intervals allow adjacency."""
    room_id = _positive_integer(room_id, "room_id")
    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at)
    if start_dt >= end_dt:
        raise InvalidInputError("Booking start time must be before end time.")
    cursor = db_connection.execute(
        """
        SELECT 1 FROM bookings
        WHERE room_id = ?
          AND cancelled_at IS NULL
          AND start_at < ?
          AND end_at > ?
        LIMIT 1
        """,
        (room_id, end_at, start_at),
    )
    if cursor.fetchone():
        raise RuleViolationError(f"Room {room_id} is already booked for that time slot.")
    return True


def validate_booking(
    room_id: int,
    employee_id: int,
    title: str,
    start_at: str,
    end_at: str,
    attendees: int,
    db_connection,
    office_now: datetime = None,
) -> bool:
    """Apply every booking rule in one place for both API and HTML handlers."""
    validate_booking_fields(room_id, employee_id, title, start_at, end_at, attendees)
    validate_booking_references(room_id, employee_id, db_connection)
    capacity_row = db_connection.execute(
        "SELECT capacity FROM rooms WHERE id = ?", (room_id,)
    ).fetchone()
    check_capacity(attendees, capacity_row[0])
    check_time_range(start_at, end_at)
    check_office_hours(start_at, end_at)
    check_future_booking(start_at, office_now)
    check_booking_overlap(room_id, start_at, end_at, db_connection)
    return True


def list_bookings(
    db_connection,
    date_value: str = None,
    room_id=None,
    office_now: datetime = None,
) -> list[dict]:
    """List active bookings for one date, optionally restricted to a room."""
    chosen_date = _parse_date(date_value, office_now=office_now)
    day_start = f"{chosen_date.isoformat()}T00:00"
    next_day = f"{(chosen_date + timedelta(days=1)).isoformat()}T00:00"
    sql = """
        SELECT b.id, b.room_id, r.name AS room_name,
               b.employee_id, e.name AS employee_name,
               b.title, b.start_at, b.end_at, b.attendees
        FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        JOIN employees e ON e.id = b.employee_id
        WHERE b.cancelled_at IS NULL
          AND b.start_at >= ?
          AND b.start_at < ?
    """
    parameters = [day_start, next_day]
    if room_id not in (None, ""):
        room_id = _positive_integer(room_id, "room_id", allow_query_string=True)
        sql += " AND b.room_id = ?"
        parameters.append(room_id)
    sql += " ORDER BY b.start_at, r.name COLLATE NOCASE, b.id"
    return _dicts_from_cursor(db_connection.execute(sql, parameters))


def create_booking(
    room_id: int,
    employee_id: int,
    title: str,
    start_at: str,
    end_at: str,
    attendees: int,
    db_connection,
    office_now: datetime = None,
) -> dict:
    """Validate and insert a booking atomically against concurrent requests.

    BEGIN IMMEDIATE serializes SQLite writers before the overlap check, so two
    requests cannot both pass the check and insert overlapping bookings.
    """
    _begin_write(db_connection)
    try:
        clean_title = title.strip() if isinstance(title, str) else title
        validate_booking(
            room_id,
            employee_id,
            clean_title,
            start_at,
            end_at,
            attendees,
            db_connection,
            office_now,
        )
        cursor = db_connection.execute(
            """
            INSERT INTO bookings
                (room_id, employee_id, title, start_at, end_at, attendees, cancelled_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (room_id, employee_id, clean_title, start_at, end_at, attendees),
        )
        booking = {
            "id": cursor.lastrowid,
            "room_id": room_id,
            "employee_id": employee_id,
            "title": clean_title,
            "start_at": start_at,
            "end_at": end_at,
            "attendees": attendees,
            "cancelled_at": None,
        }
        _finish_write(db_connection)
        return booking
    except sqlite3.IntegrityError as exc:
        _rollback(db_connection)
        raise RuleViolationError("Booking conflicts with existing data.") from exc
    except Exception:
        _rollback(db_connection)
        raise


def check_cancel_validity(
    booking_id: int, db_connection, office_now: datetime = None
) -> bool:
    """Reject missing, already-cancelled, or already-started bookings."""
    booking_id = _positive_integer(booking_id, "booking_id")
    booking = db_connection.execute(
        "SELECT start_at, cancelled_at FROM bookings WHERE id = ?", (booking_id,)
    ).fetchone()
    if booking is None:
        raise NotFoundError(f"Booking {booking_id} does not exist.")
    start_at, cancelled_at = booking
    if cancelled_at is not None:
        raise RuleViolationError(f"Booking {booking_id} has already been cancelled.")
    if _now(office_now) >= _parse_datetime(start_at):
        raise RuleViolationError("Cannot cancel a booking that has already started.")
    return True


def cancel_booking(
    booking_id: int, db_connection, office_now: datetime = None
) -> dict:
    """Cancel a booking once, only before its start, and return the updated row."""
    booking_id = _positive_integer(booking_id, "booking_id")
    _begin_write(db_connection)
    try:
        # Read the live clock after acquiring the write lock; lock contention
        # must not let a cancellation slip through after the meeting starts.
        cancellation_time = _now(office_now)
        check_cancel_validity(booking_id, db_connection, cancellation_time)
        cancelled_at = cancellation_time.isoformat(timespec="seconds")
        db_connection.execute(
            "UPDATE bookings SET cancelled_at = ? WHERE id = ?",
            (cancelled_at, booking_id),
        )
        row_cursor = db_connection.execute(
            """
            SELECT b.id, b.room_id, r.name AS room_name,
                   b.employee_id, e.name AS employee_name,
                   b.title, b.start_at, b.end_at, b.attendees, b.cancelled_at
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            JOIN employees e ON e.id = b.employee_id
            WHERE b.id = ?
            """,
            (booking_id,),
        )
        booking = _dict_from_row(row_cursor, row_cursor.fetchone())
        _finish_write(db_connection)
        return booking
    except Exception:
        _rollback(db_connection)
        raise


def get_top_rooms(db_connection, n=5) -> list[dict]:
    """Return rooms by active booking count, including zero-count rooms.

    Ties are sorted by room name A to Z. `n` may be an integer or a positive
    integer query-string value.
    """
    n = _positive_integer(n, "n", allow_query_string=True)
    cursor = db_connection.execute(
        """
        SELECT r.id, r.name, r.floor, r.capacity,
               COUNT(b.id) AS booking_count
        FROM rooms r
        LEFT JOIN bookings b
          ON b.room_id = r.id
         AND b.cancelled_at IS NULL
        GROUP BY r.id, r.name, r.floor, r.capacity
        ORDER BY booking_count DESC, r.name COLLATE NOCASE, r.name
        LIMIT ?
        """,
        (n,),
    )
    return _dicts_from_cursor(cursor)
