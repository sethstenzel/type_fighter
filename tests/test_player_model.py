import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import player_limits
from game_config import UPGRADE_CATALOG
from player_model import (
    apply_upgrade_purchase,
    apply_upgrade_sale,
    achievement_requirements_met,
    coerce_int,
    create_player_record,
    mission_stats_are_high_score,
    mission_stats_are_quick,
    mission_stats_are_perfect,
    normalize_mission_settings,
    normalize_pod_upgrades,
    player_credits,
    player_rank,
    player_shield_max_charges,
    record_latest_mission_achievement_progress,
    has_upgrade,
    upgrade_lock_reason,
    upgrade_by_id,
)


class PlayerModelTests(unittest.TestCase):
    def test_color_upgrades_keep_only_latest_single_entry(self):
        upgrades = normalize_pod_upgrades(
            [
                {"id": "ammo_charge_color", "color": "Red"},
                {"id": "ammo_charge_color", "color": "Gold"},
                {"id": "extra_life"},
            ]
        )

        self.assertEqual(upgrades, [{"id": "ammo_charge_color", "color": "Gold"}])

    def test_extra_life_purchase_and_sale_mutates_resources(self):
        player = create_player_record("Pilot", lives=3, credits=1000)
        upgrade = dict(upgrade_by_id("extra_life"))

        apply_upgrade_purchase(player, upgrade)
        self.assertEqual(player["lives"], 4)
        self.assertEqual(player["credits"], 800)

        apply_upgrade_sale(player, upgrade, 1)
        self.assertEqual(player["lives"], 3)
        self.assertEqual(player["sold_lives"], 1)
        self.assertEqual(player_credits(player), 900)

    def test_fully_upgraded_requirement_includes_consumable_purchases(self):
        player = create_player_record("Pilot", lives=99, shield_charges=1)
        player["purchased_upgrade_ids"] = [upgrade["id"] for upgrade in UPGRADE_CATALOG]

        self.assertIn("fully_upgraded", achievement_requirements_met(player, total_lessons=36))

    def test_fully_upgraded_achievement_expands_shield_slots(self):
        player = create_player_record("Pilot", achievements={"fully_upgraded": True})

        self.assertEqual(player_shield_max_charges(player), 4)

    def test_living_forever_requirement_uses_configured_max_lives(self):
        player_limits.MAX_PLAYER_LIVES = 99
        player = create_player_record("Pilot", lives=99)

        self.assertIn("living_forever", achievement_requirements_met(player, total_lessons=36))

    def test_rank_thresholds_use_updated_lesson_bands(self):
        cases = [
            ([], "Rookie"),
            ([1, 2, 3, 4], "Private"),
            (list(range(1, 10)), "Lieutenant"),
            (list(range(1, 20)), "Captain"),
            (list(range(1, 30)), "Major"),
        ]

        for completed_lessons, expected_rank in cases:
            with self.subTest(expected_rank=expected_rank):
                player = create_player_record("Pilot", completed_lessons=completed_lessons)
                self.assertEqual(player_rank(player), expected_rank)

    def test_available_second_defense_drone_has_no_lock_reason(self):
        player = create_player_record(
            "Pilot",
            completed_lessons=list(range(1, 20)),
            credits=5000,
            purchased_upgrade_ids=["defense_drone"],
        )

        self.assertIsNone(upgrade_lock_reason(player, upgrade_by_id("second_defense_drone")))

    def test_non_consumable_purchased_upgrade_ids_count_as_owned(self):
        player = create_player_record("Pilot", purchased_upgrade_ids=["defense_drone"])

        self.assertTrue(has_upgrade(player, "defense_drone"))

    def test_mission_settings_are_normalized_and_clamped(self):
        settings = normalize_mission_settings(
            {
                "disable_defense_drones": 1,
                "disable_mega_shot": True,
                "disable_shields": False,
                "spawn_rate_multiplier": 2.13,
                "music_enabled": 0,
            }
        )

        self.assertTrue(settings["disable_defense_drones"])
        self.assertTrue(settings["disable_mega_shot"])
        self.assertFalse(settings["disable_shields"])
        self.assertEqual(settings["spawn_rate_multiplier"], 2.2)
        self.assertFalse(settings["music_enabled"])

        high_settings = normalize_mission_settings({"spawn_rate_multiplier": 6.4})
        self.assertEqual(high_settings["spawn_rate_multiplier"], 5.0)

    def test_player_record_includes_default_mission_settings(self):
        player = create_player_record("Pilot")

        self.assertEqual(player["mission_settings"]["spawn_rate_multiplier"], 1.0)
        self.assertTrue(player["mission_settings"]["music_enabled"])

    def test_perfect_lesson_requires_no_damage_and_100_percent_accuracy(self):
        stats = {
            "lesson_number": 23,
            "won": True,
            "hits_taken": 0,
            "accurate_inputs": 8,
            "inaccurate_inputs": 2,
            "accuracy_percent": 80,
        }

        self.assertFalse(mission_stats_are_perfect(stats, 23))

    def test_record_latest_progress_does_not_mark_imperfect_accuracy(self):
        player = create_player_record("Pilot")
        player["last_mission_stats"] = {
            "lesson_number": 23,
            "won": True,
            "hits_taken": 0,
            "accurate_inputs": 8,
            "inaccurate_inputs": 2,
            "accuracy_percent": 80,
        }

        record_latest_mission_achievement_progress(player, 23)

        self.assertNotIn(23, player["perfect_lessons"])

    def test_record_latest_progress_marks_exact_perfect_mission(self):
        player = create_player_record("Pilot")
        player["last_mission_stats"] = {
            "lesson_number": 23,
            "won": True,
            "hits_taken": 0,
            "accurate_inputs": 10,
            "inaccurate_inputs": 0,
            "accuracy_percent": 100,
        }

        record_latest_mission_achievement_progress(player, 23)

        self.assertIn(23, player["perfect_lessons"])


    # --- Issue #9: reject booleans where integer counts are expected ---
    def test_coerce_int_rejects_bool_and_bad_values(self):
        self.assertEqual(coerce_int(True, 3), 3)
        self.assertEqual(coerce_int(False, 3), 3)
        self.assertEqual(coerce_int("7", 0), 7)
        self.assertEqual(coerce_int("abc", 9), 9)
        self.assertEqual(coerce_int(None, 4), 4)
        self.assertEqual(coerce_int(5, 0), 5)

    def test_create_player_record_rejects_boolean_counts(self):
        player = create_player_record(
            "Pilot",
            lives=True,
            shield_charges=True,
            lifetime_score=True,
            credits=True,
            sold_lives=True,
            sold_shields=True,
        )
        self.assertEqual(player["lives"], 3)  # default, not bool-as-1
        self.assertEqual(player["shield_charges"], 0)
        self.assertEqual(player["lifetime_score"], 0)
        self.assertEqual(player["credits"], 0)
        self.assertEqual(player["sold_lives"], 0)
        self.assertEqual(player["sold_shields"], 0)


    # --- Issues #15/#16: badge stat checks and marking ---
    def test_create_player_record_has_badge_lists(self):
        player = create_player_record("Pilot")
        self.assertEqual(player["high_score_lessons"], [])
        self.assertEqual(player["quick_lessons"], [])

    def test_create_player_record_time_stop_charges(self):
        self.assertEqual(create_player_record("Pilot")["time_stop_charges"], 0)
        self.assertEqual(create_player_record("Pilot", time_stop_charges=2)["time_stop_charges"], 2)
        self.assertEqual(create_player_record("Pilot", time_stop_charges=True)["time_stop_charges"], 0)

    def test_mission_stats_are_high_score(self):
        base = {"lesson_number": 7, "won": True, "score": 9800, "high_score_goal": 9800}
        self.assertTrue(mission_stats_are_high_score(base, 7))
        self.assertFalse(mission_stats_are_high_score({**base, "score": 9799}, 7))   # below goal
        self.assertFalse(mission_stats_are_high_score({**base, "won": False}, 7))    # lost
        self.assertFalse(mission_stats_are_high_score(base, 8))                       # wrong lesson
        self.assertFalse(mission_stats_are_high_score({**base, "high_score_goal": 0}, 7))

    def test_mission_stats_are_quick(self):
        base = {"lesson_number": 7, "won": True, "level_time_ms": 45000, "quick_time_goal_ms": 60000}
        self.assertTrue(mission_stats_are_quick(base, 7))
        self.assertFalse(mission_stats_are_quick({**base, "level_time_ms": 60001}, 7))  # too slow
        self.assertFalse(mission_stats_are_quick({**base, "won": False}, 7))            # lost
        self.assertFalse(mission_stats_are_quick({**base, "level_time_ms": 0}, 7))      # no time recorded

    def test_record_latest_marks_high_score_and_quick(self):
        player = create_player_record("Pilot")
        player["last_mission_stats"] = {
            "lesson_number": 3,
            "won": True,
            "score": 5000,
            "high_score_goal": 5000,
            "level_time_ms": 30000,
            "quick_time_goal_ms": 60000,
            "hits_taken": 1,            # not perfect
            "accurate_inputs": 5,
            "inaccurate_inputs": 1,
        }
        record_latest_mission_achievement_progress(player, 3)
        self.assertIn(3, player["high_score_lessons"])
        self.assertIn(3, player["quick_lessons"])
        self.assertNotIn(3, player["perfect_lessons"])

    def test_high_scorer_and_quickest_defender_achievements(self):
        all_lessons = list(range(1, 37))
        player = create_player_record(
            "Pilot", high_score_lessons=all_lessons, quick_lessons=all_lessons
        )
        met = achievement_requirements_met(player, total_lessons=36)
        self.assertIn("high_scorer", met)
        self.assertIn("quickest_defender", met)
        # missing one lesson -> not yet earned
        partial = create_player_record("Pilot2", high_score_lessons=all_lessons[:-1])
        self.assertNotIn("high_scorer", achievement_requirements_met(partial, total_lessons=36))


if __name__ == "__main__":
    unittest.main()
