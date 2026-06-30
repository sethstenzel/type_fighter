import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import cheats


class CheatTests(unittest.TestCase):
    def setUp(self):
        cheats.enable_from_argv([])  # start each test with no cheats

    def tearDown(self):
        cheats.enable_from_argv([])  # never leak cheat state into other tests

    def test_parse_equals_and_space_forms(self):
        self.assertEqual(cheats.parse_cheat_arg(["--cheats=1,4,5"]), ["1", "4", "5"])
        self.assertEqual(cheats.parse_cheat_arg(["--cheats", "2, 3 ,0"]), ["2", "3", "0"])
        self.assertEqual(cheats.parse_cheat_arg(["game.py"]), [])

    def test_enable_validates_and_reports_unknown(self):
        enabled, unknown = cheats.enable_from_argv(["--cheats", "1,4,99,foo"])
        self.assertEqual(enabled, {"1", "4"})
        self.assertEqual(unknown, ["99", "foo"])
        self.assertTrue(cheats.is_enabled("1"))
        self.assertTrue(cheats.is_enabled("4"))
        self.assertFalse(cheats.is_enabled("99"))

    def test_cheat_10_marks_all_levels_unlocked(self):
        from lessons.lesson_config import LESSON_PROGRESS

        cheats.enable_from_argv(["--cheats", "10"])
        player = {"completed_lessons": []}
        cheats.apply_player_cheats(player)
        self.assertEqual(player["completed_lessons"], list(range(1, len(LESSON_PROGRESS))))

    def test_multi_digit_cheat_id(self):
        enabled, unknown = cheats.enable_from_argv(["--cheats", "11,1"])
        self.assertEqual(enabled, {"11", "1"})
        self.assertEqual(unknown, [])
        self.assertTrue(cheats.is_enabled("11"))

    def test_listing_request(self):
        self.assertTrue(cheats.wants_listing(["--cheats", "list"]))
        self.assertTrue(cheats.wants_listing(["--cheats=help"]))
        self.assertFalse(cheats.wants_listing(["--cheats", "1"]))

    def test_apply_player_cheats_sets_values(self):
        cheats.enable_from_argv(["--cheats", "1,7"])
        player = {"lives": 3, "credits": 5}
        cheats.apply_player_cheats(player)
        self.assertEqual(player["lives"], cheats.CHEAT_LIVES)
        self.assertEqual(player["credits"], cheats.CHEAT_CREDITS)

    def test_apply_player_cheats_resets(self):
        cheats.enable_from_argv(["--cheats", "8,9"])
        player = {"lifetime_score": 900, "achievements": {"a": True}}
        cheats.apply_player_cheats(player)
        self.assertEqual(player["lifetime_score"], 0)
        self.assertEqual(player["achievements"], {})

    def test_apply_player_cheats_full_reset(self):
        cheats.enable_from_argv(["--cheats", "0"])
        player = {
            "completed_lessons": [1, 2, 3],
            "credits": 500,
            "lifetime_score": 900,
            "achievements": {"a": True},
            "perfect_lessons": [1],
            "high_score_lessons": [1, 2],
            "quick_lessons": [3],
            "last_mission_stats": {"lesson_number": 3, "won": True, "score": 9999},
            "purchased_upgrade_ids": ["defense_drone"],
            "pod": {"color": "red", "type": "standard", "upgrades": [{"id": "defense_drone"}]},
            "lives": 12,
            "shield_charges": 4,
            "time_stop_charges": 3,
        }
        cheats.apply_player_cheats(player)
        self.assertEqual(player["completed_lessons"], [])
        self.assertEqual(player["credits"], 0)
        self.assertEqual(player["lifetime_score"], 0)
        self.assertEqual(player["achievements"], {})
        self.assertEqual(player["perfect_lessons"], [])
        self.assertEqual(player["high_score_lessons"], [])
        self.assertEqual(player["quick_lessons"], [])
        self.assertEqual(player["last_mission_stats"], {})
        # purchases undone
        self.assertEqual(player["purchased_upgrade_ids"], [])
        self.assertEqual(player["pod"]["upgrades"], [])
        self.assertEqual(player["lives"], 3)
        self.assertEqual(player["shield_charges"], 0)
        self.assertEqual(player["time_stop_charges"], 0)


    def test_log_cheat_event_writes_cheats_log(self):
        import os
        import tempfile

        import player_storage_sqlite

        with tempfile.TemporaryDirectory() as tmp:
            saved = {key: os.environ.get(key) for key in ("APPDATA", "XDG_DATA_HOME")}
            os.environ["APPDATA"] = tmp
            os.environ["XDG_DATA_HOME"] = tmp
            try:
                cheats.log_cheat_event("auto-fire level=3 score=123")
                log_path = player_storage_sqlite.user_data_dir() / "cheats.log"
                self.assertTrue(log_path.exists())
                self.assertIn("auto-fire level=3 score=123", log_path.read_text(encoding="utf-8"))
            finally:
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
