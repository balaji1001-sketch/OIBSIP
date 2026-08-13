"""
Chat Application - Advanced Tier - tkinter GUI client

Connects to server.py over a plain TCP socket, then walks through connect ->
login/register -> multi-room chat. Networking runs on a background thread
that pushes parsed messages into a queue; the GUI drains that queue on a
tkinter `after()` timer so widgets are only ever touched from the main
thread.
"""

import queue
import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, ttk

import protocol

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555

COLORS = {
    "bg": "#12131a",
    "card": "#1b1d29",
    "card_alt": "#242637",
    "border": "#2f3142",
    "text": "#e9e9f2",
    "muted": "#8d8fa3",
    "accent": "#6c63ff",
    "accent_hover": "#7d75ff",
    "accent_pressed": "#5a52e0",
    "danger": "#ef4444",
    "danger_bg": "#3a1d22",
    "system": "#f5a623",
}


class ChatClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat")
        self.root.minsize(760, 560)

        self.sock = None
        self.reader = None
        self.username = None

        self.all_rooms = []
        self.joined_rooms = set()
        self.active_room = None
        self.room_history = {}       # room -> list of rendered line strings
        self.unread_counts = {}      # room -> int

        self.incoming = queue.Queue()
        self.is_focused = True

        self._configure_styles()
        self.container = ttk.Frame(self.root, style="TFrame")
        self.container.pack(fill="both", expand=True)

        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._show_connect_screen()

    # --- Styling ---

    def _configure_styles(self):
        self.root.configure(bg=COLORS["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure("CardAlt.TFrame", background=COLORS["card_alt"])

        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Segoe UI", 9))

        style.configure("TEntry", fieldbackground=COLORS["card_alt"], foreground=COLORS["text"],
                         bordercolor=COLORS["border"], insertcolor=COLORS["text"], padding=8)

        style.configure("Accent.TButton", background=COLORS["accent"], foreground="white",
                         font=("Segoe UI", 10, "bold"), padding=10, borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", COLORS["accent_hover"]), ("pressed", COLORS["accent_pressed"])])

        style.configure("Secondary.TButton", background=COLORS["card_alt"], foreground=COLORS["text"],
                         font=("Segoe UI", 10), padding=9, borderwidth=1)
        style.map("Secondary.TButton", background=[("active", COLORS["border"])])

        style.configure("Room.TFrame", background=COLORS["card"])
        style.configure("RoomActive.TFrame", background=COLORS["accent"])

    def _clear_container(self):
        for child in self.container.winfo_children():
            child.destroy()

    # --- Screen 1: Connect ---

    def _show_connect_screen(self):
        self._clear_container()
        wrap = ttk.Frame(self.container, padding=32)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(wrap, text="💬 Chat", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(wrap, text="Connect to a chat server.", style="Subtitle.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(2, 16))

        ttk.Label(wrap, text="Host").grid(row=2, column=0, sticky="w", pady=4)
        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        ttk.Entry(wrap, textvariable=self.host_var, width=28).grid(row=2, column=1, pady=4, padx=(8, 0))

        ttk.Label(wrap, text="Port").grid(row=3, column=0, sticky="w", pady=4)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        ttk.Entry(wrap, textvariable=self.port_var, width=28).grid(row=3, column=1, pady=4, padx=(8, 0))

        self.connect_error_var = tk.StringVar(value="")
        ttk.Label(wrap, textvariable=self.connect_error_var, foreground=COLORS["danger"]).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Button(wrap, text="Connect", style="Accent.TButton", command=self._on_connect).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))

    def _on_connect(self):
        host = self.host_var.get().strip() or DEFAULT_HOST
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            self.connect_error_var.set("Port must be a number.")
            return

        try:
            self.sock = socket.create_connection((host, port), timeout=6)
            self.sock.settimeout(None)
        except OSError as exc:
            self.connect_error_var.set(f"Couldn't connect: {exc}")
            return

        self.reader = protocol.make_reader(self.sock)
        threading.Thread(target=self._recv_loop, daemon=True).start()
        self._poll_job = self.root.after(100, self._poll_queue)
        self._show_auth_screen()

    # --- Screen 2: Login / Register ---

    def _show_auth_screen(self):
        self._clear_container()
        wrap = ttk.Frame(self.container, padding=32)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(wrap, text="Log in or register", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        ttk.Label(wrap, text="Username").grid(row=1, column=0, sticky="w", pady=4)
        self.username_var = tk.StringVar()
        entry = ttk.Entry(wrap, textvariable=self.username_var, width=28)
        entry.grid(row=1, column=1, pady=4, padx=(8, 0))
        entry.focus_set()

        ttk.Label(wrap, text="Password").grid(row=2, column=0, sticky="w", pady=4)
        self.password_var = tk.StringVar()
        pw_entry = ttk.Entry(wrap, textvariable=self.password_var, show="•", width=28)
        pw_entry.grid(row=2, column=1, pady=4, padx=(8, 0))
        pw_entry.bind("<Return>", lambda _e: self._on_login())

        self.auth_error_var = tk.StringVar(value="")
        ttk.Label(wrap, textvariable=self.auth_error_var, foreground=COLORS["danger"]).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        btns = ttk.Frame(wrap)
        btns.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        btns.columnconfigure((0, 1), weight=1)
        ttk.Button(btns, text="Log In", style="Accent.TButton", command=self._on_login).grid(
            row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(btns, text="Register", style="Secondary.TButton", command=self._on_register).grid(
            row=0, column=1, sticky="ew", padx=(6, 0))

    def _on_login(self):
        self._send_auth("login")

    def _on_register(self):
        self._send_auth("register")

    def _send_auth(self, kind):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        if not username or not password:
            self.auth_error_var.set("Enter a username and password.")
            return
        self._send({"type": kind, "username": username, "password": password})

    def _handle_auth_result(self, message):
        if message.get("ok"):
            self.username = message["username"]
            self._send({"type": "list_rooms"})
            self._show_chat_screen()
        else:
            self.auth_error_var.set(message.get("error") or "Authentication failed.")

    # --- Screen 3: Chat ---

    def _show_chat_screen(self):
        self._clear_container()
        self.container.columnconfigure(1, weight=1)
        self.container.rowconfigure(0, weight=1)

        # Sidebar
        sidebar = ttk.Frame(self.container, style="Card.TFrame", padding=12)
        sidebar.grid(row=0, column=0, sticky="ns")

        ttk.Label(sidebar, text=f"👤 {self.username}", style="Card.TLabel", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 12))
        ttk.Label(sidebar, text="ROOMS", style="Muted.TLabel").pack(anchor="w")

        self.rooms_list_frame = ttk.Frame(sidebar, style="Card.TFrame")
        self.rooms_list_frame.pack(fill="both", expand=True, pady=(4, 12))

        ttk.Button(sidebar, text="+ New Room", style="Secondary.TButton", command=self._on_create_room).pack(
            fill="x")

        # Main panel
        main = ttk.Frame(self.container, padding=(16, 12))
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(2, weight=1)
        main.columnconfigure(0, weight=1)

        self.room_title_var = tk.StringVar(value="Select or create a room to get started")
        ttk.Label(main, textvariable=self.room_title_var, style="Title.TLabel", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w")

        self.chat_error_var = tk.StringVar(value="")
        self.chat_error_label = tk.Label(main, textvariable=self.chat_error_var, bg=COLORS["danger_bg"],
                                          fg=COLORS["danger"], anchor="w", padx=10, pady=6, font=("Segoe UI", 9))
        self.chat_error_label.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.chat_error_label.grid_remove()

        self.message_log = scrolledtext.ScrolledText(
            main, state="disabled", wrap="word", bg=COLORS["card"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 10), padx=10, pady=10,
        )
        self.message_log.grid(row=2, column=0, sticky="nsew", pady=(10, 10))
        self.message_log.tag_config("system", foreground=COLORS["system"], font=("Segoe UI", 9, "italic"))
        self.message_log.tag_config("me", foreground=COLORS["accent"], font=("Segoe UI", 10, "bold"))
        self.message_log.tag_config("other", foreground=COLORS["text"], font=("Segoe UI", 10, "bold"))
        self.message_log.tag_config("time", foreground=COLORS["muted"], font=("Segoe UI", 8))

        entry_row = ttk.Frame(main)
        entry_row.grid(row=3, column=0, sticky="ew")
        entry_row.columnconfigure(0, weight=1)

        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(entry_row, textvariable=self.message_var, font=("Segoe UI", 10))
        self.message_entry.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 8))
        self.message_entry.bind("<Return>", lambda _e: self._on_send())
        self.message_entry.state(["disabled"])

        ttk.Button(entry_row, text="Send", style="Accent.TButton", command=self._on_send).grid(row=0, column=1)

        self._render_room_list()

    def _on_create_room(self):
        room = simpledialog.askstring("New Room", "Room name:", parent=self.root)
        if room and room.strip():
            self._send({"type": "create_room", "room": room.strip()})

    def _on_room_selected(self, room):
        self.active_room = room
        self.unread_counts[room] = 0
        self.room_title_var.set(f"# {room}")
        self._render_room_list()
        self._redraw_log()

        if room not in self.joined_rooms:
            self._send({"type": "join_room", "room": room})
        self.message_entry.state(["!disabled"])
        self.message_entry.focus_set()

    def _on_send(self):
        text = self.message_var.get().strip()
        if not text or not self.active_room:
            return
        self._send({"type": "send_message", "room": self.active_room, "text": text})
        self.message_var.set("")

    # --- Networking ---

    def _send(self, message):
        try:
            protocol.send(self.sock, message)
        except OSError as exc:
            self._show_chat_error(f"Lost connection to the server: {exc}")

    def _recv_loop(self):
        while True:
            try:
                message = protocol.receive(self.reader)
            except OSError:
                message = None
            if message is None:
                self.incoming.put({"type": "_disconnected"})
                return
            self.incoming.put(message)

    def _poll_queue(self):
        try:
            while True:
                message = self.incoming.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            pass
        self._poll_job = self.root.after(100, self._poll_queue)

    def _handle_message(self, message):
        handler = {
            "auth_result": self._handle_auth_result,
            "room_list": self._handle_room_list,
            "room_created": self._handle_room_created,
            "joined_room": self._handle_joined_room,
            "message": self._handle_chat_message,
            "system": self._handle_system_message,
            "error": self._handle_error,
            "_disconnected": self._handle_disconnected,
        }.get(message.get("type"))
        if handler:
            handler(message)

    def _handle_room_list(self, message):
        self.all_rooms = message["rooms"]
        if hasattr(self, "rooms_list_frame"):
            self._render_room_list()

    def _handle_room_created(self, message):
        if not message.get("ok"):
            self._show_chat_error(message.get("error") or "Couldn't create that room.")

    def _handle_joined_room(self, message):
        room = message["room"]
        self.joined_rooms.add(room)
        lines = [self._format_history_entry(entry) for entry in message["history"]]
        self.room_history[room] = lines
        if room == self.active_room:
            self._redraw_log()

    def _handle_chat_message(self, message):
        room = message["room"]
        is_me = message["username"] == self.username
        line = (message["timestamp"], message["username"], message["text"], "me" if is_me else "other")
        self.room_history.setdefault(room, []).append(line)
        if room == self.active_room:
            self._append_line(*line)
        else:
            self._bump_unread(room)

    def _handle_system_message(self, message):
        room = message["room"]
        line = (message["timestamp"], None, message["text"], "system")
        self.room_history.setdefault(room, []).append(line)
        if room == self.active_room:
            self._append_line(*line)

    def _handle_error(self, message):
        self._show_chat_error(message.get("message", "Something went wrong."))

    def _handle_disconnected(self, _message):
        self._show_chat_error("Disconnected from the server.")
        self.message_entry.state(["disabled"])

    # --- Rendering ---

    def _render_room_list(self):
        for child in self.rooms_list_frame.winfo_children():
            child.destroy()

        for room in self.all_rooms:
            is_active = room == self.active_room
            row = tk.Frame(self.rooms_list_frame,
                            bg=COLORS["accent"] if is_active else COLORS["card"], cursor="hand2")
            row.pack(fill="x", pady=1)

            unread = self.unread_counts.get(room, 0)
            label_text = f"# {room}" + (f"  ({unread})" if unread else "")
            label = tk.Label(row, text=label_text, bg=row["bg"],
                              fg="white" if is_active else COLORS["text"],
                              anchor="w", padx=8, pady=6, font=("Segoe UI", 10, "bold" if unread else "normal"))
            label.pack(fill="x")

            for widget in (row, label):
                widget.bind("<Button-1>", lambda _e, r=room: self._on_room_selected(r))

    def _redraw_log(self):
        self.message_log.config(state="normal")
        self.message_log.delete("1.0", tk.END)
        self.message_log.config(state="disabled")
        for entry in self.room_history.get(self.active_room, []):
            self._append_line(*entry)

    def _append_line(self, timestamp, username, text, kind):
        self.message_log.config(state="normal")
        if kind == "system":
            self.message_log.insert(tk.END, f"[{timestamp}] {text}\n", ("system",))
        else:
            self.message_log.insert(tk.END, f"[{timestamp}] ", ("time",))
            self.message_log.insert(tk.END, f"{username}: ", (kind,))
            self.message_log.insert(tk.END, f"{text}\n")
        self.message_log.see(tk.END)
        self.message_log.config(state="disabled")

    def _format_history_entry(self, entry):
        is_me = entry["username"] == self.username
        return (entry["timestamp"], entry["username"], entry["text"], "me" if is_me else "other")

    def _bump_unread(self, room):
        self.unread_counts[room] = self.unread_counts.get(room, 0) + 1
        if hasattr(self, "rooms_list_frame"):
            self._render_room_list()
        if not self.is_focused:
            self._flash_title()

    def _flash_title(self):
        total_unread = sum(self.unread_counts.values())
        if total_unread:
            self.root.title(f"({total_unread}) Chat - new message")
            self.root.bell()

    def _show_chat_error(self, message):
        self.chat_error_var.set(message)
        self.chat_error_label.grid()
        self.root.after(4000, self._clear_chat_error)

    def _clear_chat_error(self):
        self.chat_error_var.set("")
        self.chat_error_label.grid_remove()

    # --- Focus tracking (for the "not focused" notification requirement) ---

    def _on_focus_in(self, _event):
        self.is_focused = True
        self.root.title("Chat")

    def _on_focus_out(self, _event):
        self.is_focused = False

    def _on_close(self):
        if getattr(self, "_poll_job", None) is not None:
            self.root.after_cancel(self._poll_job)
            self._poll_job = None
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    ChatClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
