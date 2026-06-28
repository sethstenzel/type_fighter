import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contracts import API_CONTRACT_NOTES, PLAYER_SESSION_HEADER


class ContractTests(unittest.TestCase):
    def test_player_session_header_is_explicit(self):
        self.assertEqual(PLAYER_SESSION_HEADER, "X-Player-Session")
        self.assertIn(PLAYER_SESSION_HEADER, API_CONTRACT_NOTES["players"]["PUT /players/{player_id}"])

    def test_session_replacement_errors_are_documented(self):
        self.assertIn("401 PLAYER_SESSION_EXPIRED", API_CONTRACT_NOTES["session_errors"])
        self.assertIn("409 PLAYER_SESSION_REPLACED", API_CONTRACT_NOTES["session_errors"])


if __name__ == "__main__":
    unittest.main()
