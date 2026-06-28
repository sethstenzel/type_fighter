from __future__ import annotations

import threading


_lock = threading.Lock()
_forced_disconnect_message = ""


def set_forced_disconnect(message):
    global _forced_disconnect_message
    with _lock:
        _forced_disconnect_message = str(message or "").strip()


def consume_forced_disconnect():
    global _forced_disconnect_message
    with _lock:
        message = _forced_disconnect_message
        _forced_disconnect_message = ""
    return message


def has_forced_disconnect():
    with _lock:
        return bool(_forced_disconnect_message)
