import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, url_for, request, jsonify, flash

from backend import services
from backend.db import DATABASE_PATH, get_connection, init_db
from errors import register_error_handlers, InvalidInputError, APIError

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

@app.get("/api/rooms")
def rooms_api():
    rooms = services.list_rooms(get_db())
    return {"rooms": rooms}

@app.post("/api/rooms")
def create_room_api():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise InvalidInputError("Request body must be a JSON object.")

    room = services.create_room(
        data.get("name"),
        data.get("floor"),
        data.get("capacity"),
        get_db(),
    )
    return jsonify(room=room), 201


@app.route("/rooms", methods=["GET", "POST"])
def rooms_page():
    if request.method == "POST":
        try:
            capacity = int(request.form.get("capacity", ""))
        except ValueError:
            flash("Capacity must be a whole number of at least 1.", "error")
            return redirect(url_for("rooms_page"))

        try:
            room = services.create_room(
                request.form.get("name"),
                request.form.get("floor"),
                capacity,
                get_db(),
            )
        except APIError as error:
            flash(error.message, "error")
        else:
            flash(f"Room '{room['name']}' was added successfully.", "success")

        return redirect(url_for("rooms_page"))

    rooms = services.list_rooms(get_db())
    return render_template("rooms.html", rooms=rooms)


@app.get("/api/employees")
def list_employees_api():
    """Return all employees using the shared employee-list service."""
    return {"employees": services.list_employees(get_db())}


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