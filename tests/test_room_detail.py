from datetime import datetime

from backend import services
from backend.db import get_connection


def add_room_and_employee(client, room_name="Detail Test Room"):
    room_response = client.post(
        "/api/rooms",
        json={"name": room_name, "floor": "2", "capacity": 8},
    )
    employee_response = client.post(
        "/api/employees",
        json={
            "name": "Detail Test Employee",
            "email": "detail-test@example.com",
            "department": "Testing",
        },
    )

    assert room_response.status_code == 201
    assert employee_response.status_code == 201

    return (
        room_response.get_json()["room"],
        employee_response.get_json()["employee"],
    )


def insert_booking(client, room_id, employee_id, title, start_at, end_at,
                   cancelled_at=None):
    connection = get_connection(client.application.config["DATABASE"])
    try:
        connection.execute(
            """
            INSERT INTO bookings
                (room_id, employee_id, title, start_at, end_at,
                 attendees, cancelled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                room_id,
                employee_id,
                title,
                start_at,
                end_at,
                2,
                cancelled_at,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def test_room_detail_api_filters_and_orders_bookings_by_selected_date(client):
    room, employee = add_room_and_employee(client)

    # Insert the later meeting first to check that results are sorted by time.
    insert_booking(
        client, room["id"], employee["id"],
        "Later meeting", "2026-10-04T11:30", "2026-10-04T12:30",
    )
    insert_booking(
        client, room["id"], employee["id"],
        "Earlier meeting", "2026-10-04T08:00", "2026-10-04T09:00",
    )
    insert_booking(
        client, room["id"], employee["id"],
        "Cancelled meeting", "2026-10-04T09:00", "2026-10-04T10:00",
        cancelled_at="2026-10-03T12:00",
    )
    insert_booking(
        client, room["id"], employee["id"],
        "Different date", "2026-10-05T10:00", "2026-10-05T11:00",
    )

    response = client.get(f"/api/rooms/{room['id']}?date=2026-10-04")

    assert response.status_code == 200
    result = response.get_json()
    assert result["room"] == room
    assert result["date"] == "2026-10-04"
    assert [booking["title"] for booking in result["bookings"]] == [
        "Earlier meeting",
        "Later meeting",
    ]


def test_room_detail_api_defaults_to_today(client, monkeypatch):
    today = datetime(2026, 10, 4, 10, 0)
    monkeypatch.setattr(services, "_now", lambda office_now=None: today)

    room, employee = add_room_and_employee(client)
    insert_booking(
        client, room["id"], employee["id"],
        "Today's meeting", "2026-10-04T11:00", "2026-10-04T12:00",
    )

    response = client.get(f"/api/rooms/{room['id']}")

    assert response.status_code == 200
    result = response.get_json()
    assert result["date"] == "2026-10-04"
    assert [booking["title"] for booking in result["bookings"]] == [
        "Today's meeting"
    ]


def test_room_detail_api_returns_404_for_missing_room(client):
    response = client.get("/api/rooms/999999")

    assert response.status_code == 404
    assert "error" in response.get_json()


def test_room_detail_api_rejects_invalid_date(client):
    room, _ = add_room_and_employee(client)

    response = client.get(f"/api/rooms/{room['id']}?date=2026-02-30")

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_room_detail_page_shows_bookings_in_time_order(client):
    room, employee = add_room_and_employee(client)
    insert_booking(
        client, room["id"], employee["id"],
        "Later meeting", "2026-10-04T11:30", "2026-10-04T12:30",
    )
    insert_booking(
        client, room["id"], employee["id"],
        "Earlier meeting", "2026-10-04T08:00", "2026-10-04T09:00",
    )

    response = client.get(f"/rooms/{room['id']}?date=2026-10-04")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert room["name"] in page
    assert "2026-10-04" in page
    assert "08:00" in page
    assert "11:30" in page
    assert page.index("Earlier meeting") < page.index("Later meeting")


def test_room_detail_page_shows_empty_state_when_no_bookings(client):
    room, _ = add_room_and_employee(client)

    response = client.get(f"/rooms/{room['id']}?date=2026-10-04")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "No bookings for this date." in page