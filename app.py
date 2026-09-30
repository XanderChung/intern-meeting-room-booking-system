import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, request, url_for

from backend import services
from backend.db import DATABASE_PATH, get_connection, init_db
from errors import InvalidInputError, register_error_handlers

# Read the .env file and load needed settings.
load_dotenv(Path(__file__).with_name(".env"))

app = Flask(__name__)
app.config["DATABASE"] = DATABASE_PATH

# Hand the key to Flask so session-based flash messages can work.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY is missing. Set it in your environment or local .env file."
    )

register_error_handlers(app)


def get_db():
    """Return this request's database connection, opening it if needed."""
    if "db_connection" not in g:
        g.db_connection = get_connection(app.config["DATABASE"])
    return g.db_connection


@app.teardown_appcontext
def close_db(error=None):
    """Close the request's database connection when the request ends."""
    connection = g.pop("db_connection", None)
    if connection is not None:
        connection.close()


@app.get("/")
def home():
    return redirect(url_for("rooms_page"))


@app.get("/rooms")
def rooms_page():
    return render_template("rooms.html")


@app.get("/api/employees")
def list_employees_api():
    """Return all employees using the shared employee-list service."""
    return {"employees": services.list_employees(get_db())}


@app.post("/api/bookings")
def create_booking_api():
    """Create a booking through the shared booking service."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise InvalidInputError("Request body must be a JSON object.")

    booking = services.create_booking(
        room_id=payload.get("room_id"),
        employee_id=payload.get("employee_id"),
        title=payload.get("title"),
        start_at=payload.get("start_at"),
        end_at=payload.get("end_at"),
        attendees=payload.get("attendees"),
        db_connection=get_db(),
    )
    return {"booking": booking}, 201


@app.get("/employees")
def employees_page():
    """Render the employee directory."""
    employees = services.list_employees(get_db())
    return render_template("employees.html", employees=employees)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    init_db(app.config["DATABASE"])
    app.run()
