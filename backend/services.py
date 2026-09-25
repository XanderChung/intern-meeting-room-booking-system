"""
services.py
Centralized business rules and validation logic.
Both API endpoints and HTML routes MUST call these functions to enforce rules.
"""
from datetime import datetime, time


# ==========================================
# CUSTOM EXCEPTIONS
# ==========================================

class ConflictError(Exception):
    """
    Raised when a request conflicts with existing state.
    The API layer must map this exception to HTTP status code 409.
    """
    pass


# ==========================================
# ROOM & EMPLOYEE RULES
# ==========================================

def validate_employee_email(email: str, db_connection) -> bool:
    """
    Validates that an email contains an '@' symbol and is strictly unique in the database[cite: 2].
    Raises a ValueError if invalid or a ConflictError if it already exists[cite: 2].
    """
    if not email or "@" not in email:
        raise ValueError("Invalid email format: must contain '@'[cite: 2].")

    cursor = db_connection.cursor()
    cursor.execute("SELECT id FROM employees WHERE email = ?", (email,))
    if cursor.fetchone():
        raise ConflictError(f"An employee with email '{email}' already exists[cite: 2].")

    return True


# ==========================================
# BOOKING RULES
# ==========================================

def check_capacity(attendees: int, room_capacity: int) -> bool:
    """
    Ensures attendees are between 1 and the room's maximum capacity[cite: 2].
    Raises a ValueError if rules are violated[cite: 2].
    """
    if attendees < 1:
        raise ValueError("Attendee count must be at least 1[cite: 2].")
    if attendees > room_capacity:
        raise ValueError(f"Attendee count ({attendees}) exceeds room capacity ({room_capacity})[cite: 2].")
    
    return True


def check_time_range(start_at: str, end_at: str) -> bool:
    """
    Ensures start_at is strictly before end_at, and the booking lasts at most 4 hours[cite: 2].
    Both inputs are ISO 8601 strings (YYYY-MM-DDTHH:MM)[cite: 2].
    Raises a ValueError if violated[cite: 2].
    """
    start_dt = datetime.fromisoformat(start_at)
    end_dt = datetime.fromisoformat(end_at)

    if start_dt >= end_dt:
        raise ValueError("Booking start time must be strictly before end time[cite: 2].")

    duration_seconds = (end_dt - start_dt).total_seconds()
    if duration_seconds > 4 * 3600:
        raise ValueError("Booking duration cannot exceed 4 hours[cite: 2].")

    return True


def check_office_hours(start_at: str, end_at: str) -> bool:
    """
    Ensures the booking starts and ends on the exact same day, strictly between 08:00 and 18:00[cite: 2].
    Allows bookings to end at exactly 18:00[cite: 2].
    Raises a ValueError if outside office hours[cite: 2].
    """
    start_dt = datetime.fromisoformat(start_at)
    end_dt = datetime.fromisoformat(end_at)

    if start_dt.date() != end_dt.date():
        raise ValueError("Bookings must start and end on the exact same day[cite: 2].")

    office_start = time(8, 0)
    office_end = time(18, 0)

    if start_dt.time() < office_start:
        raise ValueError(f"Booking start time ({start_dt.time().strftime('%H:%M')}) cannot be before 08:00[cite: 2].")

    if end_dt.time() > office_end:
        raise ValueError(f"Booking end time ({end_dt.time().strftime('%H:%M')}) cannot be after 18:00[cite: 2].")

    return True


def check_future_booking(start_at: str) -> bool:
    """
    Ensures the start_at time is in the future compared to the server's current local time[cite: 2].
    Raises a ValueError if in the past[cite: 2].
    """
    start_dt = datetime.fromisoformat(start_at)
    if start_dt <= datetime.now():
        raise ValueError("Booking start time must be in the future[cite: 2].")

    return True


def check_booking_overlap(room_id: int, start_at: str, end_at: str, db_connection) -> bool:
    """
    Checks the database to ensure a room does not have two active (non-cancelled) 
    bookings at the same time[cite: 2]. 
    Back-to-back bookings (e.g., 10:00-11:00 and 11:00-12:00) DO NOT overlap[cite: 2].
    Raises a ConflictError if an overlap is detected[cite: 2].
    """
    cursor = db_connection.cursor()
    # Overlap formula: existing_start < new_end AND existing_end > new_start
    # Matches non-cancelled bookings where cancelled_at IS NULL
    query = """
        SELECT id FROM bookings
        WHERE room_id = ?
          AND cancelled_at IS NULL
          AND start_at < ?
          AND end_at > ?
    """
    cursor.execute(query, (room_id, end_at, start_at))
    if cursor.fetchone():
        raise ConflictError(f"Room {room_id} is already booked for the selected time slot[cite: 2].")

    return True


def check_cancel_validity(booking_id: int, db_connection) -> bool:
    """
    Ensures a booking can be cancelled[cite: 2]. It must be rejected if the booking 
    has already started, or if it was already cancelled previously[cite: 2].
    Raises a ValueError or ConflictError if invalid[cite: 2].
    """
    cursor = db_connection.cursor()
    cursor.execute("SELECT start_at, cancelled_at FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        raise ValueError(f"Booking with ID {booking_id} does not exist.")

    start_at_str, cancelled_at = booking

    if cancelled_at is not None:
        raise ConflictError(f"Booking {booking_id} has already been cancelled[cite: 2].")

    start_dt = datetime.fromisoformat(start_at_str)
    if datetime.now() >= start_dt:
        raise ValueError("Cannot cancel a booking that has already started or passed[cite: 2].")

    return True