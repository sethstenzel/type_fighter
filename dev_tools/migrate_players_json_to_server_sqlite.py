from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path


PASSWORD_ITERATIONS = 260_000
DEFAULT_EMAIL = "seth.c.stenzel@gmail.com"
DEFAULT_PASSWORD = "1Dropatatime!"
DEFAULT_USERNAME = "Seth"


def utc_now():
    return datetime.now(UTC).isoformat()


def hash_password(password, iterations=PASSWORD_ITERATIONS):
    salt = uuid.uuid4().bytes + uuid.uuid4().bytes[:8]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (
        base64.b64encode(digest).decode("ascii"),
        base64.b64encode(salt).decode("ascii"),
        iterations,
    )


def init_db(connection):
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            password_iterations INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            active_session_hash TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(account_id, name COLLATE NOCASE),
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY(active_session_hash) REFERENCES sessions(token_hash) ON DELETE SET NULL
        )
        """
    )


def load_players(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("players.json must contain a player list")
    players = []
    seen_names = set()
    for player in data:
        if not isinstance(player, dict):
            continue
        name = str(player.get("name", "")).strip()
        if not name or name.lower() in seen_names:
            continue
        player = dict(player)
        player["id"] = str(player.get("id") or uuid.uuid4())
        player["name"] = name[:24]
        players.append(player)
        seen_names.add(name.lower())
    return players


def migrate(players_json, sqlite_path, email, username, password):
    players = load_players(players_json)
    sqlite_path = Path(sqlite_path)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    account_id = str(uuid.uuid4())
    password_hash, salt, iterations = hash_password(password)
    with sqlite3.connect(sqlite_path) as connection:
        init_db(connection)
        connection.execute("DELETE FROM sessions")
        connection.execute("DELETE FROM players")
        connection.execute("DELETE FROM accounts")
        connection.execute(
            """
            INSERT INTO accounts (id, email, username, password_hash, password_salt, password_iterations, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (account_id, email.strip().lower(), username.strip(), password_hash, salt, iterations, now, now),
        )
        for player in players:
            player_json = json.dumps(player, separators=(",", ":"))
            connection.execute(
                """
                INSERT INTO players (id, account_id, name, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (player["id"], account_id, player["name"], player_json, now, now),
            )
    return len(players), sqlite_path


def main():
    parser = argparse.ArgumentParser(description="Migrate Type Fighter players.json into server players.sqlite.")
    parser.add_argument("--players-json", default="players.json", help="Source players.json path.")
    parser.add_argument("--sqlite", default="players.sqlite", help="Output SQLite database path.")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Account email.")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Account username.")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Account password.")
    args = parser.parse_args()
    count, sqlite_path = migrate(args.players_json, args.sqlite, args.email, args.username, args.password)
    print(f"Migrated {count} players to {sqlite_path}")


if __name__ == "__main__":
    main()
