"""Non-blocking raw-mode keyboard reader running in a background thread.

Emits normalised key names ("space", "q", "left", "right", "up", "down") to a
callback. POSIX only (macOS/Linux); on other platforms it is a no-op so the rest
of the app still runs (control via Ctrl-C only).
"""

from __future__ import annotations

import sys
import threading
from typing import Callable

try:
    import termios
    import tty

    _POSIX = True
except ImportError:  # pragma: no cover - non-POSIX
    _POSIX = False


_ARROWS = {"A": "up", "B": "down", "C": "right", "D": "left"}


class KeyReader:
    def __init__(self, on_key: Callable[[str], None]):
        self._on_key = on_key
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._old_settings = None

    def start(self) -> None:
        if not _POSIX or not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._old_settings is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)
            self._old_settings = None

    def _loop(self) -> None:
        import select

        fd = sys.stdin.fileno()
        while not self._stop.is_set():
            if not select.select([fd], [], [], 0.1)[0]:
                continue
            ch = sys.stdin.read(1)
            if ch == "\x1b":  # escape sequence, e.g. arrow keys
                seq = sys.stdin.read(2)
                if len(seq) == 2 and seq[0] == "[" and seq[1] in _ARROWS:
                    self._on_key(_ARROWS[seq[1]])
                continue
            if ch == " ":
                self._on_key("space")
            elif ch in ("\x03", "\x04"):  # Ctrl-C / Ctrl-D
                self._on_key("q")
            elif ch:
                self._on_key(ch.lower())
