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