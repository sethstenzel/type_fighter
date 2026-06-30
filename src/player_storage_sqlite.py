from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


def utc_now():
    return datetime.now(UTC).isoformat()


def user_data_dir():
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "TypeFighter"
    if sys_platform := os.environ.get("XDG_DATA_HOME"):
        return Path(sys_platform) / "type-fighter"
    return Path.home() / ".local" / "share" / "type-fighter"


def saves_dir():
    path = user_data_dir() / "saves" / steam_user_id()
    path.mkdir(parents=True, exist_ok=True)
    return path


def steam_user_id():
    return os.environ.get("TYPE_FIGHTER_STEAM_ID", "").strip() or "mock_steam_id"


def safe_player_filename(name):
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(name).strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return (cleaned or "player")[:80]


def player_db_path(name):
    return saves_dir() / f"{safe_player_filename(name)}.tfp.db"


def connect_player_db(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_player_db(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS player_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            player_id TEXT NOT NULL,
            name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            game_version TEXT NOT NULL
        )
        """
    )


def normalize_player_metadata(player, client_version, touch=False):
    if not isinstance(player.get("id"), str) or not player["id"].strip():
        player["id"] = str(uuid.uuid4())
    if touch or not player.get("updated_at"):
        player["updated_at"] = utc_now()
    player["game_version"] = client_version
    return player


def read_player_db(path):
    with closing(connect_player_db(path)) as connection:
        with connection:
            init_player_db(connection)
        row = connection.execute("SELECT * FROM player_profile WHERE id = 1").fetchone()
    if row is None:
        return None
    try:
        player = json.loads(row["data_json"])
    except json.JSONDecodeError:
        return None
    if not isinstance(player, dict):
        return None
    player["id"] = row["player_id"]
    player["name"] = row["name"]
    player["updated_at"] = row["updated_at"]
    player["game_version"] = row["game_version"]
    return player


def write_player_db(player, client_version, touch=True):
    normalize_player_metadata(player, client_version, touch=touch)
    path = player_db_path(player["name"])
    data_json = json.dumps(player, separators=(",", ":"))
    with closing(connect_player_db(path)) as connection:
        with connection:
            init_player_db(connection)
            connection.execute(
                """
            INSERT INTO player_profile (id, player_id, name, data_json, updated_at, game_version)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                player_id = excluded.player_id,
                name = excluded.name,
                data_json = excluded.data_json,
                updated_at = excluded.updated_at,
                game_version = excluded.game_version
            """,
            (player["id"], player["name"], data_json, player["updated_at"], player["game_version"]),
        )
    return path


def load_player_dbs():
    players = []
    for path in sorted(saves_dir().glob("*.tfp.db")):
        player = read_player_db(path)
        if player is not None:
            players.append(player)
    return players


def delete_player_db(player):
    try:
        player_db_path(player["name"]).unlink()
    except OSError:
        pass
