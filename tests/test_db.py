from backend.db import get_connection, init_db


def test_init_db_creates_all_tables(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)

    connection = get_connection(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()

    assert {"rooms", "employees", "bookings"} <= tables


def test_each_connection_has_foreign_keys_enabled(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)

    connection = get_connection(db_path)
    try:
        foreign_keys_enabled = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]
    finally:
        connection.close()

    assert foreign_keys_enabled == 1