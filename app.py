from flask import Flask, redirect, render_template, url_for
from errors import register_error_handlers
import os 

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
)
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