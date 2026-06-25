from lessons.mission_engine import run_mission


LESSON_DIR_NAME = "lesson_2"
VALID_KEYS = ("f", "j", "d", "k", "space")


def run(screen, clock, base_dir, player=None):
    return run_mission(screen, clock, base_dir, LESSON_DIR_NAME, VALID_KEYS, player)
