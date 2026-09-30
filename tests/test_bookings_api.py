"""API tests for creating bookings through the shared service."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import pytest

from app import app
from backend import services
from backend.db import get_connection, init_db


BOOKING = {
    "room_id": 1,
    "employee_id": 1,
    "title": "  Planning  ",
    "start_at": "2030-01-15T10:00",
    "end_at": "2030-01-15T11:00",
    "attendees": 6,
}


@pytest.fixture
def booking_api(tmp_path, monkeypatch):
    database_path = tmp_path / "booking-api.sqlite3"
    init_db(database_path)
    connection = get_connection(database_path)
    room = services.create_room("Test Room", "2", 6, connection)
    employee = services.create_employee(
        "Test Employee", "test@example.com", "Operations", connection
    )
    connection.close()

    monkeypatch.setitem(app.config, "DATABASE", database_path)
    monkeypatch.setitem(app.config, "TESTING", True)
    return app.test_client(), room["id"], employee["id"], database_path


def _payload(room_id=1, employee_id=1, **overrides):
    values = dict(BOOKING, room_id=room_id, employee_id=employee_id)
    values.update(overrides)
    return values


def test_create_booking_returns_201_envelope_and_persists(booking_api):
    client, room_id, employee_id, database_path = booking_api

    response = client.post(
        "/api/bookings", json=_payload(room_id=room_id, employee_id=employee_id)
    )

    assert response.status_code == 201
    booking = response.get_json()["booking"]
    assert booking == {
        "id": 1,
        "room_id": room_id,
        "employee_id": employee_id,
        "title": "Planning",
        "start_at": BOOKING["start_at"],
        "end_at": BOOKING["end_at"],
        "attendees": 6,
        "cancelled_at": None,
    }
    connection = get_connection(database_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1
    finally:
        connection.close()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"room_id": 1, "employee_id": 1, "title": "Planning"},
        _payload(attendees=True),
        _payload(start_at="2030-01-15T10:00", end_at="2030-01-15T10:00"),
    ],
)
def test_invalid_booking_input_returns_400(booking_api, payload):
    client, _, _, _ = booking_api

    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 400
    assert set(response.get_json()) == {"error"}


@pytest.mark.parametrize("raw_body", ["{", "[]"])
def test_non_object_or_malformed_json_returns_400(booking_api, raw_body):
    client, _, _, _ = booking_api

    response = client.post(
        "/api/bookings", data=raw_body, content_type="application/json"
    )

    assert response.status_code == 400
    assert set(response.get_json()) == {"error"}


@pytest.mark.parametrize(
    ("field", "unknown_id"),
    [("room_id", 999), ("employee_id", 999)],
)
def test_missing_room_or_employee_returns_404(booking_api, field, unknown_id):
    client, room_id, employee_id, _ = booking_api
    values = {"room_id": room_id, "employee_id": employee_id}
    values[field] = unknown_id

    response = client.post(
        "/api/bookings", json=_payload(**values)
    )

    assert response.status_code == 404
    assert set(response.get_json()) == {"error"}


def test_exceeding_room_capacity_returns_409(booking_api):
    client, room_id, employee_id, _ = booking_api

    response = client.post(
        "/api/bookings",
        json=_payload(room_id=room_id, employee_id=employee_id, attendees=7),
    )

    assert response.status_code == 409


def test_overlapping_booking_conflicts_but_back_to_back_booking_succeeds(
    booking_api,
):
    client, room_id, employee_id, _ = booking_api
    first = client.post(
        "/api/bookings", json=_payload(room_id=room_id, employee_id=employee_id)
    )
    overlap = client.post(
        "/api/bookings",
        json=_payload(
            room_id=room_id,
            employee_id=employee_id,
            start_at="2030-01-15T10:30",
            end_at="2030-01-15T11:30",
        ),
    )
    adjacent = client.post(
        "/api/bookings",
        json=_payload(
            room_id=room_id,
            employee_id=employee_id,
            start_at="2030-01-15T11:00",
            end_at="2030-01-15T12:00",
        ),
    )

    assert first.status_code == 201
    assert overlap.status_code == 409
    assert adjacent.status_code == 201


def test_cancelled_booking_does_not_block_slot_reuse(booking_api):
    client, room_id, employee_id, database_path = booking_api
    original = client.post(
        "/api/bookings", json=_payload(room_id=room_id, employee_id=employee_id)
    )
    booking_id = original.get_json()["booking"]["id"]
    connection = get_connection(database_path)
    try:
        connection.execute(
            "UPDATE bookings SET cancelled_at = ? WHERE id = ?",
            ("2030-01-15T09:00:00", booking_id),
        )
        connection.commit()
    finally:
        connection.close()

    reused = client.post(
        "/api/bookings", json=_payload(room_id=room_id, employee_id=employee_id)
    )

    assert original.status_code == 201
    assert reused.status_code == 201


def test_insert_failure_rolls_back_without_partial_booking(booking_api):
    client, _, _, database_path = booking_api
    connection = get_connection(database_path)
    try:
        connection.execute(
            """
            CREATE TRIGGER reject_booking_insert
            BEFORE INSERT ON bookings
            BEGIN
                SELECT RAISE(ABORT, 'forced insert failure');
            END
            """
        )
        connection.commit()
    finally:
        connection.close()

    response = client.post("/api/bookings", json=BOOKING)

    assert response.status_code == 409
    connection = get_connection(database_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 0
    finally:
        connection.close()


def test_competing_requests_cannot_double_book_the_same_slot(
    booking_api, monkeypatch
):
    _, room_id, employee_id, database_path = booking_api
    barrier = Barrier(2)
    original_create_booking = services.create_booking

    def synchronized_create_booking(*args, **kwargs):
        barrier.wait(timeout=10)
        return original_create_booking(*args, **kwargs)

    monkeypatch.setattr(services, "create_booking", synchronized_create_booking)

    def submit_booking():
        with app.test_client() as client:
            return client.post(
                "/api/bookings",
                json=_payload(room_id=room_id, employee_id=employee_id),
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: submit_booking(), range(2)))

    assert sorted(response.status_code for response in responses) == [201, 409]
    connection = get_connection(database_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1
    finally:
        connection.close()
