"""
Wire protocol: newline-delimited JSON over a plain TCP socket.

Reading is implemented directly on socket.recv() with a small manual
buffer, rather than socket.makefile(). makefile()'s TextIOWrapper turned
out to never detect a peer closing the connection on this platform —
readline() blocked forever instead of returning "" at EOF — which silently
broke disconnect handling. Raw recv() correctly returns b"" on EOF, so
LineReader is built on that directly.
"""

import json

ENCODING = "utf-8"


class LineReader:
    def __init__(self, sock, chunk_size=4096):
        self._sock = sock
        self._chunk_size = chunk_size
        self._buffer = b""

    def readline(self):
        """Returns the next newline-terminated chunk of bytes, or b"" once
        the peer has disconnected and no more data is buffered."""
        while b"\n" not in self._buffer:
            try:
                chunk = self._sock.recv(self._chunk_size)
            except OSError:
                chunk = b""
            if not chunk:
                remainder, self._buffer = self._buffer, b""
                return remainder
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line + b"\n"


def make_reader(sock):
    return LineReader(sock)


def send(sock, message: dict):
    data = (json.dumps(message) + "\n").encode(ENCODING)
    sock.sendall(data)


def receive(reader):
    """Returns the next parsed message, or None if the peer disconnected
    or sent a line that isn't valid JSON."""
    line = reader.readline()
    if not line:
        return None
    line = line.decode(ENCODING).strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None
