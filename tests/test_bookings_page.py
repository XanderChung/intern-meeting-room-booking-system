from datetime import datetime

from html import unescape

import pytest

from app import app
from backend import services
from backend.db import get_connection, init_db


OFFICE_NOW = datetime(2030, 1, 15, 7, 0)


@pytest.fixture
def bookings_page(tmp_path, monkeypatch):
    db_path = tmp_path / "bookings-page.sqlite3"
    init_db(db_path)
    db = get_connection(db_path)
    room = services.create_room("Boardroom", "2", 6, db)
    employee = services.create_employee(
        "Alex Lee", "alex@example.com", "Operations", db
    )
    db.close()

    monkeypatch.setitem(app.config, "DATABASE", db_path)
    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setattr(services, "_now", lambda office_now=None: OFFICE_NOW)
    return app.test_client(), room["id"], employee["id"], db_path


def _make_booking(db_path, room_id, employee_id, start_at, end_at, attendees=3):
    db = get_connection(db_path)
    try:
        return services.create_booking(
            room_id=room_id,
            employee_id=employee_id,
            title="Planning",
            start_at=start_at,
            end_at=end_at,
            attendees=attendees,
            db_connection=db,
            office_now=OFFICE_NOW,
        )
    finally:
        db.close()


def test_bookings_page_defaults_to_office_today_and_shows_empty_state(bookings_page):
    client, *_ = bookings_page
    response = client.get("/bookings")

    assert response.status_code == 200
    assert b"Bookings for 2030-01-15" in response.data
    assert b"No active bookings match this date and room." in response.data
    assert b"Boardroom (capacity 6)" in response.data
    assert b"Alex Lee" in response.data


def test_bookings_page_lists_selected_date_in_time_order(bookings_page):
    client, room_id, employee_id, db_path = bookings_page
    _make_booking(db_path, room_id, employee_id, "2030-01-15T11:00", "2030-01-15T12:00")
    _make_booking(db_path, room_id, employee_id, "2030-01-15T09:00", "2030-01-15T10:00")

    response = client.get("/bookings?date=2030-01-15")
    body = response.data.decode()

    assert response.status_code == 200
    assert body.index("09:00–10:00") < body.index("11:00–12:00")
    assert body.count("Planning") == 2


def test_booking_form_calls_shared_service_and_shows_success(bookings_page, monkeypatch):
    client, room_id, employee_id, db_path = bookings_page
    calls = []
    create_booking = services.create_booking

    def record_call(**kwargs):
        calls.append(kwargs.copy())
        return create_booking(**kwargs)

    monkeypatch.setattr(services, "create_booking", record_call)
    response = client.post(
        "/bookings",
        data={
            "room_id": str(room_id),
            "employee_id": str(employee_id),
            "title": "  Planning  ",
            "date": "2030-01-15",
            "start_time": "10:00",
            "end_time": "11:00",
            "attendees": "4",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["start_at"] == "2030-01-15T10:00"
    assert calls[0]["end_at"] == "2030-01-15T11:00"
    assert calls[0]["db_connection"] is not None
    assert b'class="notice notice--success"' in response.data
    assert 'Booking "Planning" was created.' in unescape(response.get_data(as_text=True))
    assert b"Planning" in response.data

    db = get_connection(db_path)
    try:
        assert db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1
    finally:
        db.close()


def test_booking_rule_error_is_visible_and_form_values_are_preserved(bookings_page):
    client, room_id, employee_id, _ = bookings_page
    response = client.post(
        "/bookings",
        data={
            "room_id": str(room_id),
            "employee_id": str(employee_id),
            "title": "Over capacity",
            "date": "2030-01-15",
            "start_time": "10:00",
            "end_time": "11:00",
            "attendees": "7",
        },
    )

    assert response.status_code == 200
    assert b'class="notice notice--error"' in response.data
    assert b"capacity" in response.data.lower()
    assert b'value="Over capacity"' in response.data


def test_invalid_page_filter_shows_error_and_falls_back_to_office_today(bookings_page):
    client, *_ = bookings_page
    response = client.get("/bookings?date=2030-02-30")

    assert response.status_code == 200
    assert b'class="notice notice--error"' in response.data
    assert b"Bookings for 2030-01-15" in response.data

