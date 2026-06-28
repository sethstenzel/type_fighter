import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame

from lessons.mission_engine import (
    Drone,
    FinalBoss,
    MEGA_DRONE_HP,
    mega_charge_required_for_target,
    mega_damage_for_target,
    player_defense_drone_count,
    queue_mega_shot,
)


class MissionMechanicsTests(unittest.TestCase):
    def drone(self, hp=1, is_mega=False):
        return Drone(
            pos=pygame.Vector2(100, 100),
            letter="k",
            hp=hp,
            max_hp=hp,
            radius=10,
            speed=0,
            is_mega=is_mega,
        )

    def test_advanced_mega_shot_uses_only_regular_drone_hp_charge(self):
        drone = self.drone(hp=2)
        pending = []

        spent = queue_mega_shot([drone], [], pending, "k", pygame.Vector2(0, 0), 5, 0, advanced=True)

        self.assertEqual(spent, 2)
        self.assertEqual(pending[0].mega_charge_level, 2)

    def test_purple_mini_boss_requires_four_charge_to_kill(self):
        mini_boss = self.drone(hp=MEGA_DRONE_HP, is_mega=True)

        self.assertEqual(mega_charge_required_for_target(mini_boss), 4)
        self.assertEqual(mega_damage_for_target(mini_boss, 3), 4)
        self.assertEqual(mega_damage_for_target(mini_boss, 4), MEGA_DRONE_HP)

    def test_final_boss_requires_five_charge(self):
        boss = FinalBoss(
            pos=pygame.Vector2(100, 100),
            target_pos=pygame.Vector2(200, 100),
            letter="k",
        )

        self.assertEqual(mega_charge_required_for_target(boss), 5)

    def test_major_rank_achievement_adds_third_defense_drone(self):
        player = {
            "achievements": {"major_rank": True},
            "pod": {
                "upgrades": [
                    {"id": "defense_drone"},
                    {"id": "second_defense_drone"},
                ]
            },
        }

        self.assertEqual(player_defense_drone_count(player), 3)


if __name__ == "__main__":
    unittest.main()
