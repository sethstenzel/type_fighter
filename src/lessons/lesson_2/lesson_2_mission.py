from lessons.lesson_1.lesson_1_mission import run_mission


LESSON_DIR_NAME = "lesson_2"
VALID_KEYS = ("f", "j", "d", "k", "space")


def run(screen, clock, base_dir):
    return run_mission(screen, clock, base_dir, LESSON_DIR_NAME, VALID_KEYS)
