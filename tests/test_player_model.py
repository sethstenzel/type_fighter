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
    create_player_record,
    normalize_pod_upgrades,
    player_credits,
    player_shield_max_charges,
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


if __name__ == "__main__":
    unittest.main()
