from datetime import datetime

from backend import services
from backend.db import get_connection

def test_employee_detail_without_bookings(client):
    created = client.post(
        "/api/employees",
        json={
            "name": "Detail Employee",
            "email": "detail@example.com",
            "department": "Testing",
        },
    )
    assert created.status_code == 201
    employee = created.get_json()["employee"]
    employee_id = employee["id"]

    response = client.get(f"/api/employees/{employee_id}")
    assert response.status_code == 200
    assert response.get_json() == {
        "employee": employee,
        "bookings": [],
    }

    page = client.get(f"/employees/{employee_id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Detail Employee" in html
    assert "detail@example.com" in html
    assert "Testing" in html
    assert "No upcoming bookings for this employee." in html
    assert 'href="/employees"' in html

    directory = client.get("/employees").get_data(as_text=True)
    assert f'href="/employees/{employee_id}"' in directory

def test_employee_detail_missing_employee(client):
    response = client.get("/api/employees/999999")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Employee 999999 does not exist."
    }

    page = client.get("/employees/999999")
    assert page.status_code == 404

def test_employee_detail_filters_and_orders_bookings(client, monkeypatch):
    fixed_now = datetime(2026, 10, 1, 10, 0)
    monkeypatch.setattr(
        services, "_now", lambda office_now=None: fixed_now
    )

    connection = get_connection(client.application.config["DATABASE"])
    try:
        room_id = connection.execute(
            "INSERT INTO rooms (name, floor, capacity) VALUES (?, ?, ?)",
            ("Test Boardroom", "2", 10),
        ).lastrowid

        employee_id = connection.execute(
            "INSERT INTO employees (name, email, department) VALUES (?, ?, ?)",
            ("Detail Employee", "detail@example.com", "Testing"),
        ).lastrowid

        other_id = connection.execute(
            "INSERT INTO employees (name, email, department) VALUES (?, ?, ?)",
            ("Other Employee", "other@example.com", "Testing"),
        ).lastrowid

        # Insert later booking first to check chronological ordering.
        bookings = [
            (employee_id, "Later meeting", "12:00", "13:00", None),
            (employee_id, "Earlier meeting", "11:00", "12:00", None),
            (employee_id, "Past meeting", "08:00", "09:00", None),
            (employee_id, "Ongoing meeting", "09:00", "10:30", None),
            (employee_id, "Starts now", "10:00", "11:00", None),
            (
                employee_id, "Cancelled meeting", "14:00", "15:00",
                "2026-10-01T09:00",
            ),
            (other_id, "Other employee meeting", "16:00", "17:00", None),
        ]

        for owner, title, start, end, cancelled in bookings:
            connection.execute(
                """
                INSERT INTO bookings
                    (room_id, employee_id, title, start_at, end_at,
                     attendees, cancelled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    room_id, owner, title,
                    f"2026-10-01T{start}", f"2026-10-01T{end}",
                    3, cancelled,
                ),
            )

        connection.commit()
    finally:
        connection.close()

    response = client.get(f"/api/employees/{employee_id}")
    assert response.status_code == 200
    result = response.get_json()

    assert result["employee"]["id"] == employee_id
    assert [booking["title"] for booking in result["bookings"]] == [
        "Earlier meeting",
        "Later meeting",
    ]
    for booking in result["bookings"]:
        assert booking["room_id"] == room_id
        assert booking["room_name"] == "Test Boardroom"
        assert booking["attendees"] == 3

    page = client.get(f"/employees/{employee_id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)

    assert "Test Boardroom" in html
    assert "2026-10-01T11:00" in html
    assert "2026-10-01T13:00" in html
    assert html.index("Earlier meeting") < html.index("Later meeting")

    for excluded in [
        "Past meeting",
        "Ongoing meeting",
        "Starts now",
        "Cancelled meeting",
        "Other employee meeting",
    ]:
        assert excluded not in html