from datetime import datetime

from backend import services
from backend.db import get_connection


def add_room(client, name="Boardroom", floor="2", capacity=6):
    connection = get_connection(client.application.config["DATABASE"])
    try:
        return services.create_room(name, floor, capacity, connection)
    finally:
        connection.close()


def test_rooms_api_returns_empty_list(client):
    response = client.get("/api/rooms")

    assert response.status_code == 200
    assert response.get_json() == {"rooms": []}


def test_rooms_api_lists_rooms_and_current_availability(client, monkeypatch):
    office_now = datetime(2026, 10, 1, 10, 30)
    monkeypatch.setattr(
        services,
        "_now",
        lambda office_now=None: datetime(2026, 10, 1, 10, 30),
    )

    occupied_room = add_room(client, "Boardroom")
    cancelled_booking_room = add_room(client, "Focus Room", floor="1", capacity=4)

    connection = get_connection(client.application.config["DATABASE"])
    try:
        employee = services.create_employee(
            "Alex Lee",
            "alex@example.com",
            "Operations",
            connection,
        )

        connection.execute(
            """
            INSERT INTO bookings
                (room_id, employee_id, title, start_at, end_at, attendees)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                occupied_room["id"],
                employee["id"],
                "Planning",
                "2026-10-01T10:00",
                "2026-10-01T11:00",
                2,
            ),
        )

        connection.execute(
            """
            INSERT INTO bookings
                (room_id, employee_id, title, start_at, end_at, attendees, cancelled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cancelled_booking_room["id"],
                employee["id"],
                "Cancelled meeting",
                "2026-10-01T10:00",
                "2026-10-01T11:00",
                2,
                "2026-10-01T09:00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    response = client.get("/api/rooms")

    assert response.status_code == 200
    availability = {
        room["name"]: room["available_now"]
        for room in response.get_json()["rooms"]
    }
    assert availability == {"Boardroom": False, "Focus Room": True}


def test_rooms_page_displays_room_details(client):
    add_room(client)

    response = client.get("/rooms")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Boardroom" in page
    assert "Capacity" in page
    assert "Available now" in page
    assert "Yes" in page