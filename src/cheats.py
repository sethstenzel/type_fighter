"""Developer cheats, enabled from the command line.

Usage:
    uv run python src/game.py --cheats 1,4,5
    uv run python src/game.py --cheats=1,4,5

Pass a comma-delimited list of cheat numbers. Unknown entries are ignored with
a warning. `--cheats list` (or `help`) reports the available cheats.

Cheats fall into two groups:
- One-shot player-record cheats (1, 7, 8, 9, 0) are applied to the save when a
  player is selected.
- Behavioural mission cheats (2, 3, 4, 5, 6) take effect during play.
"""

from __future__ import annotations


# id -> human-readable description
AVAILABLE_CHEATS = {
    "1": "Player lives set to 99",
    "2": "Player does not lose lives when hit",
    "3": "Hits do nothing - no life lost and not counted as a hit",
    "4": "Mega Shot charge is always 5 and never drains when fired",
    "5": "Shield charges are always 3 and never drain when used",
    "6": "Time Stop charges are always 3 and are never consumed",
    "7": "Player credits set to 100,000",
    "8": "Reset the player's high score (lifetime score) to 0",
    "9": "Reset achievements earned so they can trigger again",
    "0": "Full reset: credits, score, unlocked levels, and achievements cleared",
}

CHEAT_LIVES = 99
CHEAT_CREDITS = 100000
CHEAT_SHIELD_CHARGES = 3
CHEAT_TIME_STOP_CHARGES = 3

_enabled = set()


def parse_cheat_arg(argv):
    """Extract raw cheat ids from --cheats=1,4,5 or --cheats 1,4,5 in argv."""
    names = []
    for index, arg in enumerate(argv):
        value = None
        if arg.startswith("--cheats="):
            value = arg.split("=", 1)[1]
        elif arg == "--cheats" and index + 1 < len(argv):
            value = argv[index + 1]
        if value:
            names.extend(part.strip().lower() for part in value.split(",") if part.strip())
    return names


def enable_from_argv(argv):
    """Enable cheats parsed from argv. Returns (enabled_set, unknown_list)."""
    global _enabled
    enabled = set()
    unknown = []
    for name in parse_cheat_arg(argv):
        if name in ("list", "help"):
            continue
        if name in AVAILABLE_CHEATS:
            enabled.add(name)
        else:
            unknown.append(name)
    _enabled = enabled
    return enabled, unknown


def wants_listing(argv):
    return any(name in ("list", "help") for name in parse_cheat_arg(argv))


def is_enabled(name):
    return name in _enabled


def enabled_cheats():
    return set(_enabled)


def apply_player_cheats(player):
    """Apply the one-shot player-record cheats to a selected player's save."""
    if not isinstance(player, dict):
        return
    if is_enabled("0"):
        # Full wipe of progress.
        player["completed_lessons"] = []
        player["credits"] = 0
        player["lifetime_score"] = 0
        player["achievements"] = {}
        player["perfect_lessons"] = []
        player["high_score_lessons"] = []
        player["quick_lessons"] = []
        player["purchased_upgrade_ids"] = []
        player["sold_lives"] = 0
        player["sold_shields"] = 0
    if is_enabled("8"):
        player["lifetime_score"] = 0
    if is_enabled("9"):
        player["achievements"] = {}
    if is_enabled("1"):
        player["lives"] = CHEAT_LIVES
    if is_enabled("7"):
        player["credits"] = CHEAT_CREDITS
