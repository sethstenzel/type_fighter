from __future__ import annotations

import player_limits
from game_config import ACHIEVEMENTS, UPGRADE_CATALOG


DEFAULT_POD = {"color": "blue", "type": "standard", "upgrades": []}
PLAYER_SHIELD_BASE_CHARGES = 3
CONSUMABLE_UPGRADE_IDS = {"extra_life", "shield_charge", "shield_charge_3"}
SINGLE_ENTRY_UPGRADE_IDS = {"drone_splash_color", "ammo_charge_color"}
RANK_ORDER = ("Rookie", "Private", "Lieutenant", "Captain", "Major")
UPGRADE_COLORS = (
    ("Red", (219, 92, 101)),
    ("Orange", (240, 158, 74)),
    ("Yellow", (246, 216, 79)),
    ("Green", (88, 214, 141)),
    ("Teal", (72, 209, 204)),
    ("Cyan", (116, 211, 255)),
    ("Blue", (112, 170, 255)),
    ("Indigo", (112, 118, 255)),
    ("Purple", (153, 92, 214)),
    ("Pink", (238, 111, 176)),
    ("Rose", (244, 124, 143)),
    ("Gold", (255, 184, 77)),
)


def normalize_pod_upgrades(upgrades):
    if not isinstance(upgrades, list):
        return []
    normalized = []
    single_entry_indexes = {}
    for upgrade in upgrades:
        if isinstance(upgrade, str):
            if upgrade in CONSUMABLE_UPGRADE_IDS:
                continue
            normalized_upgrade = {"id": upgrade}
        elif isinstance(upgrade, dict) and isinstance(upgrade.get("id"), str):
            if upgrade["id"] in CONSUMABLE_UPGRADE_IDS:
                continue
            normalized_upgrade = {"id": upgrade["id"]}
            if isinstance(upgrade.get("color"), str):
                normalized_upgrade["color"] = upgrade["color"]
        else:
            continue
        upgrade_id = normalized_upgrade["id"]
        if upgrade_id in SINGLE_ENTRY_UPGRADE_IDS:
            existing_index = single_entry_indexes.get(upgrade_id)
            if existing_index is not None:
                normalized[existing_index] = normalized_upgrade
                continue
            single_entry_indexes[upgrade_id] = len(normalized)
        normalized.append(normalized_upgrade)
    return normalized


def upgrade_ids(player):
    if not isinstance(player, dict):
        return set()
    pod = player.get("pod", {}) if isinstance(player, dict) else {}
    upgrades = pod.get("upgrades", []) if isinstance(pod, dict) else []
    ids = {
        upgrade.get("id")
        for upgrade in normalize_pod_upgrades(upgrades)
        if isinstance(upgrade, dict) and isinstance(upgrade.get("id"), str)
    }
    ids.update(
        upgrade_id
        for upgrade_id in normalize_string_list(player.get("purchased_upgrade_ids", []))
        if upgrade_id not in CONSUMABLE_UPGRADE_IDS
    )
    return ids


def has_upgrade(player, upgrade_id):
    return upgrade_id in upgrade_ids(player)


def player_shield_max_charges(player):
    charges = PLAYER_SHIELD_BASE_CHARGES
    if has_upgrade(player, "extra_shield_slot_1"):
        charges += 1
    if has_upgrade(player, "extra_shield_slot_2"):
        charges += 1
    if has_achievement(player, "fully_upgraded"):
        charges += 1
    return charges


def set_player_shield_base_charges(charges):
    global PLAYER_SHIELD_BASE_CHARGES
    PLAYER_SHIELD_BASE_CHARGES = max(0, int(charges))


def normalize_string_list(values):
    if not isinstance(values, list):
        return []
    return sorted({str(value).strip() for value in values if str(value).strip()})


def normalize_achievement_awards(values):
    if isinstance(values, dict):
        normalized = {}
        for achievement_id, awarded in values.items():
            if isinstance(achievement_id, str) and achievement_id.strip():
                normalized[achievement_id.strip()] = bool(awarded)
        return normalized
    return {achievement_id: True for achievement_id in normalize_string_list(values)}


def normalized_achievement_ids(values):
    return {
        achievement_id
        for achievement_id, awarded in normalize_achievement_awards(values).items()
        if awarded
    }


def has_achievement(player, achievement_id):
    return achievement_id in normalized_achievement_ids(player.get("achievements", {}))


def normalize_lesson_number_list(values):
    normalized = []
    if not isinstance(values, list):
        return normalized
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            normalized.append(number)
    return sorted(set(normalized))


def create_player_record(
    name,
    completed_lessons=None,
    lives=3,
    lifetime_score=0,
    achievements=None,
    credits=0,
    pod=None,
    purchased_upgrade_ids=None,
    shield_charges=0,
    perfect_lessons=None,
    last_mission_stats=None,
    sold_lives=0,
    sold_shields=0,
    player_id=None,
):
    pod = dict(DEFAULT_POD if pod is None else pod)
    pod_upgrades = normalize_pod_upgrades(pod.get("upgrades", []))
    upgrade_id_set = {
        upgrade.get("id")
        for upgrade in pod_upgrades
        if isinstance(upgrade, dict) and isinstance(upgrade.get("id"), str)
    }
    if "extra_shield_slot_1" in upgrade_id_set:
        shield_charges = min(max(shield_charges, 0), 4)
    if "extra_shield_slot_2" in upgrade_id_set:
        shield_charges = min(max(shield_charges, 0), 5)
    achievement_awards = normalize_achievement_awards(achievements)
    if achievement_awards.get("fully_upgraded"):
        shield_charges = min(max(shield_charges, 0), 6)
    return {
        "id": player_id,
        "name": str(name).strip()[:24],
        "completed_lessons": normalize_lesson_number_list(completed_lessons or []),
        "lives": max(1, min(player_limits.MAX_PLAYER_LIVES, int(lives or 3))),
        "shield_charges": max(0, int(shield_charges or 0)),
        "lifetime_score": max(0, int(lifetime_score or 0)),
        "achievements": achievement_awards,
        "purchased_upgrade_ids": normalize_string_list(purchased_upgrade_ids),
        "sold_lives": max(0, int(sold_lives or 0)),
        "sold_shields": max(0, int(sold_shields or 0)),
        "credits": max(0, int(credits or 0)),
        "perfect_lessons": normalize_lesson_number_list(perfect_lessons),
        "last_mission_stats": last_mission_stats if isinstance(last_mission_stats, dict) else {},
        "pod": {
            "color": str(pod.get("color", "blue")),
            "type": str(pod.get("type", "standard")),
            "upgrades": pod_upgrades,
        },
    }


def completed_prefix_count(player):
    completed = set(player.get("completed_lessons", []))
    count = 0
    for lesson_number in range(1, 10_000):
        if lesson_number not in completed:
            break
        count += 1
    return count


def unlocked_lesson_count(player, total_lessons=36):
    return min(total_lessons, completed_prefix_count(player) + 1)


def player_rank(player):
    unlocked = unlocked_lesson_count(player)
    if unlocked <= 4:
        return "Rookie"
    if unlocked <= 9:
        return "Private"
    if unlocked <= 19:
        return "Lieutenant"
    if unlocked <= 29:
        return "Captain"
    return "Major"


def achievement_count(player):
    return len(normalized_achievement_ids(player.get("achievements", {})))


def player_credits(player):
    try:
        return max(0, int(player.get("credits", 0)))
    except (TypeError, ValueError):
        return 0


def player_lives(player):
    try:
        return max(1, int(player.get("lives", 3)))
    except (TypeError, ValueError):
        return 3


def rank_at_least(player, minimum_rank):
    try:
        return RANK_ORDER.index(player_rank(player)) >= RANK_ORDER.index(minimum_rank)
    except ValueError:
        return False


def upgrade_by_id(upgrade_id):
    return next((upgrade for upgrade in UPGRADE_CATALOG if upgrade["id"] == upgrade_id), None)


def upgrade_lock_reason(player, upgrade):
    if not upgrade.get("repeatable") and has_upgrade(player, upgrade["id"]):
        return "Owned"
    if upgrade["id"] == "extra_life" and player_lives(player) >= player_limits.MAX_PLAYER_LIVES:
        return "Life max"
    min_unlocked = upgrade.get("min_unlocked")
    if min_unlocked and unlocked_lesson_count(player) < min_unlocked:
        return upgrade["requirement"]
    min_rank = upgrade.get("min_rank")
    if min_rank and not rank_at_least(player, min_rank):
        return upgrade["requirement"]
    required_upgrade = upgrade.get("requires_upgrade")
    if required_upgrade and not has_upgrade(player, required_upgrade):
        required = upgrade_by_id(required_upgrade)
        return f"Requires {required['name']}" if required else "Locked"
    if player_credits(player) < upgrade["cost"]:
        return "Need credits"
    if upgrade["id"] in ("shield_charge", "shield_charge_3"):
        max_charges = player_shield_max_charges(player)
        if int(player.get("shield_charges", 0) or 0) >= max_charges:
            return "Shield full"
    return None


def upgrade_is_progress_locked(player, upgrade):
    reason = upgrade_lock_reason(player, upgrade)
    return bool(reason and reason not in ("Not enough credits", "Already purchased"))


def upgrade_shows_purchased(player, upgrade):
    purchased_upgrade_ids = {
        "extra_shield_slot_1",
        "extra_shield_slot_2",
        "defense_drone",
        "second_defense_drone",
    }
    return upgrade["id"] in purchased_upgrade_ids and has_upgrade(player, upgrade["id"])


def upgrade_color(player, upgrade_id):
    pod = player.get("pod", {}) if isinstance(player, dict) else {}
    upgrades = pod.get("upgrades", []) if isinstance(pod, dict) else []
    for upgrade in reversed(normalize_pod_upgrades(upgrades)):
        if upgrade.get("id") == upgrade_id and isinstance(upgrade.get("color"), str):
            return upgrade["color"]
    return None


def color_value(color_name):
    for name, color in UPGRADE_COLORS:
        if name == color_name:
            return color
    return None


def disabled_icon_name(icon_name):
    if not isinstance(icon_name, str) or not icon_name.endswith(".png"):
        return icon_name
    return f"{icon_name[:-4]}_disabled.png"


def add_pod_upgrade(player, upgrade, color_name=None):
    pod = player.setdefault("pod", dict(DEFAULT_POD))
    upgrades = normalize_pod_upgrades(pod.get("upgrades", []))
    entry = {"id": upgrade["id"]}
    if color_name:
        entry["color"] = color_name
    if upgrade["id"] in SINGLE_ENTRY_UPGRADE_IDS:
        upgrades = [existing for existing in upgrades if existing.get("id") != upgrade["id"]]
    upgrades.append(entry)
    pod["upgrades"] = upgrades


def remove_pod_upgrade_entries(player, upgrade_id, count):
    pod = player.setdefault("pod", dict(DEFAULT_POD))
    upgrades = normalize_pod_upgrades(pod.get("upgrades", []))
    remaining = []
    removed = 0
    for entry in reversed(upgrades):
        if removed < count and entry.get("id") == upgrade_id:
            removed += 1
            continue
        remaining.append(entry)
    pod["upgrades"] = list(reversed(remaining))
    return removed


def apply_upgrade_purchase(player, upgrade, color_name=None):
    player["credits"] = max(0, player_credits(player) - upgrade["cost"])
    purchased = set(normalize_string_list(player.get("purchased_upgrade_ids", [])))
    purchased.add(upgrade["id"])
    player["purchased_upgrade_ids"] = sorted(purchased)
    if upgrade["id"] == "extra_life":
        player["lives"] = min(player_limits.MAX_PLAYER_LIVES, player_lives(player) + 1)
    elif upgrade["id"] == "shield_charge":
        player["shield_charges"] = min(player_shield_max_charges(player), int(player.get("shield_charges", 0)) + 1)
    elif upgrade["id"] == "shield_charge_3":
        player["shield_charges"] = min(player_shield_max_charges(player), int(player.get("shield_charges", 0)) + 3)
    else:
        add_pod_upgrade(player, upgrade, color_name)
        if upgrade["id"].startswith("extra_shield_slot"):
            player["shield_charges"] = min(player_shield_max_charges(player), int(player.get("shield_charges", 0)))


def max_sell_quantity(player, upgrade):
    if upgrade["id"] == "extra_life":
        return max(0, player_lives(player) - 3)
    if upgrade["id"] == "shield_charge":
        try:
            return max(0, int(player.get("shield_charges", 0)))
        except (TypeError, ValueError):
            return 0
    return 0


def upgrade_can_sell(player, upgrade):
    return upgrade["id"] in ("extra_life", "shield_charge") and max_sell_quantity(player, upgrade) > 0


def upgrade_sell_value(upgrade):
    return max(0, upgrade["cost"] // 2)


def apply_upgrade_sale(player, upgrade, quantity):
    try:
        quantity = max(0, int(quantity))
    except (TypeError, ValueError):
        quantity = 0
    if upgrade["id"] == "extra_life":
        quantity = min(quantity, max_sell_quantity(player, upgrade))
        player["lives"] = max(3, player_lives(player) - quantity)
        player["sold_lives"] = max(0, int(player.get("sold_lives", 0) or 0)) + quantity
    elif upgrade["id"] == "shield_charge":
        quantity = min(quantity, max_sell_quantity(player, upgrade))
        player["shield_charges"] = max(0, int(player.get("shield_charges", 0) or 0) - quantity)
        player["sold_shields"] = max(0, int(player.get("sold_shields", 0) or 0)) + quantity
    else:
        return
    player["credits"] = player_credits(player) + upgrade_sell_value(upgrade) * quantity


def mark_lesson_complete(player, lesson_number):
    completed = set(player.get("completed_lessons", []))
    completed.add(lesson_number)
    player["completed_lessons"] = sorted(completed)


def mission_accuracy_percent(stats):
    if not isinstance(stats, dict):
        return 0
    if "accuracy_percent" in stats:
        try:
            return int(stats.get("accuracy_percent", 0))
        except (TypeError, ValueError):
            return 0
    try:
        accurate_inputs = max(0, int(stats.get("accurate_inputs", 0) or 0))
        inaccurate_inputs = max(0, int(stats.get("inaccurate_inputs", 0) or 0))
    except (TypeError, ValueError):
        return 0
    total_inputs = accurate_inputs + inaccurate_inputs
    return 100 if total_inputs == 0 else round(accurate_inputs * 100 / total_inputs)


def mission_stats_are_perfect(stats, lesson_number):
    if not isinstance(stats, dict):
        return False
    try:
        hits_taken = int(stats.get("hits_taken", 0) or 0)
        inaccurate_inputs = int(stats.get("inaccurate_inputs", 0) or 0)
    except (TypeError, ValueError):
        return False
    return (
        stats.get("lesson_number") == lesson_number
        and bool(stats.get("won"))
        and hits_taken == 0
        and inaccurate_inputs == 0
        and mission_accuracy_percent(stats) == 100
    )


def achievement_by_id(achievement_id):
    for achievement in ACHIEVEMENTS:
        if achievement.get("id") == achievement_id:
            return achievement
    return None


def award_achievement(player, achievement_id):
    achievement = achievement_by_id(achievement_id)
    if achievement is None:
        return None
    current = normalize_achievement_awards(player.get("achievements", {}))
    if current.get(achievement_id):
        return None
    current[achievement_id] = True
    player["achievements"] = current
    player["credits"] = player_credits(player) + int(achievement.get("reward_credits", 0) or 0)
    try:
        lifetime_score = int(player.get("lifetime_score", 0) or 0)
    except (TypeError, ValueError):
        lifetime_score = 0
    player["lifetime_score"] = max(0, lifetime_score) + int(achievement.get("score", 0) or 0)
    if achievement_id == "fully_upgraded":
        player["shield_charges"] = min(player_shield_max_charges(player), int(player.get("shield_charges", 0) or 0))
    return achievement


def purchased_upgrade_id_set(player):
    purchased = set(normalize_string_list(player.get("purchased_upgrade_ids", [])))
    purchased.update(upgrade_ids(player))
    if player_lives(player) > 3:
        purchased.add("extra_life")
    try:
        shield_charges = int(player.get("shield_charges", 0) or 0)
    except (TypeError, ValueError):
        shield_charges = 0
    if shield_charges > 0:
        purchased.add("shield_charge")
    return purchased


def record_latest_mission_achievement_progress(player, lesson_number):
    stats = player.get("last_mission_stats", {})
    if mission_stats_are_perfect(stats, lesson_number):
        perfect_lessons = set(normalize_lesson_number_list(player.get("perfect_lessons", [])))
        perfect_lessons.add(lesson_number)
        player["perfect_lessons"] = sorted(perfect_lessons)


def achievement_requirements_met(player, lesson_number=None, total_lessons=36):
    met = []
    rank_requirements = (
        ("private_rank", "Private"),
        ("lieutenant_rank", "Lieutenant"),
        ("captain_rank", "Captain"),
        ("major_rank", "Major"),
    )
    for achievement_id, required_rank in rank_requirements:
        if rank_at_least(player, required_rank):
            met.append(achievement_id)

    perfect_lessons = set(normalize_lesson_number_list(player.get("perfect_lessons", [])))
    if len(perfect_lessons) >= 5:
        met.append("seeking_perfection")
    if len(perfect_lessons) >= 20:
        met.append("near_perfection")
    if set(range(1, total_lessons + 1)).issubset(perfect_lessons):
        met.append("totally_perfect")
    if player_lives(player) >= player_limits.MAX_PLAYER_LIVES:
        met.append("living_forever")
    upgrade_catalog_ids = {upgrade["id"] for upgrade in UPGRADE_CATALOG}
    if upgrade_catalog_ids and upgrade_catalog_ids.issubset(purchased_upgrade_id_set(player)):
        met.append("fully_upgraded")
    completed = set(player.get("completed_lessons", []))
    if set(range(1, total_lessons + 1)).issubset(completed):
        met.append("typing_master")
    if int(player.get("sold_lives", 0) or 0) >= 50 and int(player.get("sold_shields", 0) or 0) >= 50:
        met.append("quartermaster")
    stats = player.get("last_mission_stats", {})
    if (
        isinstance(stats, dict)
        and stats.get("lesson_number") == lesson_number
        and stats.get("won")
        and stats.get("starting_shield_charges", 0) >= 6
        and stats.get("ending_shield_charges") == 0
        and (stats.get("no_damage_taken") or stats.get("hits_taken", 0) == 0)
    ):
        met.append("shields_up")
    earned = set(normalized_achievement_ids(player.get("achievements", {})))
    return [achievement_id for achievement_id in met if achievement_id not in earned]
