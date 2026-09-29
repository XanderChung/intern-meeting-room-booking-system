import pytest

from app import app
from backend.db import get_connection, init_db


@pytest.fixture
def employee_client(tmp_path, monkeypatch):
    """Use an isolated database containing two employees for each route test."""
    db_path = tmp_path / "employees.sqlite3"
    monkeypatch.setitem(app.config, "DATABASE", db_path)
    monkeypatch.setitem(app.config, "TESTING", True)
    init_db(db_path)

    connection = get_connection(db_path)
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
    connection.close()

    return app.test_client()


def test_employee_api_returns_list_in_name_order(employee_client):
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


def test_employees_page_renders_employee_table(employee_client):
    response = employee_client.get("/employees")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<h2>Employees</h2>" in page
    assert "<th scope=\"col\">Name</th>" in page
    assert "Alex Lee" in page
    assert "alex@example.com" in page
    assert "Operations" in page
    assert page.index("Alex Lee") < page.index("Maya Chen")
