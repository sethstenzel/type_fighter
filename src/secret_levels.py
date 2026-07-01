"""Hidden "secret" levels, unlocked from the command line.

Usage:
    uv run python src/game.py --secret_level 1
    uv run python src/game.py --secret_level=1

Passing ``--secret_level N`` arms secret level ``N``. Once armed, the player
reaches it by selecting training mission one in the menu **while holding Shift**.
Only level 1 (a "reposition run" where you pilot the pod to a goal zone while
drones give chase) is implemented today; other numbers are accepted but simply
do nothing until a matching level exists.
"""

from __future__ import annotations


# Secret levels that actually have an implementation wired up in the game.
IMPLEMENTED_LEVELS = {1}

_armed_level: int | None = None


def parse_secret_level_arg(argv):
    """Return the int from ``--secret_level=N`` / ``--secret_level N`` in argv.

    Returns None when the flag is absent or its value is not a positive int.
    The last occurrence wins, mirroring typical command-line behaviour.
    """
    value = None
    for index, arg in enumerate(argv):
        if arg.startswith("--secret_level="):
            value = arg.split("=", 1)[1]
        elif arg == "--secret_level" and index + 1 < len(argv):
            value = argv[index + 1]
    if value is None:
        return None
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def arm_from_argv(argv):
    """Arm the secret level parsed from argv. Returns the armed level or None."""
    global _armed_level
    _armed_level = parse_secret_level_arg(argv)
    return _armed_level


def armed_level():
    """The secret level number armed for this run, or None."""
    return _armed_level


def available_for_lesson(lesson_number):
    """The secret level to launch for ``lesson_number``, or None.

    Secret levels are reached through training mission one, so only lesson 1
    maps to the armed level (and only when that level is implemented).
    """
    if lesson_number != 1:
        return None
    if _armed_level in IMPLEMENTED_LEVELS:
        return _armed_level
    return None
