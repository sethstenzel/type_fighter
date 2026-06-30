import json
import sqlite3
from pathlib import Path


DEFAULT_GAME_SETTINGS = {
    "starting_lives": 3,
    "max_player_lives": 99,
    "player_shield_max_charges": 3,
    "energy_saver_bonus_credits": 50,
    "max_life_power_ups_per_mission": 4,
    "power_up_duration_ms": 5000,
    "power_up_warning_ms": 2000,
    "power_up_min_interval_ms": 18000,
    "power_up_max_interval_ms": 32000,
    "player_shield_start_lesson": 3,
    "player_active_shield_duration_ms": 9000,
    "player_active_shield_fade_start_ms": 6000,
    "player_active_shield_extra_hits": 2,
    "defense_drone_fire_interval_ms": 6000,
    "defense_drone_accuracy_grace_ms": 3000,
    "mega_charge_max_blocks": 5,
    "mega_recharge_interval_ms": 1000,
    "mega_recharge_delay_ms": 1000,
    "mega_shield_min_level": 3,
    "mega_final_kill_level": 5,
    "final_boss_attack_interval_ms": 4000,
    "final_boss_semi_boss_first_spawn_ms": 20000,
    "final_boss_semi_boss_spawn_interval_ms": 20000,
    "final_boss_count_by_lesson": {str(lesson): 1 for lesson in range(5, 37)},
    "accuracy_threshold_bands": [
        {"start": 1, "end": 3, "warning_threshold": 10, "limited_threshold": 10},
        {"start": 4, "end": 9, "warning_threshold": 40, "limited_threshold": 30},
        {"start": 10, "end": 19, "warning_threshold": 70, "limited_threshold": 60},
        {"start": 20, "end": 29, "warning_threshold": 75, "limited_threshold": 65},
        {"start": 30, "end": None, "warning_threshold": 80, "limited_threshold": 70},
    ],
    "time_stop_duration_ms": 7000,
    "time_stop_expand_ms": 450,
    "time_stop_contract_ms": 1500,
    "time_stop_min_speed_scale": 0.0,
    "time_stop_max_charges": 3,
    "time_stop_start_lesson": 27,
    "time_stop_unlock_lesson": 26,
    "time_stop_double_tap_ms": 600,
    "time_ring_alpha": 90,
}


DEFAULT_UPGRADES = [
    {
        "id": "extra_life",
        "name": "Extra Life",
        "cost": 200,
        "repeatable": True,
        "requirement": "Unlock mission 2",
        "min_unlocked": 2,
        "icon": "extra_life.png",
    },
    {
        "id": "shield_charge",
        "name": "Shield Charge",
        "cost": 300,
        "repeatable": True,
        "requirement": "Unlock mission 3",
        "min_unlocked": 3,
        "icon": "extra_shields.png",
    },
    {
        "id": "shield_charge_3",
        "name": "Shield Charge x3",
        "cost": 600,
        "repeatable": True,
        "requirement": "Unlock mission 3",
        "min_unlocked": 3,
        "icon": "extra_shields_3.png",
    },
    {
        "id": "extra_shield_slot_1",
        "name": "Extra Shield Slot 1",
        "cost": 2000,
        "repeatable": False,
        "requirement": "Lieutenant rank",
        "min_rank": "Lieutenant",
        "icon": "extra_shield_slot_1.png",
    },
    {
        "id": "extra_shield_slot_2",
        "name": "Extra Shield Slot 2",
        "cost": 2000,
        "repeatable": False,
        "requirement": "Captain rank",
        "min_rank": "Captain",
        "requires_upgrade": "extra_shield_slot_1",
        "icon": "extra_shield_slot_2.png",
    },
    {
        "id": "defense_drone",
        "name": "Defense Drone",
        "cost": 2500,
        "repeatable": False,
        "requirement": "Lieutenant rank",
        "min_rank": "Lieutenant",
        "icon": "defense_drone.png",
    },
    {
        "id": "second_defense_drone",
        "name": "Second Defense Drone",
        "cost": 2500,
        "repeatable": False,
        "requirement": "Captain rank",
        "min_rank": "Captain",
        "requires_upgrade": "defense_drone",
        "icon": "defense_drone.png",
    },
    {
        "id": "drone_splash_color",
        "name": "Player Splash Color",
        "cost": 250,
        "repeatable": True,
        "requirement": "Private rank",
        "min_rank": "Private",
        "color_choice": True,
        "icon": "player_splash_color.png",
    },
    {
        "id": "ammo_charge_color",
        "name": "Shot Charge Color",
        "cost": 500,
        "repeatable": True,
        "requirement": "Lieutenant rank",
        "min_rank": "Lieutenant",
        "color_choice": True,
        "icon": "shot_charge_color.png",
    },
]


DEFAULT_ACHIEVEMENTS = [
    {
        "id": "private_rank",
        "name": "Private",
        "text": "You reached Private rank. Your training discipline is starting to show.",
        "image": "rank_private_achievement.png",
        "reward_credits": 500,
        "score": 500,
        "sort_order": 10,
    },
    {
        "id": "lieutenant_rank",
        "name": "Lieutenant",
        "text": "You reached Lieutenant rank. Your keyboard control is combat-ready.",
        "image": "rank_lieutenant_achievement.png",
        "reward_credits": 750,
        "score": 750,
        "sort_order": 20,
    },
    {
        "id": "captain_rank",
        "name": "Captain",
        "text": "You reached Captain rank. You can lead from the home row under pressure.",
        "image": "rank_captain_achievement.png",
        "reward_credits": 1000,
        "score": 1000,
        "sort_order": 30,
    },
    {
        "id": "major_rank",
        "name": "Major",
        "text": "You reached Major rank. Your defense formation now supports a third defense drone.",
        "image": "rank_major_achievement.png",
        "reward_credits": 2000,
        "score": 2000,
        "sort_order": 40,
    },
    {
        "id": "shields_up",
        "name": "Shields Up",
        "text": "Start a mission with six shield charges, use all six, and finish without taking damage.",
        "image": "shields_up_achievement.png",
        "reward_credits": 300,
        "score": 300,
        "sort_order": 50,
    },
    {
        "id": "seeking_perfection",
        "name": "Seeking Perfection",
        "text": "Complete five lessons with no damage and perfect accuracy.",
        "image": "seeking_perfection_achievement.png",
        "reward_credits": 300,
        "score": 500,
        "sort_order": 60,
    },
    {
        "id": "near_perfection",
        "name": "Nearing Perfection",
        "text": "Complete twenty lessons with no damage and perfect accuracy.",
        "image": "nearing_perfection_achievement.png",
        "reward_credits": 300,
        "score": 1000,
        "sort_order": 70,
    },
    {
        "id": "totally_perfect",
        "name": "Total Perfection",
        "text": "Complete all main lessons with no damage and perfect accuracy.",
        "image": "total_perfection_achievement.png",
        "reward_credits": 300,
        "score": 2000,
        "sort_order": 80,
    },
    {
        "id": "living_forever",
        "name": "Living Forever",
        "text": "Build your reserve up to ninety-nine lives.",
        "image": "living_forever_achievement.png",
        "reward_credits": 300,
        "score": 750,
        "sort_order": 90,
    },
    {
        "id": "fully_upgraded",
        "name": "Fully Upgraded",
        "text": "Purchase every upgrade at least once and unlock the sixth shield slot.",
        "image": "fully_upgraded_achievement.png",
        "reward_credits": 0,
        "score": 1500,
        "sort_order": 100,
    },
    {
        "id": "typing_master",
        "name": "Typing Master",
        "text": "Complete every main lesson and prove mastery over the full keyboard.",
        "image": "typing_master_achievement.png",
        "reward_credits": 10000,
        "score": 5000,
        "sort_order": 110,
    },
    {
        "id": "quartermaster",
        "name": "Quartermaster",
        "text": "Sell fifty lives and fifty shield charges.",
        "image": "quartermaster_achievement.png",
        "reward_credits": 300,
        "score": 1000,
        "sort_order": 120,
    },
    {
        "id": "high_scorer",
        "name": "High Scorer",
        "text": "Earn the High Scorer badge on every main lesson by beating each level's score goal.",
        "image": "high_scorer_achievement.png",
        "reward_credits": 2000,
        "score": 3000,
        "sort_order": 130,
    },
    {
        "id": "quickest_defender",
        "name": "Quickest Defender",
        "text": "Earn the Quick Defender badge on every main lesson by clearing each level in time.",
        "image": "quickest_defender_achievement.png",
        "reward_credits": 2000,
        "score": 3000,
        "sort_order": 140,
    },
]



GAME_SETTINGS = dict(DEFAULT_GAME_SETTINGS)
UPGRADE_CATALOG = [dict(upgrade) for upgrade in DEFAULT_UPGRADES]
ACHIEVEMENTS = [dict(achievement) for achievement in DEFAULT_ACHIEVEMENTS]


def normalize_settings(settings):
    normalized = dict(DEFAULT_GAME_SETTINGS)
    if not isinstance(settings, dict):
        return normalized
    for key, default in DEFAULT_GAME_SETTINGS.items():
        value = settings.get(key, default)
        if isinstance(default, bool):
            normalized[key] = bool(value)
        elif isinstance(default, int):
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                normalized[key] = default
        elif isinstance(default, float):
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                normalized[key] = default
        elif isinstance(default, dict):
            normalized[key] = value if isinstance(value, dict) else dict(default)
        elif isinstance(default, list):
            normalized[key] = value if isinstance(value, list) else [dict(item) for item in default]
        else:
            normalized[key] = value
    return normalized


def normalize_upgrades(upgrades):
    default_by_id = {upgrade["id"]: dict(upgrade) for upgrade in DEFAULT_UPGRADES}
    ordered_ids = [upgrade["id"] for upgrade in DEFAULT_UPGRADES]
    if not isinstance(upgrades, list):
        return [default_by_id[upgrade_id] for upgrade_id in ordered_ids]

    for upgrade in upgrades:
        if not isinstance(upgrade, dict) or not isinstance(upgrade.get("id"), str):
            continue
        upgrade_id = upgrade["id"]
        merged = dict(default_by_id.get(upgrade_id, {}))
        merged.update(upgrade)
        default_by_id[upgrade_id] = merged
        if upgrade_id not in ordered_ids:
            ordered_ids.append(upgrade_id)
    return [default_by_id[upgrade_id] for upgrade_id in ordered_ids]


def normalize_achievements(achievements):
    default_by_id = {achievement["id"]: dict(achievement) for achievement in DEFAULT_ACHIEVEMENTS}
    ordered_ids = [achievement["id"] for achievement in DEFAULT_ACHIEVEMENTS]
    if not isinstance(achievements, list):
        return [default_by_id[achievement_id] for achievement_id in ordered_ids]
    for achievement in achievements:
        if not isinstance(achievement, dict) or not isinstance(achievement.get("id"), str):
            continue
        achievement = dict(achievement)
        achievement_id = achievement["id"]
        achievement["id"] = achievement_id
        merged = dict(default_by_id.get(achievement_id, {}))
        merged.update(achievement)
        default_by_id[achievement_id] = merged
        if achievement_id not in ordered_ids:
            ordered_ids.append(achievement_id)
    return sorted(
        [default_by_id[achievement_id] for achievement_id in ordered_ids],
        key=lambda item: (int(item.get("sort_order", 9999)), item.get("name", "")),
    )


def apply_config(config):
    if not isinstance(config, dict):
        return
    GAME_SETTINGS.clear()
    GAME_SETTINGS.update(normalize_settings(config.get("settings", {})))
    UPGRADE_CATALOG[:] = normalize_upgrades(config.get("upgrades", []))
    ACHIEVEMENTS[:] = normalize_achievements(config.get("achievements", []))


def load_cached_config(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    apply_config(data)
    return True


def save_cached_config(path):
    Path(path).write_text(
        json.dumps({"settings": GAME_SETTINGS, "upgrades": UPGRADE_CATALOG, "achievements": ACHIEVEMENTS}, indent=2),
        encoding="utf-8",
    )


def init_game_data_db(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS game_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS upgrades (
                id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                sort_order INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                sort_order INTEGER NOT NULL
            )
            """
        )
        if not connection.execute("SELECT 1 FROM game_settings LIMIT 1").fetchone():
            save_game_data_db(path)


def load_game_data_db(path):
    path = Path(path)
    if not path.exists():
        init_game_data_db(path)
        return False
    settings = {}
    upgrades = []
    achievements = []
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        for row in connection.execute("SELECT key, value_json FROM game_settings ORDER BY key"):
            try:
                settings[row["key"]] = json.loads(row["value_json"])
            except json.JSONDecodeError:
                continue
        for row in connection.execute("SELECT data_json FROM upgrades ORDER BY sort_order, id"):
            try:
                value = json.loads(row["data_json"])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                upgrades.append(value)
        for row in connection.execute("SELECT data_json FROM achievements ORDER BY sort_order, id"):
            try:
                value = json.loads(row["data_json"])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                achievements.append(value)
    apply_config({"settings": settings, "upgrades": upgrades, "achievements": achievements})
    return True


def save_game_data_db(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM game_settings")
        connection.execute("DELETE FROM upgrades")
        connection.execute("DELETE FROM achievements")
        for key, value in GAME_SETTINGS.items():
            connection.execute(
                "INSERT INTO game_settings (key, value_json) VALUES (?, ?)",
                (key, json.dumps(value, separators=(",", ":"))),
            )
        for sort_order, upgrade in enumerate(UPGRADE_CATALOG):
            connection.execute(
                "INSERT INTO upgrades (id, data_json, sort_order) VALUES (?, ?, ?)",
                (upgrade["id"], json.dumps(upgrade, separators=(",", ":")), sort_order),
            )
        for sort_order, achievement in enumerate(ACHIEVEMENTS):
            connection.execute(
                "INSERT INTO achievements (id, data_json, sort_order) VALUES (?, ?, ?)",
                (achievement["id"], json.dumps(achievement, separators=(",", ":")), sort_order),
            )
