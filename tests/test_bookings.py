"""Focused service tests for booking time rules and room overlap."""

from datetime import datetime

import pytest

from backend import services
from errors import InvalidInputError, RuleViolationError


# Naive values here mean Asia/Jakarta wall time, as required by the contract.
OFFICE_NOW = datetime(2030, 1, 15, 7, 0)
BOOKING_DAY = "2030-01-15"


@pytest.fixture
def booking_context(db_connection):
    """Seed one room and employee, then leave the write-service connection idle."""
    room_id = db_connection.execute(
        "INSERT INTO rooms (name, floor, capacity) VALUES (?, ?, ?)",
        ("Test Room", "2", 6),
    ).lastrowid
    employee_id = db_connection.execute(
        "INSERT INTO employees (name, email, department) VALUES (?, ?, ?)",
        ("Test Employee", "test@example.com", "Operations"),
    ).lastrowid
    db_connection.commit()
    return db_connection, room_id, employee_id


def _arguments(room_id, employee_id, **changes):
    values = {
        "room_id": room_id,
        "employee_id": employee_id,
        "title": "Planning",
        "start_at": f"{BOOKING_DAY}T10:00",
        "end_at": f"{BOOKING_DAY}T11:00",
        "attendees": 6,
    }
    values.update(changes)
    return values


def _validate(context, **changes):
    connection, room_id, employee_id = context
    return services.validate_booking(
        **_arguments(room_id, employee_id, **changes),
        db_connection=connection,
        office_now=OFFICE_NOW,
    )


def _create(context, **changes):
    connection, room_id, employee_id = context
    return services.create_booking(
        **_arguments(room_id, employee_id, **changes),
        db_connection=connection,
        office_now=OFFICE_NOW,
    )


def test_valid_future_booking_passes_with_controlled_office_time(booking_context):
    assert _validate(booking_context) is True


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        ("2030-01-15 10:00", f"{BOOKING_DAY}T11:00"),
        ("2030-02-30T10:00", f"{BOOKING_DAY}T11:00"),
        ("2030-01-15T10:00:00", f"{BOOKING_DAY}T11:00"),
        (f"{BOOKING_DAY}T10:00", f"{BOOKING_DAY}T10:00"),
        (f"{BOOKING_DAY}T11:00", f"{BOOKING_DAY}T10:00"),
    ],
)
def test_malformed_equal_or_reversed_intervals_are_invalid(
    booking_context, start_at, end_at
):
    connection, room_id, _ = booking_context

    with pytest.raises(InvalidInputError):
        services.check_time_range(start_at, end_at)
    with pytest.raises(InvalidInputError):
        services.check_booking_overlap(room_id, start_at, end_at, connection)


def test_exactly_four_hours_is_allowed():
    assert services.check_time_range(
        f"{BOOKING_DAY}T08:00", f"{BOOKING_DAY}T12:00"
    )


def test_more_than_four_hours_is_invalid():
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
def test_office_hours_include_eight_am_and_six_pm(start_at, end_at):
    assert services.check_office_hours(start_at, end_at)


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        (f"{BOOKING_DAY}T07:59", f"{BOOKING_DAY}T08:59"),
        (f"{BOOKING_DAY}T17:00", f"{BOOKING_DAY}T18:01"),
    ],
)
def test_times_outside_office_hours_conflict(start_at, end_at):
    with pytest.raises(RuleViolationError):
        services.check_office_hours(start_at, end_at)


def test_booking_must_start_and_end_on_the_same_day():
    with pytest.raises(RuleViolationError):
        services.check_office_hours(
            f"{BOOKING_DAY}T17:00", "2030-01-16T09:00"
        )


def test_future_start_uses_the_injected_jakarta_time():
    assert services.check_future_booking(
        f"{BOOKING_DAY}T07:01", office_now=OFFICE_NOW
    )


@pytest.mark.parametrize("start_at", [f"{BOOKING_DAY}T06:59", f"{BOOKING_DAY}T07:00"])
def test_past_and_exactly_now_starts_conflict(start_at):
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
def test_overlapping_active_intervals_conflict(booking_context, start_at, end_at):
    _create(booking_context)

    with pytest.raises(RuleViolationError):
        _validate(booking_context, start_at=start_at, end_at=end_at)


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        (f"{BOOKING_DAY}T09:00", f"{BOOKING_DAY}T10:00"),
        (f"{BOOKING_DAY}T11:00", f"{BOOKING_DAY}T12:00"),
    ],
)
def test_back_to_back_intervals_are_allowed(booking_context, start_at, end_at):
    _create(booking_context)
    assert _validate(booking_context, start_at=start_at, end_at=end_at)


def test_same_time_in_another_room_is_allowed(booking_context):
    connection, _, employee_id = booking_context
    other_room_id = connection.execute(
        "INSERT INTO rooms (name, floor, capacity) VALUES (?, ?, ?)",
        ("Other Room", "3", 6),
    ).lastrowid
    connection.commit()
    _create(booking_context)

    assert services.validate_booking(
        **_arguments(other_room_id, employee_id),
        db_connection=connection,
        office_now=OFFICE_NOW,
    )


def test_cancelled_booking_does_not_block_its_old_slot(booking_context):
    connection, _, _ = booking_context
    booking = _create(booking_context)
    services.cancel_booking(booking["id"], connection, office_now=OFFICE_NOW)

    assert _validate(booking_context)
