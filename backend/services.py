"""Centralized business rules and validation logic.

Both API endpoints and HTML routes must call these functions to enforce rules.
"""
import re
from datetime import datetime, time


_DATETIME_FORMAT = "%Y-%m-%dT%H:%M"
_DATETIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z")


# ==========================================
# CUSTOM EXCEPTIONS
# ==========================================

class ConflictError(Exception):
    """Raised when a request conflicts with an existing rule or state (HTTP 409)."""


class NotFoundError(Exception):
    """Raised when a requested room, employee, or booking does not exist (HTTP 404)."""


def _parse_datetime(value: str) -> datetime:
    """Parse the contract's exact YYYY-MM-DDTHH:MM local-time format."""
    if not isinstance(value, str) or not _DATETIME_PATTERN.fullmatch(value):
        raise ValueError("Date and time must use YYYY-MM-DDTHH:MM format.")

    try:
        return datetime.strptime(value, _DATETIME_FORMAT)
    except ValueError as exc:
        raise ValueError("Date and time must be a valid YYYY-MM-DDTHH:MM value.") from exc


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


# ==========================================
# ROOM & EMPLOYEE RULES
# ==========================================

def validate_room(name: str, floor, capacity: int, db_connection) -> bool:
    """Validate the required room fields, minimum capacity, and unique name."""
    if _is_blank(name):
        raise ValueError("Room name is required.")
    if _is_blank(floor):
        raise ValueError("Room floor is required.")
    if capacity is None or capacity == "":
        raise ValueError("Room capacity is required.")
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError("Room capacity must be an integer of at least 1.")

    cursor = db_connection.cursor()
    cursor.execute("SELECT id FROM rooms WHERE name = ?", (name,))
    if cursor.fetchone():
        raise ConflictError(f"A room named '{name}' already exists.")

    return True


def validate_employee(name: str, email: str, department: str, db_connection) -> bool:
    """Validate required employee fields and the unique, valid email address."""
    if _is_blank(name):
        raise ValueError("Employee name is required.")
    if _is_blank(department):
        raise ValueError("Employee department is required.")

    return validate_employee_email(email, db_connection)


def validate_employee_email(email: str, db_connection) -> bool:
    """Require an email containing '@' and reject duplicates."""
    if not isinstance(email, str) or not email or "@" not in email:
        raise ValueError("Invalid email format: must contain '@'.")

    cursor = db_connection.cursor()
    cursor.execute("SELECT id FROM employees WHERE email = ?", (email,))
    if cursor.fetchone():
        raise ConflictError(f"An employee with email '{email}' already exists.")

    return True


# ==========================================
# BOOKING RULES
# ==========================================

def validate_booking_fields(room_id, employee_id, title, start_at, end_at, attendees) -> bool:
    """Require the fields used to create a booking."""
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
        raise ValueError(f"Missing required booking fields: {', '.join(missing)}.")

    return True


def validate_booking_references(room_id: int, employee_id: int, db_connection) -> bool:
    """Ensure the room and employee referenced by a booking exist."""
    cursor = db_connection.cursor()
    cursor.execute("SELECT id FROM rooms WHERE id = ?", (room_id,))
    if cursor.fetchone() is None:
        raise NotFoundError(f"Room {room_id} does not exist.")

    cursor.execute("SELECT id FROM employees WHERE id = ?", (employee_id,))
    if cursor.fetchone() is None:
        raise NotFoundError(f"Employee {employee_id} does not exist.")

    return True


def check_capacity(attendees: int, room_capacity: int) -> bool:
    """Require attendee count to be between 1 and the room's capacity."""
    if isinstance(attendees, bool) or not isinstance(attendees, int) or attendees < 1:
        raise ValueError("Attendee count must be an integer of at least 1.")
    if attendees > room_capacity:
        raise ConflictError(
            f"Attendee count ({attendees}) exceeds room capacity ({room_capacity})."
        )

    return True


def check_time_range(start_at: str, end_at: str) -> bool:
    """Require start before end and a duration of no more than four hours."""
    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at)

    if start_dt >= end_dt:
        raise ValueError("Booking start time must be before end time.")

    if (end_dt - start_dt).total_seconds() > 4 * 3600:
        raise ValueError("Booking duration cannot exceed 4 hours.")

    return True


def check_office_hours(start_at: str, end_at: str) -> bool:
    """Require a same-day booking from 08:00 through 18:00, inclusive."""
    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at)

    if start_dt.date() != end_dt.date():
        raise ConflictError("Bookings must start and end on the same day.")

    if start_dt.time() < time(8, 0) or end_dt.time() > time(18, 0):
        raise ConflictError("Bookings must be within office hours (08:00–18:00).")

    return True


def check_future_booking(start_at: str, office_now: datetime = None) -> bool:
    """Require a future start time using the office's local clock.

    Pass `office_now` when the server's local timezone is not the office timezone.
    """
    start_dt = _parse_datetime(start_at)
    now = office_now if office_now is not None else datetime.now()

    if start_dt <= now:
        raise ConflictError("Booking start time must be in the future.")

    return True


def check_booking_overlap(room_id: int, start_at: str, end_at: str, db_connection) -> bool:
    """Reject overlapping active bookings; back-to-back bookings are allowed."""
    # Parse first so only contract-format local timestamps reach the SQL comparison.
    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at)
    if start_dt >= end_dt:
        raise ValueError("Booking start time must be before end time.")

    cursor = db_connection.cursor()
    # Half-open interval check: touching endpoints are not overlaps.
    query = """
        SELECT id FROM bookings
        WHERE room_id = ?
          AND cancelled_at IS NULL
          AND start_at < ?
          AND end_at > ?
    """
    cursor.execute(query, (room_id, end_at, start_at))
    if cursor.fetchone():
        raise ConflictError(f"Room {room_id} is already booked for that time slot.")

    return True


def check_cancel_validity(
    booking_id: int, db_connection, office_now: datetime = None
) -> bool:
    """Reject missing, already-cancelled, or already-started bookings."""
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT start_at, cancelled_at FROM bookings WHERE id = ?", (booking_id,)
    )
    booking = cursor.fetchone()

    if booking is None:
        raise NotFoundError(f"Booking {booking_id} does not exist.")

    start_at_str, cancelled_at = booking
    if cancelled_at is not None:
        raise ConflictError(f"Booking {booking_id} has already been cancelled.")

    start_dt = _parse_datetime(start_at_str)
    now = office_now if office_now is not None else datetime.now()
    if now >= start_dt:
        raise ConflictError("Cannot cancel a booking that has already started.")

    return True
