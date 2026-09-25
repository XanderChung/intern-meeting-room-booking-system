"""Shared domain exceptions and Flask error-response handling."""

from flask import jsonify, request
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """A user-facing application error with an HTTP status code."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidInputError(APIError):
    """Malformed or missing request input (HTTP 400)."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class NotFoundError(APIError):
    """A requested room, employee, or booking does not exist (HTTP 404)."""

    def __init__(self, message: str):
        super().__init__(message, 404)


class RuleViolationError(APIError):
    """A valid request conflicts with a business rule (HTTP 409)."""

    def __init__(self, message: str):
        super().__init__(message, 409)


def _is_api_request() -> bool:
    return request.path == "/api" or request.path.startswith("/api/")


def register_error_handlers(app) -> None:
    """Register one JSON error shape for application and Flask API errors.

    HTML route handlers should catch APIError and pass its message to the
    shared page-message component. Unhandled API errors still use JSON.
    """

    @app.errorhandler(APIError)
    def handle_api_error(error):
        return jsonify(error=error.message), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if not _is_api_request():
            return error

        response = error.get_response()

        if error.code == 404:
            message = "The requested API endpoint was not found."
        elif error.code == 405:
            message = "Method not allowed for this API endpoint."
        else:
            message = error.description

        response.set_data(app.json.dumps({"error": message}))
        response.content_type = "application/json"
        return response
