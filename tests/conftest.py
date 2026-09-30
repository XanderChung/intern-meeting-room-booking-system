import os

# Give the test process its own key before any tests import app.py.
os.environ["SECRET_KEY"] = "test-only-key"

import pytest
from backend.db import get_connection, init_db


@pytest.fixture
def db_connection(tmp_path):
    """Give each test a fresh, separate SQLite database connection."""
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)

    connection = get_connection(db_path)
    yield connection
    connection.close()

@pytest.fixture
def client(tmp_path):
    """Give each test a Flask client with a fresh database."""
    from app import app

    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)

    previous_config = {
        "TESTING": app.config["TESTING"],
        "DATABASE": app.config["DATABASE"],
    }
    app.config.update(TESTING=True, DATABASE=db_path)

    try:
        with app.test_client() as test_client:
            yield test_client
    finally:
        app.config.update(previous_config)