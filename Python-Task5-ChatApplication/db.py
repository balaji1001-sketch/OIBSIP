"""
SQLite persistence: users (with salted/hashed passwords), rooms, and message
history. See README's security section for exactly what this stores and how.

A single connection is shared by every client-handler thread, serialized
through one lock. Handing each thread its own connection to the same file
turned out to be unreliable on this filesystem (spurious "database is
locked" errors even without real concurrent writers) — serializing access
in Python sidesteps SQLite's cross-connection file-locking entirely.
"""

import hashlib
import os
import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "chat.db"

_PBKDF2_ITERATIONS = 100_000
DEFAULT_ROOM = "general"


class Database:
    def __init__(self, path=DB_PATH):
        self._conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    name TEXT PRIMARY KEY,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room TEXT NOT NULL,
                    username TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (room) REFERENCES rooms(name)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room, id);
                """
            )
            self._conn.commit()
            if not self._room_exists_locked(DEFAULT_ROOM):
                self._create_room_locked(DEFAULT_ROOM, created_by="system")

    def close(self):
        with self._lock:
            self._conn.close()

    # --- Users ---

    @staticmethod
    def _hash_password(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS).hex()

    def create_user(self, username, password):
        """Returns True on success, False if the username is already taken."""
        salt = os.urandom(16)
        password_hash = self._hash_password(password, salt)
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                    (username, password_hash, salt.hex(), _now()),
                )
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def verify_user(self, username, password):
        with self._lock:
            row = self._conn.execute(
                "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
            ).fetchone()
        if row is None:
            return False
        salt = bytes.fromhex(row["salt"])
        expected = self._hash_password(password, salt)
        return _constant_time_eq(expected, row["password_hash"])

    # --- Rooms ---

    def room_exists(self, room):
        with self._lock:
            return self._room_exists_locked(room)

    def _room_exists_locked(self, room):
        row = self._conn.execute("SELECT 1 FROM rooms WHERE name = ?", (room,)).fetchone()
        return row is not None

    def create_room(self, room, created_by):
        """Returns True on success, False if the room name is already taken."""
        with self._lock:
            return self._create_room_locked(room, created_by)

    def _create_room_locked(self, room, created_by):
        try:
            self._conn.execute(
                "INSERT INTO rooms (name, created_by, created_at) VALUES (?, ?, ?)",
                (room, created_by, _now()),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_rooms(self):
        with self._lock:
            rows = self._conn.execute("SELECT name FROM rooms ORDER BY name").fetchall()
        return [row["name"] for row in rows]

    # --- Messages ---

    def save_message(self, room, username, text, timestamp):
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages (room, username, text, timestamp) VALUES (?, ?, ?, ?)",
                (room, username, text, timestamp),
            )
            self._conn.commit()

    def get_recent_messages(self, room, limit=50):
        with self._lock:
            rows = self._conn.execute(
                "SELECT username, text, timestamp FROM messages WHERE room = ? "
                "ORDER BY id DESC LIMIT ?",
                (room, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]


def _constant_time_eq(a, b):
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")
