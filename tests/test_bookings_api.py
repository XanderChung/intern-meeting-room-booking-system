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


def _post_booking(client, room_id, employee_id, date, start, end):
    return client.post(
        "/api/bookings",
        json=payload(
            room_id,
            employee_id,
            start_at=f"{date}T{start}",
            end_at=f"{date}T{end}",
        ),
    )


def test_list_bookings_defaults_to_office_today_and_excludes_cancelled(booking_api):
    client, room_id, employee_id, path = booking_api
    earlier = _post_booking(
        client, room_id, employee_id, "2030-01-15", "09:00", "10:00"
    )
    cancelled = _post_booking(
        client, room_id, employee_id, "2030-01-15", "10:00", "11:00"
    )
    later = _post_booking(
        client, room_id, employee_id, "2030-01-15", "11:00", "12:00"
    )
    next_day = _post_booking(
        client, room_id, employee_id, "2030-01-16", "09:00", "10:00"
    )
    assert [earlier.status_code, cancelled.status_code, later.status_code, next_day.status_code] == [201] * 4

    db = get_connection(path)
    try:
        cancelled_id = cancelled.get_json()["booking"]["id"]
        db.execute(
            "UPDATE bookings SET cancelled_at = ? WHERE id = ?",
            ("2030-01-15T08:00:00", cancelled_id),
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/bookings")
    assert response.status_code == 200
    assert [row["start_at"] for row in response.get_json()["bookings"]] == [
        "2030-01-15T09:00",
        "2030-01-15T11:00",
    ]


def test_list_bookings_accepts_blank_date_and_room_filter(booking_api):
    client, room_id, employee_id, _ = booking_api
    _post_booking(client, room_id, employee_id, "2030-01-15", "09:00", "10:00")
    response = client.get(f"/api/bookings?date=&room_id={room_id}")

    assert response.status_code == 200
    assert len(response.get_json()["bookings"]) == 1
    assert response.get_json()["bookings"][0]["room_id"] == room_id


def test_list_bookings_unknown_room_returns_empty_list(booking_api):
    client, *_ = booking_api
    response = client.get("/api/bookings?date=2030-01-15&room_id=999")

    assert response.status_code == 200
    assert response.get_json() == {"bookings": []}


@pytest.mark.parametrize(
    "query",
    [
        "date=2030-02-30",
        "date=2030-01-15&room_id=0",
        "date=2030-01-15&room_id=abc",
    ],
)
def test_list_bookings_invalid_filters_return_standard_400(booking_api, query):
    client, *_ = booking_api
    response = client.get(f"/api/bookings?{query}")

    assert response.status_code == 400
    assert set(response.get_json()) == {"error"}




def test_cancel_booking_returns_updated_envelope_and_releases_slot(booking_api):
    client, room_id, employee_id, path = booking_api
    created = client.post("/api/bookings", json=payload(room_id, employee_id))
    booking_id = created.get_json()["booking"]["id"]

    response = client.post(f"/api/bookings/{booking_id}/cancel")

    assert response.status_code == 200
    cancelled = response.get_json()["booking"]
    assert cancelled["id"] == booking_id
    assert cancelled["title"] == "Planning"
    assert cancelled["cancelled_at"] == "2030-01-15T07:00:00"
    assert client.get("/api/bookings?date=2030-01-15").get_json() == {
        "bookings": []
    }

    db = get_connection(path)
    try:
        assert services.get_top_rooms(db)[0]["booking_count"] == 0
    finally:
        db.close()

    rebooked = client.post(
        "/api/bookings", json=payload(room_id, employee_id)
    )
    assert rebooked.status_code == 201


def test_cancel_unknown_booking_returns_404(booking_api):
    client, *_ = booking_api

    response = client.post("/api/bookings/999/cancel")

    assert response.status_code == 404
    assert set(response.get_json()) == {"error"}


def test_cancelling_booking_twice_returns_409(booking_api):
    client, room_id, employee_id, _ = booking_api
    created = client.post("/api/bookings", json=payload(room_id, employee_id))
    booking_id = created.get_json()["booking"]["id"]

    assert client.post(f"/api/bookings/{booking_id}/cancel").status_code == 200
    response = client.post(f"/api/bookings/{booking_id}/cancel")

    assert response.status_code == 409
    assert "already been cancelled" in response.get_json()["error"]


def test_cancelling_at_or_after_start_returns_409(booking_api, monkeypatch):
    client, room_id, employee_id, _ = booking_api
    created = client.post("/api/bookings", json=payload(room_id, employee_id))
    booking_id = created.get_json()["booking"]["id"]
    monkeypatch.setattr(
        services, "_now", lambda office_now=None: datetime(2030, 1, 15, 10, 0)
    )

    response = client.post(f"/api/bookings/{booking_id}/cancel")

    assert response.status_code == 409
    assert "already started" in response.get_json()["error"]
