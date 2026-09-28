import os 
from pathlib import Path

from dotenv import load_dotenv 
from flask import Flask, redirect, render_template, url_for
from errors import register_error_handlers

#Read the .env file and load needed settings 
load_dotenv(Path(__file__).with_name(".env"))

#Creats a Flask object named "app"
app = Flask(__name__)

#Hand over the key to Flask 
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

#Stop program if Secret Key is not defined at the start with explaination 
if not app.config["SECRET_KEY"]: 
    raise RuntimeError("SECRET_KEY is missing. " \
    "Set it in your environment or local .env file.")


register_error_handlers(app)

@app.get("/")
def home():
    return redirect(url_for("rooms_page"))

@app.get("/rooms")
def rooms_page():
    return render_template("rooms.html")

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run()