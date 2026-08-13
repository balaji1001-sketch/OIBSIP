"""
Threaded TCP chat server.

Each connected client gets its own thread and its own SQLite connection
(sqlite3 connections aren't safe to share across threads). Room membership
is tracked in memory (`rooms: dict[str, set[ClientSession]]`) guarded by a
single lock, since broadcasting and join/leave can happen concurrently from
any client's thread.
"""

import argparse
import socket
import threading
import time

import db
import protocol
from emoji_shortcodes import render as render_emoji

HOST = "127.0.0.1"
PORT = 5555


class ClientSession:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.reader = protocol.make_reader(conn)
        self.username = None
        self.rooms = set()
        self.write_lock = threading.Lock()

    def send(self, message):
        with self.write_lock:
            try:
                protocol.send(self.conn, message)
            except OSError:
                pass  # socket already closed; the read loop will clean this session up


class ChatServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.rooms = {}  # room name -> set[ClientSession]
        self.rooms_lock = threading.Lock()
        self.db = db.Database()

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(f"[server] Listening on {self.host}:{self.port}")

        try:
            while True:
                conn, addr = server_socket.accept()
                session = ClientSession(conn, addr)
                thread = threading.Thread(target=self._handle_client, args=(session,), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print("\n[server] Shutting down.")
        finally:
            server_socket.close()

    def _handle_client(self, session):
        print(f"[server] {session.addr} connected")
        try:
            while True:
                message = protocol.receive(session.reader)
                if message is None:
                    break
                self._dispatch(session, message)
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            self._cleanup(session)
            session.conn.close()
            print(f"[server] {session.addr} disconnected")

    def _dispatch(self, session, message):
        msg_type = message.get("type")
        handler = {
            "register": self._handle_register,
            "login": self._handle_login,
            "list_rooms": self._handle_list_rooms,
            "create_room": self._handle_create_room,
            "join_room": self._handle_join_room,
            "leave_room": self._handle_leave_room,
            "send_message": self._handle_send_message,
        }.get(msg_type)

        if handler is None:
            session.send({"type": "error", "message": f"Unknown request type: {msg_type!r}"})
            return
        handler(session, message)

    # --- Handlers ---

    def _handle_register(self, session, message):
        username = (message.get("username") or "").strip()
        password = message.get("password") or ""
        if not username or not password:
            session.send({"type": "auth_result", "ok": False, "error": "Username and password are required."})
            return
        if self.db.create_user(username, password):
            session.username = username
            session.send({"type": "auth_result", "ok": True, "username": username})
        else:
            session.send({"type": "auth_result", "ok": False, "error": "That username is already taken."})

    def _handle_login(self, session, message):
        username = (message.get("username") or "").strip()
        password = message.get("password") or ""
        if self.db.verify_user(username, password):
            session.username = username
            session.send({"type": "auth_result", "ok": True, "username": username})
        else:
            session.send({"type": "auth_result", "ok": False, "error": "Incorrect username or password."})

    def _handle_list_rooms(self, session, _message):
        session.send({"type": "room_list", "rooms": self.db.list_rooms()})

    def _handle_create_room(self, session, message):
        if not self._require_login(session):
            return
        room = (message.get("room") or "").strip()
        if not room:
            session.send({"type": "room_created", "ok": False, "error": "Room name can't be empty."})
            return
        ok = self.db.create_room(room, created_by=session.username)
        if ok:
            with self.rooms_lock:
                self.rooms.setdefault(room, set())
            self._broadcast_room_list()
        session.send({
            "type": "room_created", "ok": ok, "room": room,
            "error": None if ok else "That room already exists.",
        })

    def _handle_join_room(self, session, message):
        if not self._require_login(session):
            return
        room = (message.get("room") or "").strip()
        if not self.db.room_exists(room):
            session.send({"type": "error", "message": f"Room '{room}' doesn't exist."})
            return

        with self.rooms_lock:
            self.rooms.setdefault(room, set()).add(session)
            session.rooms.add(room)
            members = sorted(s.username for s in self.rooms[room] if s.username)

        history = self.db.get_recent_messages(room)
        session.send({"type": "joined_room", "room": room, "history": history, "members": members})
        self._broadcast(room, {
            "type": "system", "room": room,
            "text": f"{session.username} joined the room.",
            "timestamp": _now(),
        }, exclude=None)

    def _handle_leave_room(self, session, message):
        room = (message.get("room") or "").strip()
        self._remove_from_room(session, room)
        self._broadcast(room, {
            "type": "system", "room": room,
            "text": f"{session.username} left the room.",
            "timestamp": _now(),
        }, exclude=None)

    def _handle_send_message(self, session, message):
        if not self._require_login(session):
            return
        room = (message.get("room") or "").strip()
        text = (message.get("text") or "").strip()
        if not text:
            return
        if room not in session.rooms:
            session.send({"type": "error", "message": f"Join '{room}' before sending messages there."})
            return

        text = render_emoji(text)
        timestamp = _now()
        self.db.save_message(room, session.username, text, timestamp)
        self._broadcast(room, {
            "type": "message", "room": room, "username": session.username,
            "text": text, "timestamp": timestamp,
        }, exclude=None)

    # --- Helpers ---

    def _require_login(self, session):
        if session.username:
            return True
        session.send({"type": "error", "message": "You must log in first."})
        return False

    def _broadcast(self, room, message, exclude=None):
        with self.rooms_lock:
            members = list(self.rooms.get(room, ()))
        for member in members:
            if member is not exclude:
                member.send(message)

    def _broadcast_room_list(self):
        rooms = self.db.list_rooms()
        with self.rooms_lock:
            all_sessions = {s for members in self.rooms.values() for s in members}
        for session in all_sessions:
            session.send({"type": "room_list", "rooms": rooms})

    def _remove_from_room(self, session, room):
        with self.rooms_lock:
            if room in self.rooms:
                self.rooms[room].discard(session)
            session.rooms.discard(room)

    def _cleanup(self, session):
        rooms_to_notify = list(session.rooms)
        for room in rooms_to_notify:
            self._remove_from_room(session, room)
            if session.username:
                self._broadcast(room, {
                    "type": "system", "room": room,
                    "text": f"{session.username} disconnected.",
                    "timestamp": _now(),
                }, exclude=None)


def _now():
    return time.strftime("%H:%M:%S")


def main():
    parser = argparse.ArgumentParser(description="Threaded TCP chat server.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    ChatServer(args.host, args.port).start()


if __name__ == "__main__":
    main()
