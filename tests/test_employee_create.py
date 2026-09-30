import pytest
def test_create_employee_api(client):
    response = client.post(
        "/api/employees",
        json={
            "name": "Test Employee",
            "email": "test@example.com",
            "department": "Testing",
        },
    )

    assert response.status_code == 201

    employee = response.get_json()["employee"]
    assert employee["name"] == "Test Employee"
    assert employee["email"] == "test@example.com"
    assert employee["department"] == "Testing"

    list_response = client.get("/api/employees")
    assert list_response.status_code == 200
    assert list_response.get_json()["employees"] == [employee]

def test_create_employee_duplicate_email(client):
    details = {
        "name": "First Employee",
        "email": "test@example.com",
        "department": "Testing",
    }

    assert client.post("/api/employees", json=details).status_code == 201

    details["name"] = "Second Employee"
    response = client.post("/api/employees", json=details)

    assert response.status_code == 409
    assert "error" in response.get_json()

    employees = client.get("/api/employees").get_json()["employees"]
    assert len(employees) == 1
    assert employees[0]["name"] == "First Employee"

def test_create_employee_invalid_email(client):
    response = client.post(
        "/api/employees",
        json={
            "name": "Invalid Email Employee",
            "email": "invalid-email",
            "department": "Testing",
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()

    employees = client.get("/api/employees").get_json()["employees"]
    assert employees == []

@pytest.mark.parametrize("field", ["name", "email", "department"])
@pytest.mark.parametrize("value", ["", "   ", None, 123, False, [], {}])
def test_create_employee_invalid_field(client, field, value):
    details = {
        "name": "Test Employee",
        "email": "test@example.com",
        "department": "Testing",
    }
    details[field] = value

    response = client.post("/api/employees", json=details)

    assert response.status_code == 400
    assert "error" in response.get_json()
    assert client.get("/api/employees").get_json()["employees"] == []

def test_create_employee_form_success(client):
    response = client.post(
        "/employees",
        data={
            "name": "Form Employee",
            "email": "form@example.com",
            "department": "Testing",
        },
    )

    assert response.status_code == 303
    assert response.headers["Location"].endswith("/employees")

    page = client.get(response.headers["Location"])
    assert page.status_code == 200
    assert b"Employee added successfully." in page.data
    assert b"notice--success" in page.data
    assert b"Form Employee" in page.data

    # The success message should disappear on the next visit.
    next_page = client.get("/employees")
    assert b"Employee added successfully." not in next_page.data

def test_create_employee_form_error(client):
    response = client.post(
        "/employees",
        data={
            "name": "Form Employee",
            "email": "invalid-email",
            "department": "Testing",
        },
    )

    assert response.status_code == 400
    assert b"notice--error" in response.data
    assert b'value="Form Employee"' in response.data
    assert b'value="invalid-email"' in response.data
    assert b'value="Testing"' in response.data

    employees = client.get("/api/employees").get_json()["employees"]
    assert employees == []

def test_create_employee_form_duplicate_email(client):
    first = {
        "name": "First Employee",
        "email": "duplicate@example.com",
        "department": "First Department",
    }
    assert client.post("/employees", data=first).status_code == 303
    client.get("/employees")

    second = {
        "name": "Second Employee",
        "email": "duplicate@example.com",
        "department": "Second Department",
    }
    response = client.post("/employees", data=second)

    assert response.status_code == 409

    html = response.get_data(as_text=True)
    assert "notice--error" in html
    assert "already exists" in html

    for value in second.values():
        assert f'value="{value}"' in html

    employees = client.get("/api/employees").get_json()["employees"]
    assert len(employees) == 1
    assert employees[0]["name"] == first["name"]
    assert employees[0]["email"] == first["email"]
    assert employees[0]["department"] == first["department"]