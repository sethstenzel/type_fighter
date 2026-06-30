import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame

import lessons.mission_engine as me
import player_model
from lessons.mission_engine import (
    Drone,
    FinalBoss,
    MEGA_DRONE_HP,
    accuracy_thresholds_for_lesson,
    defense_drone_remaining_shot_capacity,
    event_to_lesson_key,
    final_boss_count,
    mega_charge_required_for_target,
    mega_damage_for_target,
    mega_shot_speed,
    mission_target_keys,
    normalize_mission_settings,
    player_defense_drone_count,
    queue_shot_at,
    queue_mega_shot,
    random_spawn_key,
    spawn_final_boss,
    spawn_power_up,
    target_is_available,
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

    # --- Issue #8: empty key-set guards ---
    def test_random_spawn_key_handles_empty_key_sets(self):
        self.assertEqual(random_spawn_key(()), "")
        self.assertEqual(random_spawn_key((), blocked_key="x"), "")
        # falls back to valid_keys when the only available key is the blocked one
        self.assertEqual(random_spawn_key(("a",), blocked_key="a"), "a")

    def test_spawn_power_up_returns_none_when_no_keys(self):
        screen = pygame.Surface((640, 480))
        self.assertIsNone(spawn_power_up(screen, (), now=0))

    def test_spawn_final_boss_handles_empty_key_sets(self):
        screen = pygame.Surface((640, 480))
        boss = spawn_final_boss(screen, 0, (), pygame.Vector2(320, 240), focus_keys=())
        self.assertEqual(boss.letter, "")

    # --- Issue #3: target revalidation prevents double-defeat ---
    def test_target_is_available_tracks_membership(self):
        drone = self.drone()
        boss = FinalBoss(pos=pygame.Vector2(0, 0), target_pos=pygame.Vector2(1, 0), letter="k")
        self.assertTrue(target_is_available(drone, [drone], [boss]))
        self.assertTrue(target_is_available(boss, [drone], [boss]))
        # once removed from its list, an in-flight shot must drop the target
        self.assertFalse(target_is_available(drone, [], [boss]))
        self.assertFalse(target_is_available(boss, [drone], []))

    # --- Issue #5: mega_shot_speed table + boss-count key normalization ---
    def test_mega_shot_speed_matches_expected_table(self):
        self.assertEqual(mega_shot_speed(1), 820)
        self.assertEqual(mega_shot_speed(2), 820 * 1.10)
        self.assertEqual(mega_shot_speed(3), 820 * 1.20)
        self.assertEqual(mega_shot_speed(4), 820 * 1.40)
        self.assertEqual(mega_shot_speed(5), 820 * 1.80)

    def test_final_boss_count_reads_str_and_int_keys(self):
        me.apply_game_settings({"final_boss_count_by_lesson": {7: 2, "8": 3}})
        try:
            self.assertEqual(final_boss_count(7), 2)   # configured with an int key
            self.assertEqual(final_boss_count(8), 3)   # configured with a str key
            self.assertEqual(final_boss_count(9), 1)   # unconfigured -> default
            self.assertEqual(final_boss_count(4), 0)   # no final boss before lesson 5
        finally:
            me.apply_game_settings({"final_boss_count_by_lesson": {}})

    # --- Issue #4: single source of truth for mission settings ---
    def test_mission_settings_normalizer_shared_with_player_model(self):
        self.assertIs(normalize_mission_settings, player_model.normalize_mission_settings)
        self.assertIs(me.DEFAULT_MISSION_SETTINGS, player_model.DEFAULT_MISSION_SETTINGS)
        self.assertEqual(me.MAX_SPAWN_RATE_MULTIPLIER, player_model.MAX_SPAWN_RATE_MULTIPLIER)

    # --- Issue #13: accuracy band boundaries + credit math ---
    def test_accuracy_thresholds_out_of_range_lessons(self):
        self.assertEqual(accuracy_thresholds_for_lesson(0), (100, 100))
        self.assertEqual(accuracy_thresholds_for_lesson(-5), (100, 100))
        self.assertEqual(accuracy_thresholds_for_lesson(999), (80, 70))  # last open-ended band

    # --- Issue #15: scoring helpers ---
    def test_regular_drone_clear_score(self):
        self.assertEqual(me.regular_drone_clear_score(1), 100)   # yellow
        self.assertEqual(me.regular_drone_clear_score(2), 300)   # orange
        self.assertEqual(me.regular_drone_clear_score(3), 700)   # red ("7 drones worth")

    def test_mega_kill_bonus(self):
        self.assertEqual(me.mega_kill_bonus(1), 0)    # yellow
        self.assertEqual(me.mega_kill_bonus(2), 50)   # orange
        self.assertEqual(me.mega_kill_bonus(3), 100)  # red

    def test_high_score_goal_formula(self):
        # drone*100 + powerups*100 + 500 (flat) + boss + semis*200 + 2000
        self.assertEqual(me.high_score_goal(30, 4, 0, 0), 30 * 100 + 400 + 500 + 0 + 0 + 2000)
        self.assertEqual(me.high_score_goal(51, 4, 1000, 5), 5100 + 400 + 500 + 1000 + 1000 + 2000)

    # --- Issue #16: timer helpers ---
    def test_format_mission_time(self):
        self.assertEqual(me.format_mission_time(0), "0:00")
        self.assertEqual(me.format_mission_time(9000), "0:09")
        self.assertEqual(me.format_mission_time(75000), "1:15")

    def test_quick_defender_goal_default(self):
        self.assertEqual(me.quick_defender_goal_ms(1), me.DEFAULT_QUICK_DEFENDER_MS)

    def test_format_level_timer_hundredths_and_cap(self):
        self.assertEqual(me.format_level_timer(0), "T: 0.00")
        self.assertEqual(me.format_level_timer(1500), "T: 1.50")
        self.assertEqual(me.format_level_timer(12340), "T: 12.34")
        # stops counting past 999.99s
        self.assertEqual(me.format_level_timer(999990), "T: 999.99")
        self.assertEqual(me.format_level_timer(5_000_000), "T: 999.99")

    def test_calculate_credits_earned_bonuses(self):
        engine = me.MissionEngine.__new__(me.MissionEngine)
        engine.destroyed = 50
        engine.drone_target = 46
        engine.hits_taken = 0
        engine.inaccurate_inputs = 0
        win_perfect = 46 + 50 + 25 + me.ENERGY_SAVER_BONUS_CREDITS
        self.assertEqual(engine._calculate_credits_earned(True), win_perfect)
        # damage + inaccuracies -> only base destroyed count + win bonus
        engine.hits_taken = 2
        engine.inaccurate_inputs = 3
        self.assertEqual(engine._calculate_credits_earned(True), 46 + 50)
        # a loss awards only the destroyed count, capped at the target
        self.assertEqual(engine._calculate_credits_earned(False), 46)


if __name__ == "__main__":
    unittest.main()
