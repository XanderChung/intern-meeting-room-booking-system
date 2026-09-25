"""
services.py
Centralized business rules and validation logic.
Both API endpoints and HTML routes MUST call these functions to enforce rules.
"""
from datetime import datetime, time

# Custom Exception for HTTP 409 mapping
class ConflictError(Exception):
    """Raised when a request conflicts with existing state (e.g., unique email, booking overlap)."""
    pass


# ==========================================
# ROOM & EMPLOYEE RULES
# ==========================================

def validate_employee_email(email: str, db_connection) -> bool:
    """
    Validates that an email contains an '@' symbol and is strictly unique in the database.
    Raises a ValueError if invalid or a ConflictError if it already exists.
    """
    if not email or "@" not in email:
        raise ValueError("Invalid email format: must contain '@'.")

    cursor = db_connection.cursor()
    cursor.execute("SELECT id FROM employees WHERE email = ?", (email,))
    if cursor.fetchone():
        raise ConflictError(f"An employee with email '{email}' already exists.")

    return True


# ==========================================
# BOOKING RULES
# ==========================================

def check_capacity(attendees: int, room_capacity: int) -> bool:
    """
    Ensures attendees are between 1 and the room's maximum capacity.
    Raises a ValueError if rules are violated.
    """
    if attendees < 1:
        raise ValueError("Attendee count must be at least 1.")
    if attendees > room_capacity:
        raise ValueError(f"Attendee count ({attendees}) exceeds room capacity ({room_capacity}).")
    
    return True


def check_time_range(start_at: str, end_at: str) -> bool:
    """
    Ensures start_at is strictly before end_at, and the booking lasts at most 4 hours.
    Both inputs are ISO 8601 strings (YYYY-MM-DDTHH:MM).
    Raises a ValueError if violated.
    """
    start_dt = datetime.fromisoformat(start_at)
    end_dt = datetime.fromisoformat(end_at)

    if start_dt >= end_dt:
        raise ValueError("Booking start time must be strictly before end time.")

    duration_seconds = (end_dt - start_dt).total_seconds()
    if duration_seconds > 4 * 3600:
        raise ValueError("Booking duration cannot exceed 4 hours.")

    return True


def check_office_hours(start_at: str, end_at: str) -> bool:
    """
    Ensures the booking starts and ends on the exact same day, strictly between 08:00 and 18:00.
    Raises a ValueError if outside office hours.
    """
    start_dt = datetime.fromisoformat(start_at)
    end_dt = datetime.fromisoformat(end_at)

    if start_dt.date() != end_dt.date():
        raise ValueError("Bookings must start and end on the exact same day.")

    office_start = time(8, 0)
    office_end = time(18, 0)

    if start_dt.time() < office_start or start_dt.time() > office_end:
        raise ValueError(f"Booking start time ({start_dt.time()}) must be within office hours (08:00 - 18:00).")

    if end_dt.time() < office_start or end_dt.time() > office_end:
        raise ValueError(f"Booking end time ({end_dt.time()}) must be within office hours (08:00 - 18:00).")

    return True


def check_future_booking(start_at: str) -> bool:
    """
    Ensures the start_at time is in the future compared to the server's current local time.
    Raises a ValueError if in the past.
    """
    start_dt = datetime.fromisoformat(start_at)
    if start_dt <= datetime.now():
        raise ValueError("Booking start time must be in the future.")

    return True


def check_booking_overlap(room_id: int, start_at: str, end_at: str, db_connection) -> bool:
    """
    Checks the database to ensure a room does not have two active (non-cancelled) 
    bookings at the same time. 
    Back-to-back bookings (e.g., 10:00-11:00 and 11:00-12:00) DO NOT overlap.
    Raises a ConflictError if an overlap is detected.
    """
    cursor = db_connection.cursor()
    # Overlap occurs if existing_start < new_end AND existing_end > new_start
    query = """
        SELECT id FROM bookings
        WHERE room_id = ?
          AND is_cancelled = 0
          AND start_at < ?
          AND end_at > ?
    """
    cursor.execute(query, (room_id, end_at, start_at))
    if cursor.fetchone():
        raise ConflictError(f"Room {room_id} is already booked for the selected time slot.")

    return True


def check_cancel_validity(booking_id: int, db_connection) -> bool:
    """
    Ensures a booking can be cancelled. It must be rejected if the booking 
    has already started, or if it was already cancelled previously.
    Raises a ValueError or ConflictError if invalid.
    """
    cursor = db_connection.cursor()
    cursor.execute("SELECT start_at, is_cancelled FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        raise ValueError(f"Booking with ID {booking_id} does not exist.")

    start_at_str, is_cancelled = booking

    if is_cancelled:
        raise ConflictError(f"Booking {booking_id} has already been cancelled.")

    start_dt = datetime.fromisoformat(start_at_str)
    if datetime.now() >= start_dt:
        raise ValueError("Cannot cancel a booking that has already started or passed.")

    return True