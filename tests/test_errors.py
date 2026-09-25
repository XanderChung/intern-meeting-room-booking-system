from flask import Flask
from errors import (
    InvalidInputError,
    NotFoundError,
    RuleViolationError,
    register_error_handlers,
)
from app import app as real_app


def get_error_response(error):
    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    register_error_handlers(test_app)

    @test_app.get("/test-error")
    def trigger_error():
        raise error

    client = test_app.test_client()
    return client.get("/test-error")


def test_invalid_input_returns_400():
    response = get_error_response(
        InvalidInputError("Name is required.")
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Name is required."}


def test_not_found_returns_404():
    response = get_error_response(
        NotFoundError("Room not found.")
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Room not found."}


def test_rule_violation_returns_409():
    response = get_error_response(
        RuleViolationError("This room is already booked.")
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "This room is already booked."
    }


def test_unknown_api_route_returns_json_404():
    response = real_app.test_client().get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.is_json
    assert response.get_json() == {
        "error": "The requested API endpoint was not found."
    }


def test_unknown_page_keeps_html_404():
    response = real_app.test_client().get("/does-not-exist")

    assert response.status_code == 404
    assert response.mimetype == "text/html"

def test_api_method_not_allowed_keeps_allow_header():
    test_app = Flask(__name__)
    register_error_handlers(test_app)

    @test_app.get("/api/only-get")
    def only_get():
        return {"ok": True}

    response = test_app.test_client().post("/api/only-get")

    assert response.status_code == 405
    assert response.is_json
    assert "GET" in response.headers["Allow"]
