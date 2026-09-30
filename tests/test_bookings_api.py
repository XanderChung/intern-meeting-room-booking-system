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
OFFICE_NOW = datetime(2030, 1, 15, 7, 0)


@pytest.fixture
def booking_api(tmp_path, monkeypatch):
    path = tmp_path / "booking-api.sqlite3"
    init_db(path)
    db = get_connection(path)
    room = services.create_room("Test Room", "2", 6, db)
    employee = services.create_employee("Test Employee", "test@example.com", "Ops", db)
    db.close()
    monkeypatch.setitem(app.config, "DATABASE", path)
    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setattr(services, "_now", lambda office_now=None: OFFICE_NOW)
    return app.test_client(), room["id"], employee["id"], path


def payload(room_id, employee_id, **changes):
    data = dict(BOOKING, room_id=room_id, employee_id=employee_id)
    data.update(changes)
    return data


def booking_count(path):
    db = get_connection(path)
    try:
        return db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    finally:
        db.close()


def test_create_booking_returns_documented_envelope_and_persists(booking_api):
    client, room_id, employee_id, path = booking_api
    response = client.post("/api/bookings", json=payload(room_id, employee_id))

    assert response.status_code == 201
    assert response.get_json()["booking"] == {
        "id": 1,
        "room_id": room_id,
        "employee_id": employee_id,
        "title": "Planning",
        "start_at": BOOKING["start_at"],
        "end_at": BOOKING["end_at"],
        "attendees": 6,
        "cancelled_at": None,
    }
    assert booking_count(path) == 1


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"room_id": 1, "employee_id": 1, "title": "Planning"},
        dict(BOOKING, attendees=True),
        dict(BOOKING, end_at=BOOKING["start_at"]),
        [],
    ],
)
def test_invalid_or_non_object_booking_data_returns_400(booking_api, body):
    client, *_ = booking_api
    response = client.post("/api/bookings", json=body)
    assert response.status_code == 400
    assert set(response.get_json()) == {"error"}

def test_malformed_json_returns_standard_400_error(booking_api):
    client, *_ = booking_api

    response = client.post(
        "/api/bookings",
        data='{"room_id": 1, "title": ',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Request body must be a JSON object."
    }

@pytest.mark.parametrize(
    ("field", "unknown_id"),
    [("room_id", 999), ("employee_id", 999)],
)
def test_missing_room_or_employee_returns_404(booking_api, field, unknown_id):
    client, room_id, employee_id, _ = booking_api
    ids = {"room_id": room_id, "employee_id": employee_id}
    ids[field] = unknown_id
    response = client.post("/api/bookings", json=payload(**ids))
    assert response.status_code == 404


def test_over_capacity_returns_409(booking_api):
    client, room_id, employee_id, _ = booking_api
    response = client.post(
        "/api/bookings",
        json=payload(room_id, employee_id, attendees=7),
    )
    assert response.status_code == 409


def test_overlap_conflicts_but_back_to_back_booking_succeeds(booking_api):
    client, room_id, employee_id, _ = booking_api
    assert client.post(
        "/api/bookings", json=payload(room_id, employee_id)
    ).status_code == 201
    overlap = client.post(
        "/api/bookings",
        json=payload(room_id, employee_id, start_at="2030-01-15T10:30",
                     end_at="2030-01-15T11:30"),
    )
    adjacent = client.post(
        "/api/bookings",
        json=payload(room_id, employee_id, start_at="2030-01-15T11:00",
                     end_at="2030-01-15T12:00"),
    )
    assert overlap.status_code == 409
    assert adjacent.status_code == 201


def test_cancelled_booking_does_not_block_slot_reuse(booking_api):
    client, room_id, employee_id, path = booking_api
    created = client.post("/api/bookings", json=payload(room_id, employee_id))
    db = get_connection(path)
    try:
        db.execute(
            "UPDATE bookings SET cancelled_at = ? WHERE id = ?",
            ("2030-01-15T09:00:00", created.get_json()["booking"]["id"]),
        )
        db.commit()
    finally:
        db.close()
    assert client.post(
        "/api/bookings", json=payload(room_id, employee_id)
    ).status_code == 201


def test_failed_insert_rolls_back_without_partial_booking(booking_api):
    client, _, _, path = booking_api
    db = get_connection(path)
    try:
        db.execute(
            """CREATE TRIGGER reject_booking BEFORE INSERT ON bookings
               BEGIN SELECT RAISE(ABORT, 'forced failure'); END"""
        )
        db.commit()
    finally:
        db.close()
    response = client.post("/api/bookings", json=BOOKING)
    assert response.status_code == 409
    assert booking_count(path) == 0


def test_competing_requests_cannot_double_book_a_slot(booking_api, monkeypatch):
    _, room_id, employee_id, path = booking_api
    barrier = Barrier(2)
    create = services.create_booking

    def simultaneous(*args, **kwargs):
        barrier.wait(timeout=10)
        return create(*args, **kwargs)

    monkeypatch.setattr(services, "create_booking", simultaneous)

    def submit():
        with app.test_client() as client:
            return client.post("/api/bookings", json=payload(room_id, employee_id))

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert booking_count(path) == 1
