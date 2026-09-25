from flask import Flask
from errors import register_error_handlers

app = Flask(__name__)
register_error_handlers(app)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run()