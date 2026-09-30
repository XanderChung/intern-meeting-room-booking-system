from datetime import datetime
import pytest

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


@pytest.mark.parametrize(
    "payload",
    [
        {"floor": "2", "capacity": 6},  # missing name
        {"name": "Test Room", "capacity": 6},  # missing floor
        {"name": "Test Room", "floor": "2"},  # missing capacity
        {"name": "Test Room", "floor": "2", "capacity": 0},
        {"name": "Test Room", "floor": "2", "capacity": "6"},
        {"name": "Test Room", "floor": "2", "capacity": True},
    ],
)
def test_create_room_api_rejects_invalid_data(client, payload):
    response = client.post("/api/rooms", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_room_api_creates_room(client):
    response = client.post(
        "/api/rooms",
        json={"name": "A2 Test Room", "floor": "4", "capacity": 6},
    )

    assert response.status_code == 201
    assert response.get_json()["room"] == {
        "id": 1,
        "name": "A2 Test Room",
        "floor": "4",
        "capacity": 6,
    }


def test_create_room_api_rejects_duplicate_name_even_with_different_case(client):
    add_room(client, name="Boardroom")

    response = client.post(
        "/api/rooms",
        json={"name": "boardroom", "floor": "4", "capacity": 6},
    )

    assert response.status_code == 409
    assert "error" in response.get_json()


def test_rooms_form_creates_room_and_shows_success_message(client):
    response = client.post(
        "/rooms",
        data={"name": "A2 Test Room", "floor": "4", "capacity": "6"},
        follow_redirects=True,
    )
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "A2 Test Room" in page
    assert "was added successfully" in page


@pytest.mark.parametrize(
    ("form_data", "expected_message"),
    [
        (
            {"name": "", "floor": "4", "capacity": "6"},
            "Room name is required.",
        ),
        (
            {"name": "A2 Test Room", "floor": "", "capacity": "6"},
            "Room floor is required.",
        ),
        (
            {"name": "A2 Test Room", "floor": "4", "capacity": "not-a-number"},
            "Capacity must be a whole number of at least 1.",
        ),
    ],
)
def test_rooms_form_shows_error_for_invalid_data(
    client, form_data, expected_message
):
    response = client.post("/rooms", data=form_data, follow_redirects=True)

    assert response.status_code == 200
    assert expected_message in response.get_data(as_text=True)


def test_rooms_form_shows_error_for_duplicate_name(client):
    add_room(client, name="Boardroom")

    response = client.post(
        "/rooms",
        data={"name": "boardroom", "floor": "4", "capacity": "6"},
        follow_redirects=True,
    )
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "already exists" in page
    assert page.count("<td>Boardroom</td>") == 1