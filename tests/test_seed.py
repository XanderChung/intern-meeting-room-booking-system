from backend.db import get_connection
from seed import SAMPLE_EMPLOYEES, SAMPLE_ROOMS, seed_database


def test_seed_database_is_repeatable_and_preserves_custom_rows(tmp_path):
    db_path = tmp_path / "test.sqlite3"

    seed_database(db_path)

    connection = get_connection(db_path)
    try:
        connection.execute(
            "INSERT INTO rooms (name, floor, capacity) VALUES (?, ?, ?)",
            ("Custom Room", "4", 8),
        )
        connection.execute(
            "INSERT INTO employees (name, email, department) VALUES (?, ?, ?)",
            ("Custom Employee", "custom@example.com", "Finance"),
        )
        connection.commit()
    finally:
        connection.close()

    seed_database(db_path)

    connection = get_connection(db_path)
    try:
        for name, _, _ in SAMPLE_ROOMS:
            count = connection.execute(
                "SELECT COUNT(*) FROM rooms WHERE name = ?", (name,)
            ).fetchone()[0]
            assert count == 1

        for _, email, _ in SAMPLE_EMPLOYEES:
            count = connection.execute(
                "SELECT COUNT(*) FROM employees WHERE email = ?", (email,)
            ).fetchone()[0]
            assert count == 1

        assert connection.execute(
            "SELECT COUNT(*) FROM rooms WHERE name = ?", ("Custom Room",)
        ).fetchone()[0] == 1

        assert connection.execute(
            "SELECT COUNT(*) FROM employees WHERE email = ?",
            ("custom@example.com",),
        ).fetchone()[0] == 1
    finally:
        connection.close()