"""
services.py
Centralized business rules and validation logic.
Both API endpoints and HTML routes MUST call these functions to enforce rules.
"""
from datetime import datetime

# ==========================================
# ROOM & EMPLOYEE RULES
# ==========================================

def validate_employee_email(email: str, db_connection) -> bool:
    """
    Validates that an email contains an '@' symbol and is strictly unique in the database[cite: 1].
    Raises a ValueError if invalid or a ConflictError if it already exists.
    """
    pass


# ==========================================
# BOOKING RULES
# ==========================================

def check_capacity(attendees: int, room_capacity: int) -> bool:
    """
    Ensures attendees are between 1 and the room's maximum capacity[cite: 1].
    Raises a ValueError if rules are violated.
    """
    pass

def check_time_range(start_at: str, end_at: str) -> bool:
    """
    Ensures start_at is strictly before end_at, and the booking lasts at most 4 hours[cite: 1].
    Both inputs are ISO 8601 strings (YYYY-MM-DDTHH:MM)[cite: 1].
    Raises a ValueError if violated.
    """
    pass

def check_office_hours(start_at: str, end_at: str) -> bool:
    """
    Ensures the booking starts and ends on the exact same day, strictly between 08:00 and 18:00[cite: 1].
    Raises a ValueError if outside office hours.
    """
    pass

def check_future_booking(start_at: str) -> bool:
    """
    Ensures the start_at time is in the future compared to the server's current local time[cite: 1].
    Raises a ValueError if in the past.
    """
    pass

def check_booking_overlap(room_id: int, start_at: str, end_at: str, db_connection) -> bool:
    """
    Checks the database to ensure a room does not have two active (non-cancelled) 
    bookings at the same time[cite: 1]. 
    Back-to-back bookings (e.g., 10:00-11:00 and 11:00-12:00) DO NOT overlap[cite: 1].
    Raises a ConflictError if an overlap is detected.
    """
    pass

def check_cancel_validity(booking_id: int, db_connection) -> bool:
    """
    Ensures a booking can be cancelled. It must be rejected if the booking 
    has already started, or if it was already cancelled previously[cite: 1].
    Raises a ValueError or ConflictError if invalid.
    """
    pass