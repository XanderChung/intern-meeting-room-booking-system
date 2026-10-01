"""Tests for the Top Rooms report API and Bookings page."""

from datetime import datetime

import pytest

from app import app
from backend import services
from backend.db import get_connection, init_db


OFFICE_NOW = datetime(2030, 1, 15, 7, 0)
ROOM_NAMES = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]


@pytest.fixture
def report_app(tmp_path, monkeypatch):
    db_path = tmp_path / "reports.sqlite3"
    init_db(db_path)
    db = get_connection(db_path)
    try:
        rooms = {
            name: services.create_room(name, "2", 6, db)["id"]
            for name in ROOM_NAMES
        }
        employee = services.create_employee(
            "Alex Lee", "alex@example.com", "Operations", db
        )
    finally:
        db.close()

    monkeypatch.setitem(app.config, "DATABASE", db_path)
    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setattr(services, "_now", lambda office_now=None: OFFICE_NOW)
    return app.test_client(), rooms, employee["id"], db_path


@pytest.fixture
def empty_report_app(tmp_path, monkeypatch):
    db_path = tmp_path / "empty-reports.sqlite3"
    init_db(db_path)
    monkeypatch.setitem(app.config, "DATABASE", db_path)
    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setattr(services, "_now", lambda office_now=None: OFFICE_NOW)
    return app.test_client()


def add_booking(db_path, room_id, employee_id, title, start, end, cancelled_at=None):
    db = get_connection(db_path)
    try:
        db.execute(
            """
            INSERT INTO bookings
                (room_id, employee_id, title, start_at, end_at, attendees, cancelled_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (room_id, employee_id, title, start, end, cancelled_at),
        )
        db.commit()
    finally:
        db.close()


def add_ranked_bookings(report_app):
    _, rooms, employee_id, db_path = report_app
    # Alpha has one four-hour booking. Beta and Gamma each have two active
    # bookings, so they rank higher by booking count rather than hours.
    add_booking(db_path, rooms["Alpha"], employee_id, "Long meeting",
                "2030-01-15T09:00", "2030-01-15T13:00")
    add_booking(db_path, rooms["Beta"], employee_id, "Beta one",
                "2030-01-15T09:00", "2030-01-15T10:00")
    add_booking(db_path, rooms["Beta"], employee_id, "Beta two",
                "2030-01-15T10:00", "2030-01-15T11:00")
    add_booking(db_path, rooms["Beta"], employee_id, "Cancelled",
                "2030-01-15T11:00", "2030-01-15T12:00",
                cancelled_at="2030-01-15T08:00:00")
    add_booking(db_path, rooms["Gamma"], employee_id, "Gamma one",
                "2030-01-15T09:00", "2030-01-15T10:00")
    add_booking(db_path, rooms["Gamma"], employee_id, "Gamma two",
                "2030-01-15T10:00", "2030-01-15T11:00")


def test_top_rooms_api_defaults_to_five_and_ranks_active_booking_counts(report_app):
    client, *_ = report_app
    add_ranked_bookings(report_app)

    response = client.get("/api/reports/top-rooms")

    assert response.status_code == 200
    rooms = response.get_json()["rooms"]
    assert [(room["name"], room["booking_count"]) for room in rooms] == [
        ("Beta", 2),
        ("Gamma", 2),
        ("Alpha", 1),
        ("Delta", 0),
        ("Epsilon", 0),
    ]
    assert len(rooms) == 5


def test_top_rooms_api_accepts_custom_positive_limit(report_app):
    client, *_ = report_app
    add_ranked_bookings(report_app)

    response = client.get("/api/reports/top-rooms?n=2")

    assert response.status_code == 200
    assert [room["name"] for room in response.get_json()["rooms"]] == [
        "Beta",
        "Gamma",
    ]


@pytest.mark.parametrize("n", ["0", "-1", "abc", "1.5", ""])
def test_top_rooms_api_rejects_invalid_limit(report_app, n):
    client, *_ = report_app

    response = client.get(f"/api/reports/top-rooms?n={n}")

    assert response.status_code == 400
    assert set(response.get_json()) == {"error"}


def test_top_rooms_api_returns_empty_list_when_database_has_no_rooms(empty_report_app):
    response = empty_report_app.get("/api/reports/top-rooms")

    assert response.status_code == 200
    assert response.get_json() == {"rooms": []}


def test_bookings_page_shows_top_five_in_service_order(report_app):
    client, *_ = report_app
    add_ranked_bookings(report_app)

    response = client.get("/bookings?date=2030-01-15")
    body = response.get_data(as_text=True)
    table = body.split('id="top-rooms-table"', 1)[1].split("</table>", 1)[0]

    assert response.status_code == 200
    assert "<h3 id=\"top-rooms-heading\">Top 5 rooms</h3>" in body
    assert table.index(">Beta</td>") < table.index(">Gamma</td>")
    assert ">2</td>" in table
    assert ">0</td>" in table
    assert "Zeta" not in table


def test_bookings_page_shows_report_empty_state_with_no_rooms(empty_report_app):
    response = empty_report_app.get("/bookings")

    assert response.status_code == 200
    assert b"No rooms to rank yet." in response.data

