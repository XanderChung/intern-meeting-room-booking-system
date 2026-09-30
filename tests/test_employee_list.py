import pytest

from app import app
from backend.db import get_connection, init_db


@pytest.fixture
def employee_client(tmp_path, monkeypatch):
    """Use an isolated, initially empty database for each page/API test."""
    db_path = tmp_path / "employees.sqlite3"
    monkeypatch.setitem(app.config, "DATABASE", db_path)
    monkeypatch.setitem(app.config, "TESTING", True)
    init_db(db_path)
    return app.test_client()


def add_employees(db_path):
    connection = get_connection(db_path)
    try:
        connection.executemany(
            """
            INSERT INTO employees (name, email, department)
            VALUES (?, ?, ?)
            """,
            [
                ("Maya Chen", "maya@example.com", "Finance"),
                ("Alex Lee", "alex@example.com", "Operations"),
            ],
        )
        connection.commit()
    finally:
        connection.close()


def test_employee_api_returns_empty_list(employee_client):
    response = employee_client.get("/api/employees")

    assert response.status_code == 200
    assert response.get_json() == {"employees": []}


def test_employees_page_shows_empty_state(employee_client):
    response = employee_client.get("/employees")

    assert response.status_code == 200
    assert "No employees have been added yet." in response.get_data(as_text=True)


def test_employee_api_returns_list_in_name_order(employee_client):
    add_employees(app.config["DATABASE"])
    response = employee_client.get("/api/employees")

    assert response.status_code == 200
    assert response.get_json() == {
        "employees": [
            {
                "id": 2,
                "name": "Alex Lee",
                "email": "alex@example.com",
                "department": "Operations",
            },
            {
                "id": 1,
                "name": "Maya Chen",
                "email": "maya@example.com",
                "department": "Finance",
            },
        ]
    }


def test_employees_page_renders_table_in_name_order(employee_client):
    add_employees(app.config["DATABASE"])
    response = employee_client.get("/employees")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<h2>Employees</h2>" in page
    assert '<th scope="col">Name</th>' in page
    assert "alex@example.com" in page
    assert "Operations" in page
    assert page.index("Alex Lee") < page.index("Maya Chen")
