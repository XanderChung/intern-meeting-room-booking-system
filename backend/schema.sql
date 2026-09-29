CREATE TABLE rooms (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL COLLATE NOCASE UNIQUE,
    floor    TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity >= 1)
);
CREATE TABLE employees (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL COLLATE NOCASE UNIQUE,
    department TEXT NOT NULL
);
CREATE TABLE bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id      INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    employee_id  INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    title        TEXT NOT NULL,
    start_at     TEXT NOT NULL,
    end_at       TEXT NOT NULL,
    attendees    INTEGER NOT NULL CHECK (attendees >= 1),
    cancelled_at TEXT NULL,
    CHECK (start_at < end_at)
);
CREATE INDEX bookings_room_time_idx
    ON bookings (room_id, start_at, end_at);
CREATE INDEX bookings_employee_time_idx
    ON bookings (employee_id, start_at);