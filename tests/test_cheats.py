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
        }
        cheats.apply_player_cheats(player)
        self.assertEqual(player["completed_lessons"], [])
        self.assertEqual(player["credits"], 0)
        self.assertEqual(player["lifetime_score"], 0)
        self.assertEqual(player["achievements"], {})
        self.assertEqual(player["perfect_lessons"], [])


if __name__ == "__main__":
    unittest.main()
