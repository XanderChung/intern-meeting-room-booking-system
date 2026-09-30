import os 
from pathlib import Path

from dotenv import load_dotenv 
from flask import Flask, g, redirect, render_template, url_for
from errors import register_error_handlers
from backend.db import DATABASE_PATH, get_connection, init_db
from backend import services

#Read the .env file and load needed settings 
load_dotenv(Path(__file__).with_name(".env"))

#Creats a Flask object named "app"
app = Flask(__name__)

#After creating the app, we configure the database 
app.config["DATABASE"] = DATABASE_PATH

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


#Hand over the key to Flask 
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

#Stop program if Secret Key is not defined at the start with explianation 
if not app.config["SECRET_KEY"]: 
    raise RuntimeError("SECRET_KEY is missing. " \
    "Set it in your environment or local .env file.")


register_error_handlers(app)

@app.get("/")
def home():
    return redirect(url_for("rooms_page"))

@app.get("/api/rooms")
def rooms_api():
    rooms = services.list_rooms(get_db())
    return {"rooms": rooms}


@app.get("/rooms")
def rooms_page():
    rooms = services.list_rooms(get_db())
    return render_template("rooms.html", rooms=rooms)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    init_db(app.config["DATABASE"])
    app.run()