import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, request, url_for

from backend import services
from backend.db import DATABASE_PATH, get_connection, init_db
from errors import APIError, InvalidInputError, register_error_handlers

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

@app.post("/api/employees")
def create_employee_api():
    """Validate and save a new employee through the shared service."""
    if not request.is_json:
        raise InvalidInputError("Send employee details as JSON.")

    data = request.get_json()

    if not isinstance(data, dict):
        raise InvalidInputError("The request body must be a JSON object.")

    employee = services.create_employee(
        name=data.get("name"),
        email=data.get("email"),
        department=data.get("department"),
        db_connection=get_db(),
    )

    return {"employee": employee}, 201

@app.post("/employees")
def create_employee_page():
    values = {
        "name": request.form.get("name", ""),
        "email": request.form.get("email", ""),
        "department": request.form.get("department", ""),
    }

    try:
        services.create_employee(
            name=values["name"],
            email=values["email"],
            department=values["department"],
            db_connection=get_db(),
        )
    except APIError as error:
        flash(error.message, "error")
        return render_template(
            "employees.html",
            employees=services.list_employees(get_db()),
            values=values,
        ), error.status_code

    flash("Employee added successfully.", "success")
    return redirect(url_for("employees_page"), code=303)

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
