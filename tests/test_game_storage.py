import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import player_storage_sqlite as storage
from player_model import create_player_record
import game


class NormalizePlayersTests(unittest.TestCase):
    def test_dedupes_by_name_case_insensitive(self):
        players = game.normalize_players(
            [{"name": "Ace"}, {"name": "ace"}, {"name": "Bee"}]
        )
        self.assertEqual([p["name"] for p in players], ["Ace", "Bee"])

    def test_clamps_lives_and_rejects_bool(self):
        players = game.normalize_players(
            [
                {"name": "Hi", "lives": 9999, "shield_charges": -5},
                {"name": "Bo", "lives": True, "shield_charges": True},
            ]
        )
        by_name = {p["name"]: p for p in players}
        self.assertLessEqual(by_name["Hi"]["lives"], game.player_limits.MAX_PLAYER_LIVES)
        self.assertGreaterEqual(by_name["Hi"]["lives"], 1)
        self.assertEqual(by_name["Hi"]["shield_charges"], 0)  # clamped up from -5
        self.assertEqual(by_name["Bo"]["lives"], game.STARTING_LIVES)  # bool -> default
        self.assertEqual(by_name["Bo"]["shield_charges"], 0)

    def test_skips_non_dict_and_unnamed_entries(self):
        players = game.normalize_players(["x", 5, {}, {"name": "   "}, {"name": "Real"}])
        self.assertEqual([p["name"] for p in players], ["Real"])

    def test_legacy_save_without_new_fields_gets_defaults(self):
        # An old save predating the scoring/timer features must load gracefully.
        legacy = {"name": "Legacy", "lives": 5, "completed_lessons": [1, 2], "credits": 100}
        player = game.normalize_players([legacy])[0]
        self.assertEqual(player["high_score_lessons"], [])
        self.assertEqual(player["quick_lessons"], [])
        self.assertEqual(player["perfect_lessons"], [])
        self.assertEqual(player["time_dilation_charges"], 0)
        self.assertEqual(player["lives"], 5)


class BadgeUnlockModalTests(unittest.TestCase):
    def _stats(self, **over):
        base = {
            "lesson_number": 3,
            "won": True,
            "score": 5000,
            "high_score_goal": 5000,
            "level_time_ms": 30000,
            "quick_time_goal_ms": 60000,
        }
        base.update(over)
        return base

    def test_modals_emitted_when_newly_earned(self):
        player = create_player_record("M")
        player["last_mission_stats"] = self._stats()
        modals = game.collect_badge_unlock_modals(player, 3)
        titles = [m["title"] for m in modals]
        self.assertIn("High Scorer!", titles)
        self.assertIn("Quick Defender!", titles)
        high = next(m for m in modals if m["title"] == "High Scorer!")
        self.assertIn("5000", high["text"])  # shows required goal and achieved score

    def test_no_modal_when_already_earned(self):
        player = create_player_record("M", high_score_lessons=[3], quick_lessons=[3])
        player["last_mission_stats"] = self._stats()
        self.assertEqual(game.collect_badge_unlock_modals(player, 3), [])

    def test_only_qualified_badges_emit(self):
        player = create_player_record("M")
        player["last_mission_stats"] = self._stats(score=10)  # below high-score goal
        titles = [m["title"] for m in game.collect_badge_unlock_modals(player, 3)]
        self.assertNotIn("High Scorer!", titles)
        self.assertIn("Quick Defender!", titles)

    def test_wrap_plain_text_handles_newlines(self):
        # Regression: wrap_plain_text was missing, crashing every reward modal.
        import pygame

        pygame.font.init()
        font = pygame.font.SysFont("arial", 20)
        self.assertEqual(game.wrap_plain_text("alpha\n\nbeta", font, 1000), ["alpha", "", "beta"])


class SaveRoundTripTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._saved_env = {key: os.environ.get(key) for key in ("APPDATA", "XDG_DATA_HOME")}
        # Redirect the save directory into a temp folder (Windows uses APPDATA,
        # other platforms use XDG_DATA_HOME).
        os.environ["APPDATA"] = self._tmp.name
        os.environ["XDG_DATA_HOME"] = self._tmp.name

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def test_write_then_read_round_trip(self):
        player = create_player_record(
            "Round Trip",
            completed_lessons=[1, 2, 3],
            lives=5,
            credits=420,
            lifetime_score=1500,
        )
        storage.write_player_db(player, "9.9.9")
        loaded = storage.read_player_db(storage.player_db_path("Round Trip"))

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["name"], "Round Trip")
        self.assertEqual(loaded["completed_lessons"], [1, 2, 3])
        self.assertEqual(loaded["lives"], 5)
        self.assertEqual(loaded["credits"], 420)
        self.assertEqual(loaded["lifetime_score"], 1500)
        self.assertEqual(loaded["game_version"], "9.9.9")
        self.assertTrue(loaded["id"])  # metadata assigned on write

    def test_load_player_dbs_returns_written_players(self):
        for name in ("Alpha", "Bravo"):
            storage.write_player_db(create_player_record(name), "1.0.0")
        loaded_names = sorted(p["name"] for p in storage.load_player_dbs())
        self.assertEqual(loaded_names, ["Alpha", "Bravo"])


if __name__ == "__main__":
    unittest.main()
