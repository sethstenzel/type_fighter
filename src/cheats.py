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
    "10": "Mark every level as unlocked in the save (persists)",
    "11": "Unlock every training mission in the menu for this run (no save change)",
    "12": "Disable the wrong-key error sound",
    "13": "Disable the drone explosion sound when they are destroyed",
    "14": "Auto-fire the turret at nearby drones (toggle with Left Ctrl x5)",
    "15": "Increase the drone spawn rate to 10x",
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


def log_cheat_event(message):
    """Append a timestamped line to cheats.log in the user data dir.

    Best-effort: never raises (cheat logging must not interfere with play).
    """
    try:
        import datetime

        from player_storage_sqlite import user_data_dir

        data_dir = user_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        log_path = data_dir / "cheats.log"
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {message}\n")
    except Exception:
        pass


def _total_lessons():
    try:
        from lessons.lesson_config import LESSON_PROGRESS

        return len(LESSON_PROGRESS)
    except Exception:
        return 36


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
        # Undo all purchases: equipped pod upgrades plus bought lives/charges.
        player["pod"] = {"color": "blue", "type": "standard", "upgrades": []}
        player["lives"] = 3
        player["shield_charges"] = 0
        player["time_stop_charges"] = 0
        # Clear the last mission's stats too, otherwise the login achievement
        # check would re-mark that lesson's perfect/high-score/quick badge.
        player["last_mission_stats"] = {}
    if is_enabled("10"):
        # Unlock every level by marking the prerequisite lessons complete (the
        # last level only needs the second-to-last completed to be unlocked).
        player["completed_lessons"] = list(range(1, _total_lessons()))
    if is_enabled("8"):
        player["lifetime_score"] = 0
    if is_enabled("9"):
        player["achievements"] = {}
    if is_enabled("1"):
        player["lives"] = CHEAT_LIVES
    if is_enabled("7"):
        player["credits"] = CHEAT_CREDITS
