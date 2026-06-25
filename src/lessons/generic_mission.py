from lessons.mission_engine import run_mission
from lessons.lesson_config import learned_keys_through


def run_lesson_mission(screen, clock, base_dir, lesson_number, player=None):
    return run_mission(
        screen,
        clock,
        base_dir,
        f"lesson_{lesson_number}",
        learned_keys_through(lesson_number),
        player,
    )
