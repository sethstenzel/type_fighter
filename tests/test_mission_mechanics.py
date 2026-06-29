import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame

from lessons.mission_engine import (
    Drone,
    FinalBoss,
    MEGA_DRONE_HP,
    accuracy_thresholds_for_lesson,
    defense_drone_remaining_shot_capacity,
    event_to_lesson_key,
    mega_charge_required_for_target,
    mega_damage_for_target,
    mission_target_keys,
    player_defense_drone_count,
    queue_shot_at,
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

    def test_second_defense_drone_counts_from_purchased_upgrade_ids(self):
        player = {
            "purchased_upgrade_ids": ["defense_drone", "second_defense_drone"],
            "pod": {"upgrades": []},
            "achievements": {},
        }

        self.assertEqual(player_defense_drone_count(player), 2)

    def test_major_rank_grants_reward_drone_without_purchased_drones(self):
        player = {
            "purchased_upgrade_ids": [],
            "pod": {"upgrades": []},
            "achievements": {"major_rank": True},
        }

        self.assertEqual(player_defense_drone_count(player), 1)

    def test_updated_accuracy_threshold_bands(self):
        cases = {
            1: (10, 10),
            3: (10, 10),
            4: (40, 30),
            9: (40, 30),
            10: (70, 60),
            19: (70, 60),
            20: (75, 65),
            29: (75, 65),
            30: (80, 70),
            36: (80, 70),
        }

        for lesson_number, expected_thresholds in cases.items():
            with self.subTest(lesson_number=lesson_number):
                self.assertEqual(accuracy_thresholds_for_lesson(lesson_number), expected_thresholds)

    def test_player_can_target_drone_reserved_by_defense_drone(self):
        drone = self.drone(hp=1)
        drone.incoming_defense_damage = 1
        pending = []

        queued = queue_shot_at([drone], pending, "k", pygame.Vector2(0, 0), 0)

        self.assertTrue(queued)
        self.assertEqual(drone.incoming_damage, 1)
        self.assertEqual(drone.incoming_defense_damage, 1)

    def test_defense_reservation_capacity_is_separate_from_player_shots(self):
        drone = self.drone(hp=1)
        drone.incoming_damage = 1

        self.assertEqual(defense_drone_remaining_shot_capacity(drone), 1)

        drone.incoming_defense_damage = 1
        self.assertEqual(defense_drone_remaining_shot_capacity(drone), 0)

    def test_defense_drones_can_reserve_extra_split_capacity(self):
        drone = self.drone(hp=2)

        self.assertEqual(defense_drone_remaining_shot_capacity(drone), 3)

        drone.incoming_defense_damage = 1
        self.assertEqual(defense_drone_remaining_shot_capacity(drone), 2)

    def test_shift_is_target_key_before_shifted_symbol_missions(self):
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT, unicode="")

        self.assertEqual(event_to_lesson_key(event, 26), "shift")
        self.assertIn("shift", mission_target_keys(("shift", "a", "!"), 26, mega_available=True))

    def test_shift_becomes_modifier_for_shifted_symbol_missions(self):
        shift_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT, unicode="")
        symbol_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1, unicode="!")

        self.assertIsNone(event_to_lesson_key(shift_event, 27))
        self.assertEqual(event_to_lesson_key(symbol_event, 27), "!")
        self.assertNotIn("shift", mission_target_keys(("shift", "a", "!"), 27, mega_available=True))
        self.assertIn("!", mission_target_keys(("shift", "a", "!"), 27, mega_available=True))


if __name__ == "__main__":
    unittest.main()
