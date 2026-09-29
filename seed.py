from backend.db import DATABASE_PATH, get_connection, init_db


SAMPLE_ROOMS = [
    ("Boardroom", "2", 12),
    ("Focus Room", "1", 4),
    ("Training Room", "3", 20),
]

SAMPLE_EMPLOYEES = [
    ("Alex Lee", "alex@example.com", "Operations"),
    ("Angad Sawhney", "angad@example.com", "Operations"),
]


def seed_database(db_path=DATABASE_PATH):
    """Create the tables and add sample records without deleting existing data."""
    init_db(db_path)
    connection = get_connection(db_path)

    try:
        connection.executemany(
            """
            INSERT OR IGNORE INTO rooms (name, floor, capacity)
            VALUES (?, ?, ?)
            """,
            SAMPLE_ROOMS,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO employees (name, email, department)
            VALUES (?, ?, ?)
            """,
            SAMPLE_EMPLOYEES,
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    seed_database()
    print("Sample rooms and employees are ready.")