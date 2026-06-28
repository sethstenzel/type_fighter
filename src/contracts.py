from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


PlayerSessionError = Literal["PLAYER_SESSION_EXPIRED", "PLAYER_SESSION_REPLACED"]


PLAYER_SESSION_HEADER = "X-Player-Session"


@dataclass(frozen=True)
class AccountContract:
    id: str
    email: str
    username: str


@dataclass(frozen=True)
class AuthResponseContract:
    token: str
    account: AccountContract


@dataclass(frozen=True)
class PlayerRowContract:
    id: str
    name: str
    data: dict[str, Any]
    updated_at: str
    locked: bool


@dataclass(frozen=True)
class PlayerClaimResponseContract:
    ok: bool
    player_session: str


@dataclass(frozen=True)
class VersionResponseContract:
    version: str


@dataclass(frozen=True)
class GameConfigContract:
    settings: dict[str, Any]
    upgrades: list[dict[str, Any]]
    achievements: list[dict[str, Any]]


API_CONTRACT_NOTES = {
    "auth": {
        "POST /auth/register": "Request: email, username, password. Response: token and account.",
        "POST /auth/login": "Request: email, password. Response: token and account.",
        "GET /auth/session": "Response: current account for bearer token.",
        "POST /auth/change-password": "Request: current_password, new_password.",
    },
    "players": {
        "GET /players": "Response: list of PlayerRowContract.",
        "POST /players": "Request: name, data. Response: PlayerRowContract.",
        "PUT /players/{player_id}": f"Requires bearer token and {PLAYER_SESSION_HEADER}. Response: PlayerRowContract.",
        "POST /players/{player_id}/claim": "Response: ok and player_session token.",
        "POST /players/{player_id}/heartbeat": f"Requires bearer token and {PLAYER_SESSION_HEADER}. Response: ok.",
        "POST /players/{player_id}/release": f"Requires bearer token and {PLAYER_SESSION_HEADER}. Response: ok.",
    },
    "session_errors": {
        "401 PLAYER_SESSION_EXPIRED": "The active player session timed out or was released.",
        "409 PLAYER_SESSION_REPLACED": "Another client claimed the same player.",
    },
}
