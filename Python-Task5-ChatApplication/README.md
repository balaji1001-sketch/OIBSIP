# Task 5 · Chat Application (Advanced Tier)

A real-time, multi-room chat application: a threaded TCP server
(`socket` + `threading`, no external frameworks) and a tkinter GUI client,
with SQLite-backed accounts, rooms, and message history.

## Features

**Beginner tier** (subsumed by the advanced client below — the same
server/client pair satisfies both):

- Server listens for incoming connections; client connects over `localhost`
- Real-time, bidirectional messaging between connected clients
- Every message is timestamped (`[14:35] alice: hello`)
- Graceful disconnect handling — other clients in the room get a
  `"alice disconnected."` system notice the moment a connection drops

**Advanced tier:**

- tkinter GUI: connect screen → login/register screen → multi-room chat
  window
- Username + password accounts stored in SQLite, passwords hashed with
  PBKDF2-HMAC-SHA256 and a random per-user salt (never stored in plaintext)
- Multiple named chat rooms — create or join any room from the sidebar
- Message history: the last 50 messages in a room are sent to you the
  moment you join it
- In-app notification: when the window loses focus, new messages badge the
  room in the sidebar and flash the window title with an unread count
  (`(3) Chat - new message`) plus a bell sound
- Emoji shortcodes (`:smile:`, `:wave:`, `:fire:`, ...) are rendered to
  Unicode server-side, so they display correctly for everyone, including
  in reloaded history
- README security section below (as required)

## Setup

No third-party dependencies — everything used (`socket`, `threading`,
`sqlite3`, `tkinter`, `json`, `hashlib`) is in the Python standard library.

```bash
pip install -r requirements.txt   # no-op; documents that nothing external is needed
```

## Usage

1. Start the server (creates `chat.db` on first run, with a default
   `general` room):
   ```bash
   python server.py                      # binds 127.0.0.1:5555 by default
   python server.py --host 0.0.0.0 --port 6000   # to accept LAN connections
   ```
2. Start one or more clients (each opens its own window):
   ```bash
   python client_gui.py
   ```
3. In each client: enter the server's host/port and connect, then register
   a new account (or log in with one you already created).
4. Click a room in the sidebar to join it and see its history, or
   **+ New Room** to create one. Type a message and press Enter or click
   **Send**.
5. Try an emoji shortcode like `great job :thumbsup:` — it renders as 👍
   for everyone in the room.
6. Click away from the chat window, then send a message from another
   client — the unfocused window's title bar and room list will show an
   unread badge.

Run two or more `client_gui.py` instances on the same machine (all pointed
at `127.0.0.1:5555`) to see real-time chat between "two users" locally.

## Project Structure

```
Python-Task5-ChatApplication/
├── server.py             # Threaded TCP server: connections, rooms, broadcast, auth dispatch
├── client_gui.py         # tkinter client: connect/login/chat screens, background recv thread
├── protocol.py           # Newline-delimited JSON framing over raw sockets
├── db.py                 # SQLite: users (hashed passwords), rooms, message history
├── emoji_shortcodes.py   # :shortcode: -> Unicode emoji rendering
├── requirements.txt
└── details.txt            # Original task requirements
```

## Protocol

Every message is one JSON object per line (`{"type": ..., ...}\n`) sent
over a plain TCP socket. Client requests: `register`, `login`,
`list_rooms`, `create_room`, `join_room`, `leave_room`, `send_message`.
Server pushes: `auth_result`, `room_list`, `room_created`, `joined_room`
(includes history + current members), `message`, `system` (join/leave/
disconnect notices), `error`.

## Security transparency

This is a learning project, not a production chat system. Here's exactly
what's stored and what isn't protected:

**What's stored, and how:**

- **Passwords** are never stored in plaintext. Each is hashed with
  PBKDF2-HMAC-SHA256 (100,000 iterations) using a unique random 16-byte
  salt per user; only the hash and salt are written to `chat.db`.
- **Messages** are stored in `chat.db` as plain, unencrypted text —
  username, room, message body, and timestamp — indefinitely (there's no
  expiry or deletion). Anyone with file access to `chat.db` can read every
  message ever sent.
- **Room membership** (who's currently in which room) lives only in the
  server's memory and is lost on restart; only the room list and message
  history persist.

**What is explicitly NOT encrypted:**

- **The network connection is plain TCP with no TLS.** Usernames,
  passwords (during login/register), and every chat message travel over
  the wire completely unencrypted. Anyone who can observe traffic on the
  network path between client and server (e.g. packet capture on a shared
  Wi-Fi network) can read everything, including login credentials.
- This is safe for its intended use — `localhost` or a trusted private
  LAN for a class project — but this code should **not** be exposed to the
  public internet or used with real/reused passwords as-is. Adding TLS
  would mean wrapping the socket with Python's `ssl` module on both ends
  (`ssl.wrap_socket` / `SSLContext`), which is the natural next step if you
  wanted to harden this further.
- There is no rate limiting, no protection against a client flooding the
  server with connections or messages, and no input length limits — again,
  fine for local/trusted use, not for internet-facing deployment.

## Testing notes

Verified with real, unmocked sockets and SQLite (no external services
needed for this task, so everything could be tested directly):

- End-to-end via raw socket test clients: registration (incl. duplicate
  rejection), login success/failure, room creation (incl. duplicate
  rejection), joining, history reload on join, live broadcast between two
  connected clients, rejection of sends to an unjoined room, and the
  auth-required guard on room creation
- Found and fixed a real concurrency bug during testing: giving each
  client-handler thread its own SQLite connection caused spurious
  "database is locked" errors on this filesystem even without genuine
  concurrent writers — fixed by serializing all DB access through one
  shared connection guarded by a lock (see `db.py`)
- Found and fixed a real disconnect-detection bug: `socket.makefile()`'s
  buffered reader never detected the peer closing the connection on this
  platform (`readline()` blocked forever instead of returning at EOF),
  which silently broke the "notify on disconnect" feature entirely —
  fixed by reading raw bytes directly off the socket instead (`protocol.py`)
- Full GUI flow tested end-to-end with two live client windows against a
  real server: connect, register, join with history, live message
  exchange with server-side emoji rendering, unread-badge/title-flash
  notification when unfocused, room-creation broadcast to all clients, and
  the disconnect notice
