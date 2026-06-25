from lessons.mission_engine import *  # noqa: F403


LESSON_DIR_NAME = "lesson_1"
VALID_KEYS = ("f", "j")


def run(screen, clock, base_dir, player=None):
    return run_mission(screen, clock, base_dir, LESSON_DIR_NAME, VALID_KEYS, player)
