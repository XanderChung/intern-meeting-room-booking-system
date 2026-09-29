import sqlite3
from pathlib import Path


# The app's database will live in the project's instance folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "instance" / "meeting_rooms.sqlite3"

# Find schema.sql beside this file.
SCHEMA_PATH = Path(__file__).resolve().with_name("schema.sql")


def get_connection(db_path=DATABASE_PATH):
    """Open a database connection and enable foreign keys for it."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def init_db(db_path=DATABASE_PATH):
    """Create the database tables if they haven't been created yet."""
    connection = get_connection(db_path)

    try:
            schema = SCHEMA_PATH.read_text(encoding="utf-8")
            connection.executescript(schema)
    finally:
        connection.close()