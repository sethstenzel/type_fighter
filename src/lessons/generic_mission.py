from lessons.lesson_1.lesson_1_mission import run_mission
from lessons.lesson_config import learned_keys_through


def run_lesson_mission(screen, clock, base_dir, lesson_number):
    return run_mission(
        screen,
        clock,
        base_dir,
        f"lesson_{lesson_number}",
        learned_keys_through(lesson_number),
    )
