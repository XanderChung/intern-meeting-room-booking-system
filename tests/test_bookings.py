"""Service-level tests for the shared booking rules.

These tests call backend.services directly. HTTP status and JSON response tests
belong with the Flask routes when those routes are added.
"""

from datetime import datetime

import pytest

from backend import services
from errors import InvalidInputError, NotFoundError, RuleViolationError


# Booking times in this module are interpreted as Asia/Jakarta wall time.
# Freezing the clock keeps tests stable regardless of the device date/timezone.
OFFICE_NOW = datetime(2030, 1, 15, 7, 0)
BOOKING_DAY = "2030-01-15"


@pytest.fixture
def booking_records(db_connection):
    """Seed one room and one employee, leaving the connection idle for writes."""
    room_id = db_connection.execute(
        "INSERT INTO rooms (name, floor, capacity) VALUES (?, ?, ?)",
        ("Test Room", "2", 6),
    ).lastrowid
    employee_id = db_connection.execute(
        "INSERT INTO employees (name, email, department) VALUES (?, ?, ?)",
        ("Test Employee", "test@example.com", "Operations"),
    ).lastrowid
    db_connection.commit()
    return room_id, employee_id


def _booking_arguments(room_id, employee_id, **changes):
    """Build one valid default request, then override fields for a test case."""
    arguments = {
        "room_id": room_id,
        "employee_id": employee_id,
        "title": "Planning",
        "start_at": f"{BOOKING_DAY}T10:00",
        "end_at": f"{BOOKING_DAY}T11:00",
        "attendees": 6,
    }
    arguments.update(changes)
    return arguments


def _validate_booking(db_connection, room_id, employee_id, **changes):
    """Run the complete service validation pipeline with a fixed office clock."""
    return services.validate_booking(
        **_booking_arguments(room_id, employee_id, **changes),
        db_connection=db_connection,
        office_now=OFFICE_NOW,
    )


def _create_booking(db_connection, room_id, employee_id, **changes):
    """Create and commit a valid booking through the production service."""
    return services.create_booking(
        **_booking_arguments(room_id, employee_id, **changes),
        db_connection=db_connection,
        office_now=OFFICE_NOW,
    )


def test_validate_booking_accepts_a_valid_booking(db_connection, booking_records):
    room_id, employee_id = booking_records

    assert _validate_booking(db_connection, room_id, employee_id) is True


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("room_id", None),
        ("employee_id", None),
        ("title", "   "),
        ("start_at", None),
        ("end_at", ""),
        ("attendees", None),
        ("room_id", True),
        ("employee_id", 1.5),
        ("title", 123),
        ("start_at", 20300115),
        ("end_at", False),
        ("attendees", True),
        ("attendees", "2"),
    ],
)
def test_validate_booking_rejects_missing_or_wrong_typed_fields(
    db_connection, booking_records, field, invalid_value
):
    room_id, employee_id = booking_records

    with pytest.raises(InvalidInputError):
        _validate_booking(
            db_connection, room_id, employee_id, **{field: invalid_value}
        )


@pytest.mark.parametrize(
    ("room_id_override", "employee_id_override"),
    [
        (999, None),
        (None, 999),
    ],
)
def test_validate_booking_reports_missing_references(
    db_connection,
    booking_records,
    room_id_override,
    employee_id_override,
):
    room_id, employee_id = booking_records
    room_id = room_id if room_id_override is None else room_id_override
    employee_id = employee_id if employee_id_override is None else employee_id_override

    with pytest.raises(NotFoundError):
        _validate_booking(db_connection, room_id, employee_id)


@pytest.mark.parametrize("attendees", [1, 6])
def test_validate_booking_accepts_capacity_boundaries(
    db_connection, booking_records, attendees
):
    room_id, employee_id = booking_records

    assert _validate_booking(
        db_connection, room_id, employee_id, attendees=attendees
    )


def test_validate_booking_rejects_zero_attendees_as_invalid_input(
    db_connection, booking_records
):
    room_id, employee_id = booking_records

    with pytest.raises(InvalidInputError):
        _validate_booking(db_connection, room_id, employee_id, attendees=0)


def test_validate_booking_rejects_attendees_over_room_capacity(
    db_connection, booking_records
):
    room_id, employee_id = booking_records

    with pytest.raises(RuleViolationError):
        _validate_booking(db_connection, room_id, employee_id, attendees=7)


@pytest.mark.parametrize(
    "timestamp",
    ["2030-01-15 10:00", "2030-02-30T10:00", "2030-01-15T10:00:00"],
)
def test_check_time_range_rejects_malformed_timestamps(timestamp):
    with pytest.raises(InvalidInputError):
        services.check_time_range(timestamp, f"{BOOKING_DAY}T11:00")


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        (f"{BOOKING_DAY}T10:00", f"{BOOKING_DAY}T10:00"),
        (f"{BOOKING_DAY}T11:00", f"{BOOKING_DAY}T10:00"),
    ],
)
def test_time_order_is_invalid_in_range_and_overlap_checks(
    db_connection, booking_records, start_at, end_at
):
    room_id, _ = booking_records

    with pytest.raises(InvalidInputError):
        services.check_time_range(start_at, end_at)
    with pytest.raises(InvalidInputError):
        services.check_booking_overlap(room_id, start_at, end_at, db_connection)


def test_check_time_range_allows_exactly_four_hours():
    assert services.check_time_range(
        f"{BOOKING_DAY}T08:00", f"{BOOKING_DAY}T12:00"
    )


def test_check_time_range_rejects_more_than_four_hours():
    with pytest.raises(InvalidInputError):
        services.check_time_range(
            f"{BOOKING_DAY}T08:00", f"{BOOKING_DAY}T12:01"
        )


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        (f"{BOOKING_DAY}T08:00", f"{BOOKING_DAY}T12:00"),
        (f"{BOOKING_DAY}T14:00", f"{BOOKING_DAY}T18:00"),
    ],
)
def test_office_hour_boundaries_are_inclusive(start_at, end_at):
    assert services.check_office_hours(start_at, end_at)


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        (f"{BOOKING_DAY}T07:59", f"{BOOKING_DAY}T08:59"),
        (f"{BOOKING_DAY}T17:00", f"{BOOKING_DAY}T18:01"),
    ],
)
def test_check_office_hours_rejects_times_outside_the_window(start_at, end_at):
    with pytest.raises(RuleViolationError):
        services.check_office_hours(start_at, end_at)


def test_check_office_hours_rejects_cross_day_bookings():
    with pytest.raises(RuleViolationError):
        services.check_office_hours(
            f"{BOOKING_DAY}T17:00", "2030-01-16T09:00"
        )


def test_future_booking_check_uses_the_injected_office_clock():
    assert services.check_future_booking(
        f"{BOOKING_DAY}T07:01", office_now=OFFICE_NOW
    )


@pytest.mark.parametrize("start_at", [f"{BOOKING_DAY}T06:59", f"{BOOKING_DAY}T07:00"])
def test_future_booking_check_rejects_past_and_exactly_now(start_at):
    with pytest.raises(RuleViolationError):
        services.check_future_booking(start_at, office_now=OFFICE_NOW)


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        (f"{BOOKING_DAY}T10:30", f"{BOOKING_DAY}T11:30"),
        (f"{BOOKING_DAY}T09:30", f"{BOOKING_DAY}T10:30"),
        (f"{BOOKING_DAY}T09:00", f"{BOOKING_DAY}T12:00"),
        (f"{BOOKING_DAY}T10:15", f"{BOOKING_DAY}T10:45"),
        (f"{BOOKING_DAY}T10:00", f"{BOOKING_DAY}T11:00"),
    ],
)
def test_validate_booking_rejects_all_same_room_overlap_shapes(
    db_connection, booking_records, start_at, end_at
):
    room_id, employee_id = booking_records
    _create_booking(db_connection, room_id, employee_id)

    with pytest.raises(RuleViolationError):
        _validate_booking(
            db_connection,
            room_id,
            employee_id,
            start_at=start_at,
            end_at=end_at,
        )


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        (f"{BOOKING_DAY}T09:00", f"{BOOKING_DAY}T10:00"),
        (f"{BOOKING_DAY}T11:00", f"{BOOKING_DAY}T12:00"),
    ],
)
def test_back_to_back_bookings_are_allowed(
    db_connection, booking_records, start_at, end_at
):
    room_id, employee_id = booking_records
    _create_booking(db_connection, room_id, employee_id)

    assert _validate_booking(
        db_connection,
        room_id,
        employee_id,
        start_at=start_at,
        end_at=end_at,
    )


def test_same_time_in_another_room_is_allowed(db_connection, booking_records):
    room_id, employee_id = booking_records
    other_room_id = db_connection.execute(
        "INSERT INTO rooms (name, floor, capacity) VALUES (?, ?, ?)",
        ("Other Room", "3", 6),
    ).lastrowid
    db_connection.commit()
    _create_booking(db_connection, room_id, employee_id)

    assert _validate_booking(db_connection, other_room_id, employee_id)
