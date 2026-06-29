from __future__ import annotations

import json
from pathlib import Path

from display_helpers import SCREEN_SIZE, aspect_locked_size
from player_storage_sqlite import user_data_dir


SETTINGS_PATH = user_data_dir() / "user_settings.cfg"


DEFAULT_SETTINGS = {
    "display": {
        "fullscreen": True,
        "window_width": SCREEN_SIZE[0],
        "window_height": SCREEN_SIZE[1],
    },
}


def load_user_settings():
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    settings = dict(DEFAULT_SETTINGS)
    display = dict(DEFAULT_SETTINGS["display"])
    if isinstance(data, dict) and isinstance(data.get("display"), dict):
        raw_display = data["display"]
        display["fullscreen"] = bool(raw_display.get("fullscreen", display["fullscreen"]))
        try:
            width = int(raw_display.get("window_width", display["window_width"]))
            height = int(raw_display.get("window_height", display["window_height"]))
        except (TypeError, ValueError):
            width, height = display["window_width"], display["window_height"]
        width, height = aspect_locked_size(width, height)
        display["window_width"] = width
        display["window_height"] = height
    settings["display"] = display
    return settings


def save_user_settings(settings):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def display_settings():
    return load_user_settings()["display"]


def set_display_state(fullscreen, size=None):
    settings = load_user_settings()
    display = settings["display"]
    display["fullscreen"] = bool(fullscreen)
    if size is not None:
        width, height = aspect_locked_size(*size)
        display["window_width"] = width
        display["window_height"] = height
    save_user_settings(settings)
    return display


def window_size():
    display = display_settings()
    return int(display["window_width"]), int(display["window_height"])


def windowed():
    return not bool(display_settings()["fullscreen"])
