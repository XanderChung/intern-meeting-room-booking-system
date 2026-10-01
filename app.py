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
    return {"rooms": services.list_rooms(get_db())}

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
    values = {"name": "", "floor": "", "capacity": ""}

    if request.method == "POST":
        values = {
            field: request.form.get(field, "")
            for field in values
        }

        try:
            capacity = int(values["capacity"])
        except ValueError:
            flash("Capacity must be a whole number of at least 1.", "error")
        else:
            try:
                room = services.create_room(
                    values["name"],
                    values["floor"],
                    capacity,
                    get_db(),
                )
            except APIError as error:
                flash(error.message, "error")
            else:
                flash(f"Room '{room['name']}' was added successfully.", "success")
                return redirect(url_for("rooms_page"), code=303)

    rooms = services.list_rooms(get_db())
    return render_template("rooms.html", rooms=rooms, values=values)

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

@app.get("/api/employees/<int:employee_id>")
def employee_detail_api(employee_id):
    """Return an employee and their upcoming active bookings."""
    return services.get_employee_with_upcoming_bookings(
        employee_id=employee_id,
        db_connection=get_db(),
    )

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


@app.get("/api/reports/top-rooms")
def top_rooms_api():
    """Return rooms ranked by their active booking count."""
    return {
        "rooms": services.get_top_rooms(
            get_db(), n=request.args.get("n", default=5)
        )
    }


@app.get("/api/bookings")
def list_bookings_api():
    """List active bookings using the shared booking-list service."""
    return {
        "bookings": services.list_bookings(
            get_db(),
            date_value=request.args.get("date"),
            room_id=request.args.get("room_id"),
        )
    }


@app.post("/api/bookings/<int:booking_id>/cancel")
def cancel_booking_api(booking_id):
    """Cancel a booking through the shared cancellation service."""
    booking = services.cancel_booking(booking_id, db_connection=get_db())
    return {"booking": booking}


def _booking_page_values(date_value=None, room_id=None, *, show_filter_error=True):
    """Get page data and fall back to office today for invalid page filters."""
    office_now = services._now()
    office_today = office_now.date().isoformat()
    selected_date = date_value or office_today
    selected_room_id = room_id or ""

    try:
        bookings = services.list_bookings(
            get_db(),
            date_value=date_value,
            room_id=room_id,
            office_now=office_now,
        )
    except APIError as error:
        if show_filter_error:
            flash(error.message, "error")
        selected_date = office_today
        selected_room_id = ""
        bookings = services.list_bookings(
            get_db(), date_value=office_today, office_now=office_now
        )

    return {
        "bookings": bookings,
        "employees": services.list_employees(get_db()),
        "rooms": services.list_rooms(get_db()),
        "top_rooms": services.get_top_rooms(get_db()),
        "selected_date": selected_date,
        "selected_room_id": selected_room_id,
        "office_now": office_now.strftime("%Y-%m-%dT%H:%M"),
    }


@app.get("/bookings")
def bookings_page():
    values = _booking_page_values(
        date_value=request.args.get("date"),
        room_id=request.args.get("room_id"),
    )
    return render_template("bookings.html", **values, form_data={})


def _form_integer(field_name):
    raw_value = request.form.get(field_name, "")
    try:
        return int(raw_value)
    except (TypeError, ValueError) as error:
        label = field_name.replace("_", " ").capitalize()
        raise InvalidInputError(f"{label} must be an integer.") from error


@app.post("/bookings")
def create_booking_page():
    form_data = request.form
    date_value = form_data.get("date", "")
    try:
        start_time = form_data.get("start_time", "")
        end_time = form_data.get("end_time", "")
        booking = services.create_booking(
            room_id=_form_integer("room_id"),
            employee_id=_form_integer("employee_id"),
            title=form_data.get("title", ""),
            start_at=f"{date_value}T{start_time}",
            end_at=f"{date_value}T{end_time}",
            attendees=_form_integer("attendees"),
            db_connection=get_db(),
        )
    except APIError as error:
        flash(error.message, "error")
        values = _booking_page_values(
            date_value=date_value, show_filter_error=False
        )
        return render_template(
            "bookings.html", **values, form_data=form_data
        )

    flash(f"Booking \"{booking['title']}\" was created.", "success")
    return redirect(url_for("bookings_page", date=date_value))


@app.post("/bookings/<int:booking_id>/cancel")
def cancel_booking_page(booking_id):
    """Cancel a booking from the page and return to its current filters."""
    date_value = request.form.get("date", "")
    room_id = request.form.get("room_id", "")

    try:
        booking = services.cancel_booking(booking_id, db_connection=get_db())
    except APIError as error:
        flash(error.message, "error")
    else:
        flash(f'Booking "{booking["title"]}" was cancelled.', "success")

    return redirect(
        url_for("bookings_page", date=date_value, room_id=room_id),
        code=303,
    )


@app.get("/employees")
def employees_page():
    """Render the employee directory."""
    employees = services.list_employees(get_db())
    return render_template("employees.html", employees=employees)

@app.get("/employees/<int:employee_id>")
def employee_detail_page(employee_id):
    """Show an employee and their upcoming active bookings."""
    try:
        details = services.get_employee_with_upcoming_bookings(
            employee_id=employee_id,
            db_connection=get_db(),
        )
    except APIError as error:
        flash(error.message, "error")
        return render_template(
            "employee_detail.html",
            employee=None,
            bookings=[],
        ), error.status_code

    return render_template(
        "employee_detail.html",
        employee=details["employee"],
        bookings=details["bookings"],
    )

@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    init_db(app.config["DATABASE"])
    app.run()
