import importlib
import json
import math
from pathlib import Path
import random
import re
import sys

import pygame

from lessons.lesson_config import LESSON_PROGRESS
from lessons.key_render import render_inline_text, render_key_label
from lessons.mission_engine import create_star_field, draw_star_field, update_star_field


SCREEN_SIZE = (1024, 768)
MIN_SCREEN_SIZE = (800, 600)
WINDOW_FLAGS = pygame.RESIZABLE
BG_COLOR = (8, 12, 24)
TEXT_COLOR = (230, 238, 255)
MUTED_TEXT = (138, 150, 178)
ACCENT = (72, 209, 204)
LOCKED_SELECTED = (245, 203, 92)
MENU_WHEEL_SCROLL_COOLDOWN_MS = 90
STARTING_LIVES = 3
PLAYER_SHIELD_MAX_CHARGES = 3
DEFAULT_POD = {"color": "blue", "type": "standard", "upgrades": []}
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
UPGRADE_CATALOG = (
    {
        "id": "extra_life",
        "name": "Extra Life",
        "cost": 50,
        "repeatable": True,
        "requirement": "Unlock mission 2",
        "min_unlocked": 2,
        "icon": "extra_life.png",
    },
    {
        "id": "shield_charge",
        "name": "Shield Charge",
        "cost": 100,
        "repeatable": True,
        "requirement": "Unlock mission 7",
        "min_unlocked": 7,
        "icon": "extra_shields.png",
    },
    {
        "id": "shield_charge_3",
        "name": "Shield Charge x3",
        "cost": 250,
        "repeatable": True,
        "requirement": "Unlock mission 7",
        "min_unlocked": 7,
        "icon": "extra_shields_3.png",
    },
    {
        "id": "extra_shield_slot_1",
        "name": "Extra Shield Slot 1",
        "cost": 1000,
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
        "name": "Drone Splash Color",
        "cost": 25,
        "repeatable": True,
        "requirement": "Private rank",
        "min_rank": "Private",
        "color_choice": True,
        "icon": "drone_splash_color.png",
    },
    {
        "id": "ammo_charge_color",
        "name": "Shot Charge Color",
        "cost": 50,
        "repeatable": True,
        "requirement": "Lieutenant rank",
        "min_rank": "Lieutenant",
        "color_choice": True,
        "icon": "shot_charge_color.png",
    },
)
RANK_ORDER = ("Rookie", "Private", "Lieutenant", "Captain", "Major")

def running_as_frozen_app():
    return getattr(sys, "frozen", False) or "__compiled__" in globals()


def app_base_dir():
    if running_as_frozen_app():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = app_base_dir()
PLAYERS_PATH = BASE_DIR / "players.json" if running_as_frozen_app() else BASE_DIR.parent / "players.json"
is_fullscreen = True
ui_image_cache = {}
ui_sound_cache = {}


LESSONS = [
    {
        "number": number,
        "title": f"Lesson {number}: {title}",
        "summary": summary,
        "intro_module": f"lessons.lesson_{number}.lesson_{number}_intro",
        "mission_module": f"lessons.lesson_{number}.lesson_{number}_mission",
    }
    for number, _, _, title, summary in LESSON_PROGRESS
]


def draw_text(surface, text, font, color, pos):
    render_inline_text(surface, text, font, color, pos)


def draw_scrollbar(surface, track_rect, total_items, visible_items, first_visible):
    if total_items <= visible_items:
        return

    pygame.draw.rect(surface, (18, 27, 48), track_rect, border_radius=4)
    pygame.draw.rect(surface, (43, 57, 89), track_rect, 1, border_radius=4)

    visible_ratio = visible_items / total_items
    thumb_height = max(28, int(track_rect.height * visible_ratio))
    max_first_visible = max(1, total_items - visible_items)
    travel = track_rect.height - thumb_height
    thumb_y = track_rect.y + int(travel * first_visible / max_first_visible)
    thumb_rect = pygame.Rect(track_rect.x + 2, thumb_y, track_rect.width - 4, thumb_height)
    pygame.draw.rect(surface, ACCENT, thumb_rect, border_radius=4)


def wheel_menu_step(event):
    if event.y > 0:
        return -1
    if event.y < 0:
        return 1
    return 0


def should_apply_menu_wheel(event, last_scroll_time):
    step = wheel_menu_step(event)
    now = pygame.time.get_ticks()
    if step == 0 or now - last_scroll_time < MENU_WHEEL_SCROLL_COOLDOWN_MS:
        return 0, last_scroll_time
    return step, now


def load_battle_image(path, size):
    try:
        image = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.smoothscale(image, size)
    except (OSError, pygame.error):
        return None


def create_mock_battle():
    return {
        "drones": [],
        "shots": [],
        "explosions": [],
        "next_spawn_time": 0,
        "next_shot_time": 0,
        "pod_rotation": 0,
        "defense_angle": 0,
        "pod_image": None,
        "turret_image": None,
        "defense_drone_image": None,
        "shot_image": None,
        "drone_images": [],
        "loaded": False,
    }


def load_mock_battle_assets(battle):
    if battle["loaded"]:
        return
    gfx_dir = BASE_DIR / "gfx"
    pod_dir = gfx_dir / "pod"
    drone_dir = gfx_dir / "drones"
    battle["pod_image"] = load_battle_image(pod_dir / "pod.png", (130, 130))
    battle["turret_image"] = load_battle_image(pod_dir / "turret.png", (72, 72))
    battle["defense_drone_image"] = load_battle_image(drone_dir / "defense_drone_image.png", (28, 28))
    battle["shot_image"] = load_battle_image(pod_dir / "shot.png", (18, 18))
    battle["drone_images"] = [
        image
        for image in (
            load_battle_image(drone_dir / "yellow_drone.png", (44, 44)),
            load_battle_image(drone_dir / "orange_drone.png", (50, 50)),
            load_battle_image(drone_dir / "red_drone.png", (54, 54)),
        )
        if image is not None
    ]
    battle["loaded"] = True


def mock_battle_pod_center(width, height, menu_right):
    return pygame.Vector2((menu_right + width) / 2, height / 2)


def mock_battle_spawn_drone(battle, width, height, menu_left):
    y = random.randint(120, max(121, height - 120))
    image = random.choice(battle["drone_images"]) if battle["drone_images"] else None
    battle["drones"].append(
        {
            "pos": pygame.Vector2(random.randint(-160, -60), y),
            "speed": random.uniform(34, 54),
            "radius": 24,
            "image": image,
            "letter": random.choice("asdfjkl;eiworu"),
            "rotation": random.uniform(0, math.tau),
            "targeted": False,
        }
    )


def draw_mock_battle_ship(screen, center, turret_angle, battle):
    if battle["pod_image"] is not None:
        rotated_pod = pygame.transform.rotozoom(battle["pod_image"], -math.degrees(battle["pod_rotation"]), 1.0)
        screen.blit(rotated_pod, rotated_pod.get_rect(center=center))
    else:
        points = [(center.x + 34, center.y), (center.x - 24, center.y - 30), (center.x - 24, center.y + 30)]
        pygame.draw.polygon(screen, (82, 137, 214), points)
        pygame.draw.polygon(screen, (210, 230, 255), points, 2)

    if battle["turret_image"] is not None:
        rotated_turret = pygame.transform.rotozoom(battle["turret_image"], -math.degrees(turret_angle) - 90, 1.0)
        screen.blit(rotated_turret, rotated_turret.get_rect(center=center))
    else:
        barrel_end = center + pygame.Vector2(math.cos(turret_angle), math.sin(turret_angle)) * 44
        pygame.draw.line(screen, ACCENT, center, barrel_end, 8)
        pygame.draw.circle(screen, (225, 243, 255), center, 12)

    defense_pos = center + pygame.Vector2(math.cos(battle["defense_angle"]), math.sin(battle["defense_angle"])) * 92
    defense_rotation = -battle["defense_angle"] * 4 + math.pi / 2
    if battle["defense_drone_image"] is not None:
        image = pygame.transform.rotozoom(battle["defense_drone_image"], math.degrees(defense_rotation), 1.0)
        screen.blit(image, image.get_rect(center=defense_pos))
    else:
        points = [
            (
                defense_pos.x + math.cos(defense_rotation + index * math.tau / 3) * 14,
                defense_pos.y + math.sin(defense_rotation + index * math.tau / 3) * 14,
            )
            for index in range(3)
        ]
        pygame.draw.polygon(screen, (145, 150, 156), points)
        pygame.draw.polygon(screen, (224, 228, 232), points, 2)


def update_and_draw_mock_battle(screen, battle, clock, menu_left, menu_right):
    load_mock_battle_assets(battle)
    width, height = screen.get_size()
    now = pygame.time.get_ticks()
    dt = min(0.05, clock.get_time() / 1000)
    pod_center = mock_battle_pod_center(width, height, menu_right)
    battle["pod_rotation"] = (battle["pod_rotation"] + math.tau * dt / 15) % math.tau
    battle["defense_angle"] = (battle["defense_angle"] + math.tau * dt / 10) % math.tau

    if now >= battle["next_spawn_time"] and len(battle["drones"]) < 6:
        mock_battle_spawn_drone(battle, width, height, menu_left)
        battle["next_spawn_time"] = now + random.randint(733, 1267)

    for drone in battle["drones"][:]:
        travel = pod_center - drone["pos"]
        if travel.length_squared() > 0:
            drone["pos"] += travel.normalize() * drone["speed"] * dt
        drone["rotation"] = (drone["rotation"] + math.tau * dt / 5) % math.tau
        if drone["pos"].distance_to(pod_center) < 44:
            battle["drones"].remove(drone)
            battle["explosions"].append({"pos": drone["pos"].copy(), "ttl": 0.42, "max_ttl": 0.42})

    if battle["drones"] and now >= battle["next_shot_time"]:
        available_targets = [drone for drone in battle["drones"] if not drone.get("targeted")]
        target = min(available_targets, key=lambda drone: drone["pos"].distance_squared_to(pod_center), default=None)
        if target is None:
            battle["next_shot_time"] = now + 250
        else:
            target["targeted"] = True
            direction = target["pos"] - pod_center
            if direction.length_squared() > 0:
                direction = direction.normalize()
                battle["shots"].append({"pos": pod_center + direction * 52, "vel": direction * 430, "target": target})
                battle["next_shot_time"] = now + random.randint(3600, 5200)

    for shot in battle["shots"][:]:
        target = shot["target"]
        if target not in battle["drones"]:
            battle["shots"].remove(shot)
            continue
        direction = target["pos"] - shot["pos"]
        if direction.length_squared() <= (target["radius"] + 7) ** 2:
            battle["drones"].remove(target)
            battle["shots"].remove(shot)
            battle["explosions"].append({"pos": target["pos"].copy(), "ttl": 0.32, "max_ttl": 0.32})
            continue
        if direction.length_squared() > 0:
            shot["vel"] = direction.normalize() * 430
        shot["pos"] += shot["vel"] * dt

    turret_targets = [drone for drone in battle["drones"] if not drone.get("targeted")]
    if not turret_targets:
        turret_targets = battle["drones"]
    target = min(turret_targets, key=lambda drone: drone["pos"].distance_squared_to(pod_center), default=None)
    turret_angle = 0 if target is None else math.atan2((target["pos"] - pod_center).y, (target["pos"] - pod_center).x)

    for explosion in battle["explosions"][:]:
        explosion["ttl"] -= dt
        if explosion["ttl"] <= 0:
            battle["explosions"].remove(explosion)
            continue
        alpha_scale = max(0, explosion["ttl"] / explosion["max_ttl"])
        radius = int(30 * (1 - alpha_scale) + 8)
        surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(surface, (255, 218, 125, int(150 * alpha_scale)), (radius + 2, radius + 2), radius, 3)
        screen.blit(surface, surface.get_rect(center=explosion["pos"]))

    for shot in battle["shots"]:
        if battle["shot_image"] is not None:
            angle = math.degrees(math.atan2(-shot["vel"].y, shot["vel"].x))
            image = pygame.transform.rotozoom(battle["shot_image"], angle, 1.0)
            screen.blit(image, image.get_rect(center=shot["pos"]))
        else:
            pygame.draw.circle(screen, (112, 241, 255), shot["pos"], 5)

    for drone in battle["drones"]:
        if drone["image"] is not None:
            image = pygame.transform.rotozoom(drone["image"], -math.degrees(drone["rotation"]), 1.0)
            screen.blit(image, image.get_rect(center=drone["pos"]))
        else:
            pygame.draw.circle(screen, ONE_SHOT_DRONE_COLOR, drone["pos"], drone["radius"])
            pygame.draw.circle(screen, (255, 231, 214), drone["pos"], drone["radius"], 2)
        label_font = pygame.font.SysFont("arial", 20, bold=True)
        render_key_label(screen, drone["letter"], label_font, (8, 10, 18), drone["pos"], drone["radius"] * 1.45)

    draw_mock_battle_ship(screen, pod_center, turret_angle, battle)


def normalize_pod_upgrades(upgrades):
    if not isinstance(upgrades, list):
        return []
    normalized = []
    for upgrade in upgrades:
        if isinstance(upgrade, str):
            normalized.append({"id": upgrade})
        elif isinstance(upgrade, dict) and isinstance(upgrade.get("id"), str):
            normalized_upgrade = {"id": upgrade["id"]}
            if isinstance(upgrade.get("color"), str):
                normalized_upgrade["color"] = upgrade["color"]
            normalized.append(normalized_upgrade)
    return normalized


def upgrade_ids(player):
    pod = player.get("pod", {})
    upgrades = pod.get("upgrades", []) if isinstance(pod, dict) else []
    return {
        upgrade.get("id")
        for upgrade in upgrades
        if isinstance(upgrade, dict) and isinstance(upgrade.get("id"), str)
    }


def has_upgrade(player, upgrade_id):
    return upgrade_id in upgrade_ids(player)


def player_shield_max_charges(player):
    max_charges = PLAYER_SHIELD_MAX_CHARGES
    if has_upgrade(player, "extra_shield_slot_1"):
        max_charges += 1
    if has_upgrade(player, "extra_shield_slot_2"):
        max_charges += 1
    return max_charges


def load_players():
    try:
        data = json.loads(PLAYERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        return []

    players = []
    seen_names = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name or name.lower() in seen_names:
            continue
        completed = item.get("completed_lessons", [])
        if not isinstance(completed, list):
            completed = []
        completed_lessons = sorted(
            {
                lesson
                for lesson in completed
                if isinstance(lesson, int) and 1 <= lesson <= len(LESSONS)
            }
        )
        lives = item.get("lives", STARTING_LIVES)
        if not isinstance(lives, int):
            lives = STARTING_LIVES
        shield_charges = item.get("shield_charges", 0)
        if not isinstance(shield_charges, int):
            shield_charges = 0
        players.append(
            create_player_record(
                name[:24],
                completed_lessons=completed_lessons,
                lives=max(1, lives),
                shield_charges=max(0, shield_charges),
                lifetime_score=item.get("lifetime_score", 0),
                achievements=item.get("achievements", []),
                credits=item.get("credits", 0),
                pod=item.get("pod", {}),
            )
        )
        seen_names.add(name.lower())
    return players


def save_players(players):
    PLAYERS_PATH.write_text(json.dumps(players, indent=2), encoding="utf-8")


def create_player_record(
    name,
    completed_lessons=None,
    lives=STARTING_LIVES,
    shield_charges=0,
    lifetime_score=0,
    achievements=None,
    credits=0,
    pod=None,
):
    if not isinstance(lifetime_score, int):
        lifetime_score = 0
    if not isinstance(credits, int):
        credits = 0
    if not isinstance(achievements, list):
        achievements = []

    pod = pod if isinstance(pod, dict) else {}
    pod_color = pod.get("color", DEFAULT_POD["color"])
    pod_type = pod.get("type", DEFAULT_POD["type"])
    pod_upgrades = normalize_pod_upgrades(pod.get("upgrades", []))
    if not isinstance(pod_color, str) or not pod_color.strip():
        pod_color = DEFAULT_POD["color"]
    if not isinstance(pod_type, str) or not pod_type.strip():
        pod_type = DEFAULT_POD["type"]
    shield_cap = PLAYER_SHIELD_MAX_CHARGES
    upgrade_id_set = {
        upgrade.get("id")
        for upgrade in pod_upgrades
        if isinstance(upgrade, dict) and isinstance(upgrade.get("id"), str)
    }
    if "extra_shield_slot_1" in upgrade_id_set:
        shield_cap += 1
    if "extra_shield_slot_2" in upgrade_id_set:
        shield_cap += 1

    return {
        "name": name,
        "completed_lessons": completed_lessons or [],
        "lives": max(1, lives),
        "shield_charges": max(0, min(shield_cap, shield_charges)),
        "lifetime_score": max(0, lifetime_score),
        "achievements": achievements,
        "credits": max(0, credits),
        "pod": {
            "color": pod_color,
            "type": pod_type,
            "upgrades": pod_upgrades,
        },
    }


def clean_player_name(name):
    return re.sub(r"\s+", " ", name).strip()[:24]


def completed_prefix_count(player):
    completed = set(player.get("completed_lessons", []))
    count = 0
    for lesson_number in range(1, len(LESSONS) + 1):
        if lesson_number not in completed:
            break
        count += 1
    return count


def unlocked_lesson_count(player):
    return min(len(LESSONS), completed_prefix_count(player) + 1)


def player_rank(player):
    unlocked = unlocked_lesson_count(player)
    if unlocked <= 4:
        return "Rookie"
    if unlocked <= 10:
        return "Private"
    if unlocked <= 24:
        return "Lieutenant"
    if unlocked <= 30:
        return "Captain"
    return "Major"


def achievement_count(player):
    achievements = player.get("achievements", [])
    return len(achievements) if isinstance(achievements, list) else 0


def player_credits(player):
    credits = player.get("credits", 0)
    return max(0, credits) if isinstance(credits, int) else 0


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
        if player.get("shield_charges", 0) >= player_shield_max_charges(player):
            return "Shield full"
    return None


def upgrade_is_progress_locked(player, upgrade):
    reason = upgrade_lock_reason(player, upgrade)
    return reason is not None and reason != "Need credits"


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
    for name, value in UPGRADE_COLORS:
        if name == color_name:
            return value
    return None


def disabled_icon_name(icon_name):
    if not isinstance(icon_name, str) or not icon_name.endswith(".png"):
        return icon_name
    return f"{icon_name[:-4]}_disabled.png"


def add_pod_upgrade(player, upgrade, color_name=None):
    pod = player.setdefault("pod", DEFAULT_POD.copy())
    if not isinstance(pod, dict):
        pod = DEFAULT_POD.copy()
        player["pod"] = pod
    upgrades = normalize_pod_upgrades(pod.get("upgrades", []))
    entry = {"id": upgrade["id"]}
    if color_name is not None:
        entry["color"] = color_name
    upgrades.append(entry)
    pod["upgrades"] = upgrades


def remove_pod_upgrade_entries(player, upgrade_id, count):
    pod = player.get("pod", {}) if isinstance(player, dict) else {}
    if not isinstance(pod, dict):
        return
    upgrades = normalize_pod_upgrades(pod.get("upgrades", []))
    remaining = []
    removed = 0
    for entry in reversed(upgrades):
        if removed < count and entry.get("id") == upgrade_id:
            removed += 1
            continue
        remaining.append(entry)
    pod["upgrades"] = list(reversed(remaining))


def apply_upgrade_purchase(player, upgrade, color_name=None):
    player["credits"] = max(0, player_credits(player) - upgrade["cost"])
    if upgrade["id"] == "extra_life":
        add_pod_upgrade(player, upgrade)
        player["lives"] = max(1, player.get("lives", STARTING_LIVES) + 1)
    elif upgrade["id"] == "shield_charge":
        add_pod_upgrade(player, upgrade)
        player["shield_charges"] = min(player_shield_max_charges(player), player.get("shield_charges", 0) + 1)
    elif upgrade["id"] == "shield_charge_3":
        add_pod_upgrade(player, upgrade)
        player["shield_charges"] = min(player_shield_max_charges(player), player.get("shield_charges", 0) + 3)
    else:
        add_pod_upgrade(player, upgrade, color_name)
        if upgrade["id"].startswith("extra_shield_slot"):
            player["shield_charges"] = min(player_shield_max_charges(player), player.get("shield_charges", 0))


def max_sell_quantity(player, upgrade):
    if upgrade["id"] == "extra_life":
        lives = player.get("lives", STARTING_LIVES)
        if not isinstance(lives, int):
            lives = STARTING_LIVES
        return max(0, lives - STARTING_LIVES)
    if upgrade["id"] == "shield_charge":
        charges = player.get("shield_charges", 0)
        return max(0, charges) if isinstance(charges, int) else 0
    return 0


def upgrade_can_sell(player, upgrade):
    return upgrade["id"] in ("extra_life", "shield_charge") and max_sell_quantity(player, upgrade) > 0


def upgrade_sell_value(upgrade):
    return max(0, upgrade["cost"] // 2)


def apply_upgrade_sale(player, upgrade, quantity):
    quantity = max(0, int(quantity))
    if quantity <= 0:
        return
    if upgrade["id"] == "extra_life":
        quantity = min(quantity, max_sell_quantity(player, upgrade))
        player["lives"] = max(STARTING_LIVES, player.get("lives", STARTING_LIVES) - quantity)
        remove_pod_upgrade_entries(player, upgrade["id"], quantity)
    elif upgrade["id"] == "shield_charge":
        quantity = min(quantity, max_sell_quantity(player, upgrade))
        player["shield_charges"] = max(0, player.get("shield_charges", 0) - quantity)
        remove_pod_upgrade_entries(player, upgrade["id"], quantity)
    else:
        return
    player["credits"] = player_credits(player) + upgrade_sell_value(upgrade) * quantity


def mark_lesson_complete(player, lesson_number):
    completed = set(player.get("completed_lessons", []))
    completed.add(lesson_number)
    player["completed_lessons"] = sorted(completed)


def load_lesson_module(module_name):
    return importlib.import_module(module_name)


def toggle_fullscreen():
    global is_fullscreen
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return pygame.display.set_mode(SCREEN_SIZE, WINDOW_FLAGS)


def enforce_min_window_size(screen):
    if screen.get_flags() & pygame.FULLSCREEN:
        return screen
    width, height = screen.get_size()
    min_width, min_height = MIN_SCREEN_SIZE
    if width >= min_width and height >= min_height:
        return screen
    return pygame.display.set_mode((max(width, min_width), max(height, min_height)), WINDOW_FLAGS)


def run_lesson(screen, clock, lesson, player):
    intro = load_lesson_module(lesson["intro_module"])
    mission = load_lesson_module(lesson["mission_module"])

    intro_result = intro.run(screen, clock, BASE_DIR)
    if intro_result != "start":
        return intro_result

    while True:
        result = mission.run(screen, clock, BASE_DIR, player)
        if result != "restart":
            return result


def create_player_screen(screen, clock, players):
    title_font = pygame.font.SysFont("arial", 46, bold=True)
    body_font = pygame.font.SysFont("arial", 24)
    small_font = pygame.font.SysFont("arial", 18)
    name = ""
    message = ""
    stars = create_star_field()

    while True:
        update_star_field(stars, clock.get_time() / 1000)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_RETURN:
                    cleaned = clean_player_name(name)
                    if not cleaned:
                        message = "Enter a name first."
                    elif any(player["name"].lower() == cleaned.lower() for player in players):
                        message = "That player already exists."
                    else:
                        player = create_player_record(cleaned)
                        players.append(player)
                        save_players(players)
                        return player
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.unicode and event.unicode.isprintable() and len(name) < 24:
                    name += event.unicode

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        content_width = min(720, max(520, width - 160))
        left = (width - content_width) / 2
        screen.fill(BG_COLOR)
        draw_star_field(screen, stars)

        title = title_font.render("CREATE PLAYER", True, TEXT_COLOR)
        screen.blit(title, title.get_rect(center=(width / 2, height / 2 - 150)))

        draw_text(screen, "Type a pilot name, then press Enter.", body_font, MUTED_TEXT, (left, height / 2 - 82))
        input_rect = pygame.Rect(left, height / 2 - 30, content_width, 62)
        pygame.draw.rect(screen, (13, 22, 42), input_rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT, input_rect, 2, border_radius=8)
        draw_text(screen, name or "Player name", body_font, TEXT_COLOR if name else MUTED_TEXT, (input_rect.x + 18, input_rect.y + 17))
        if message:
            draw_text(screen, message, small_font, (245, 203, 92), (left, height / 2 + 52))
        draw_text(screen, "Esc: Back  |  F11: Max size", small_font, MUTED_TEXT, (left, height - 58))
        pygame.display.flip()
        clock.tick(60)


def player_select_loop(screen, clock):
    title_font = pygame.font.SysFont("arial", 54, bold=True)
    item_font = pygame.font.SysFont("arial", 30, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 18)
    players = load_players()
    selected = 0
    delete_confirm = False
    stars = create_star_field()
    player_rects = []
    mock_battle = create_mock_battle()
    last_wheel_scroll_time = 0

    while True:
        update_star_field(stars, clock.get_time() / 1000)
        if selected >= len(players):
            selected = max(0, len(players) - 1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                elif event.key == pygame.K_q:
                    return "quit"
                elif delete_confirm and event.key == pygame.K_y and players:
                    players.pop(selected)
                    save_players(players)
                    selected = max(0, selected - 1)
                    delete_confirm = False
                elif delete_confirm and event.key in (pygame.K_n, pygame.K_ESCAPE):
                    delete_confirm = False
                elif event.key in (pygame.K_n, pygame.K_INSERT):
                    delete_confirm = False
                    new_player = create_player_screen(screen, clock, players)
                    if new_player == "quit":
                        return "quit"
                    if new_player is not None:
                        selected = players.index(new_player)
                elif players and event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    delete_confirm = True
                elif event.key in (pygame.K_DOWN, pygame.K_s) and players:
                    selected = (selected + 1) % len(players)
                    delete_confirm = False
                elif event.key in (pygame.K_UP, pygame.K_w) and players:
                    selected = (selected - 1) % len(players)
                    delete_confirm = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and players:
                    return players, players[selected]
            if event.type == pygame.MOUSEBUTTONDOWN and players:
                if event.button == 1:
                    for index, rect in player_rects:
                        if rect.collidepoint(event.pos):
                            return players, players[index]
            if event.type == pygame.MOUSEWHEEL and players:
                step, last_wheel_scroll_time = should_apply_menu_wheel(event, last_wheel_scroll_time)
                if step:
                    selected = (selected + step) % len(players)
                    delete_confirm = False

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        content_width = min(820, max(620, width - 120))
        content_left = (width - content_width) / 2
        text_left = content_left + 20
        screen.fill(BG_COLOR)
        draw_star_field(screen, stars)
        update_and_draw_mock_battle(screen, mock_battle, clock, content_left, content_left + content_width)

        draw_text(screen, "SELECT PILOT", title_font, TEXT_COLOR, (text_left, 86))
        draw_text(
            screen,
            "Choose a player profile before selecting a training mission.",
            body_font,
            MUTED_TEXT,
            (text_left + 4, 154),
        )

        list_top = 245
        item_gap = 104
        if not players:
            draw_text(screen, "No players yet. Press N to create your first pilot.", item_font, TEXT_COLOR, (text_left, list_top))
        else:
            visible_rows = max(1, (height - list_top - 112) // item_gap)
            first_visible = max(0, min(selected - visible_rows + 1, len(players) - visible_rows))
            list_height = visible_rows * item_gap - 22
            list_width = content_width - 24 if len(players) > visible_rows else content_width
            player_rects = []
            for index, player in enumerate(players):
                if not first_visible <= index < first_visible + visible_rows:
                    continue
                x, y = text_left, list_top + (index - first_visible) * item_gap
                is_selected = index == selected
                card_color = (20, 32, 58) if is_selected else (13, 22, 42)
                border_color = ACCENT if is_selected else (43, 57, 89)
                unlocked = unlocked_lesson_count(player)
                rank = player_rank(player)
                card_rect = pygame.Rect(content_left, y - 20, list_width, 82)
                player_rects.append((index, card_rect))
                pygame.draw.rect(screen, card_color, card_rect, border_radius=8)
                pygame.draw.rect(screen, border_color, card_rect, 2, border_radius=8)
                draw_text(screen, player["name"], item_font, TEXT_COLOR, (x, y - 4))
                summary = (
                    f"Unlocked missions: {unlocked}/{len(LESSONS)}    "
                    f"Rank: {rank}    "
                    f"Achievements: {achievement_count(player)}    "
                    f"Credits: {player_credits(player)}"
                )
                draw_text(screen, summary, body_font, MUTED_TEXT, (x, y + 34))
            scrollbar_rect = pygame.Rect(content_left + content_width - 12, list_top - 20, 8, list_height)
            draw_scrollbar(screen, scrollbar_rect, len(players), visible_rows, first_visible)

        if delete_confirm and players:
            message = f"Delete {players[selected]['name']}? Press Y to confirm or N to cancel."
            draw_text(screen, message, small_font, (245, 203, 92), (text_left + 4, height - 88))
        draw_text(screen, "Enter/␣: Select  |  N: New  |  Delete: Delete  |  Q: Quit  |  F11: Max size", small_font, MUTED_TEXT, (text_left + 4, height - 58))
        pygame.display.flip()
        clock.tick(60)


def draw_modal_backdrop(screen):
    width, height = screen.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((2, 5, 13, 210))
    screen.blit(overlay, (0, 0))


def draw_modal_button(screen, rect, text, font, enabled=True, selected=False):
    if enabled:
        fill = (20, 32, 58) if not selected else (24, 50, 70)
        border = ACCENT if selected else (65, 82, 120)
        color = TEXT_COLOR
    else:
        fill = (12, 17, 28)
        border = (35, 42, 62)
        color = MUTED_TEXT
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)
    label = font.render(text, True, color)
    screen.blit(label, label.get_rect(center=rect.center))


def draw_buy_button(screen, rect, font, hovered=False):
    fill = (118, 88, 24) if hovered else (20, 32, 58)
    border = LOCKED_SELECTED if hovered else ACCENT
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)
    label = font.render("BUY", True, TEXT_COLOR)
    screen.blit(label, label.get_rect(center=rect.center))


def draw_sell_button(screen, rect, font, hovered=False, enabled=True):
    if enabled:
        fill = (78, 42, 50) if hovered else (42, 26, 36)
        border = (219, 92, 101) if hovered else (142, 82, 96)
        color = TEXT_COLOR
    else:
        fill = (12, 17, 28)
        border = (35, 42, 62)
        color = MUTED_TEXT
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)
    label = font.render("SELL", True, color)
    screen.blit(label, label.get_rect(center=rect.center))


def wrap_plain_text(text, font, max_width):
    lines = []
    for paragraph in str(text).splitlines():
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if font.size(candidate)[0] <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def draw_centered_wrapped_text(surface, text, font, color, rect, line_spacing=6):
    line_height = font.get_linesize() + line_spacing
    lines = wrap_plain_text(text, font, rect.width)
    total_height = len(lines) * line_height - line_spacing if lines else 0
    y = rect.y + max(0, (rect.height - total_height) / 2)
    for line in lines:
        rendered = font.render(line, True, color)
        surface.blit(rendered, rendered.get_rect(center=(rect.centerx, y + font.get_height() / 2)))
        y += line_height


def load_ui_image(path):
    cache_key = str(path)
    if cache_key in ui_image_cache:
        return ui_image_cache[cache_key]
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        image = None
    ui_image_cache[cache_key] = image
    return image


def load_ui_sound(path, volume=1.0):
    if not pygame.mixer.get_init():
        return None
    cache_key = str(path)
    if cache_key in ui_sound_cache:
        return ui_sound_cache[cache_key]
    try:
        sound = pygame.mixer.Sound(str(path))
        sound.set_volume(volume)
    except (OSError, pygame.error):
        sound = None
    ui_sound_cache[cache_key] = sound
    return sound


def play_ui_sound(sound):
    if sound is not None:
        sound.play()


def load_json_dict(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_reward_image_path(lesson_dir, image_name):
    if not image_name:
        return None
    raw_name = str(image_name).strip()
    if not raw_name:
        return None
    raw_path = Path(raw_name)
    if raw_path.is_absolute() and raw_path.exists():
        return raw_path
    names = [raw_path]
    if raw_path.suffix == "":
        names.append(Path(f"{raw_name}.png"))
    for name in names:
        for base in (lesson_dir, BASE_DIR, BASE_DIR / "gfx"):
            candidate = base / name
            if candidate.exists():
                return candidate
    return None


def collect_new_achievement_modals(player, lesson_number):
    return []


def collect_lesson_unlock_modals(lesson_number):
    lesson_dir = BASE_DIR / "lessons" / f"lesson_{lesson_number}"
    unlocks = load_json_dict(lesson_dir / f"unlocks_l{lesson_number}.json")
    queued = []
    for unlock_key in sorted(unlocks):
        unlock = unlocks.get(unlock_key)
        if not isinstance(unlock, dict):
            continue
        title = str(unlock.get(f"{unlock_key}_title", unlock.get("title", ""))).strip()
        text = str(unlock.get(f"{unlock_key}_text", unlock.get("text", ""))).strip()
        image_name = unlock.get(f"{unlock_key}_img", unlock.get("img", ""))
        if title or text:
            queued.append(
                {
                    "kind": "unlock",
                    "title": title or "Unlocked",
                    "text": text,
                    "image_path": resolve_reward_image_path(lesson_dir, image_name),
                }
            )
    return queued


def collect_mission_reward_modals(player, lesson_number, include_unlocks=True):
    queue = []
    queue.extend(collect_new_achievement_modals(player, lesson_number))
    if include_unlocks:
        queue.extend(collect_lesson_unlock_modals(lesson_number))
    return queue


def reward_modal_loop(screen, clock, reward, background):
    title_font = pygame.font.SysFont("arial", 40, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    button_font = pygame.font.SysFont("arial", 24, bold=True)
    ok_rect = pygame.Rect(0, 0, 0, 0)
    image = load_ui_image(reward.get("image_path")) if reward.get("image_path") else None
    if reward.get("kind") == "unlock":
        play_ui_sound(load_ui_sound(BASE_DIR / "sfx" / "unlock.wav", 0.9))
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ok_rect.collidepoint(event.pos):
                    return None

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        if background.get_size() == screen.get_size():
            screen.blit(background, (0, 0))
        else:
            screen.fill(BG_COLOR)
        draw_modal_backdrop(screen)
        modal_rect = pygame.Rect(0, 0, min(620, width - 80), min(560, height - 40))
        modal_rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), modal_rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT, modal_rect, 2, border_radius=8)

        title_surface = title_font.render(str(reward.get("title", "Unlocked")), True, TEXT_COLOR)
        screen.blit(title_surface, title_surface.get_rect(center=(modal_rect.centerx, modal_rect.y + 58)))

        image_size = min(200, max(96, modal_rect.height - 330), modal_rect.width - 120)
        image_rect = pygame.Rect(0, 0, image_size, image_size)
        image_rect.center = (modal_rect.centerx, modal_rect.y + 190)
        if image is not None:
            scaled = pygame.transform.smoothscale(image, (image_rect.width, image_rect.height))
            screen.blit(scaled, image_rect)
        else:
            pygame.draw.rect(screen, (20, 32, 58), image_rect, border_radius=8)
            pygame.draw.rect(screen, (65, 82, 120), image_rect, 2, border_radius=8)

        text_rect = pygame.Rect(modal_rect.x + 52, image_rect.bottom + 18, modal_rect.width - 104, 112)
        draw_centered_wrapped_text(screen, reward.get("text", ""), body_font, MUTED_TEXT, text_rect)

        ok_rect = pygame.Rect(0, modal_rect.bottom - 74, 150, 44)
        ok_rect.centerx = modal_rect.centerx
        draw_modal_button(screen, ok_rect, "Okay", button_font, True, True)
        pygame.display.flip()
        clock.tick(60)


def show_reward_modal_queue(screen, clock, queue):
    while queue:
        background = screen.copy()
        result = reward_modal_loop(screen, clock, queue.pop(0), background)
        if result == "quit":
            return "quit"
    return None


def draw_square_image_button(screen, rect, image=None):
    pygame.draw.rect(screen, (20, 32, 58), rect, border_radius=8)
    if image is not None:
        scaled = pygame.transform.smoothscale(image, (rect.width, rect.height))
        screen.blit(scaled, rect)
    pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=8)


def draw_upgrades_modal(screen, title_font, body_font, small_font, player):
    width, height = screen.get_size()
    draw_modal_backdrop(screen)
    margin_x = 14 if width >= 640 else 6
    margin_y = 8 if height >= 520 else 4
    modal_width = max(1, min(1120, width - margin_x * 2))
    modal_height = max(1, min(900, height - margin_y * 2))
    modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
    modal_rect.center = (width / 2, height / 2)
    title_font = pygame.font.SysFont("arial", max(24, min(42, modal_height // 15)), bold=True)
    body_font = pygame.font.SysFont("arial", max(14, min(22, modal_height // 28)))
    small_font = pygame.font.SysFont("arial", max(11, min(20, modal_height // 34)))
    pygame.draw.rect(screen, (10, 18, 34), modal_rect, border_radius=8)
    pygame.draw.rect(screen, ACCENT, modal_rect, 2, border_radius=8)
    header_pad = max(10, min(28, modal_height // 28))
    draw_text(screen, "UPGRADES", title_font, TEXT_COLOR, (modal_rect.x + header_pad, modal_rect.y + header_pad))
    draw_text(
        screen,
        f"Credits: {player_credits(player)}    Rank: {player_rank(player)}    Lives: {player.get('lives', STARTING_LIVES)}    Shields: {player.get('shield_charges', 0)}/{player_shield_max_charges(player)}",
        body_font,
        MUTED_TEXT,
        (modal_rect.x + header_pad + 4, modal_rect.y + header_pad + title_font.get_height() + 16),
    )

    action_rects = []
    mouse_pos = pygame.mouse.get_pos()
    if modal_width >= 560:
        cols = 3
    elif modal_width >= 390:
        cols = 2
    else:
        cols = 1
    gap = max(6, min(16, modal_width // 70))
    side_pad = max(8, min(32, modal_width // 35))
    box_width = max(1, (modal_width - side_pad * 2 - gap * (cols - 1)) // cols)
    start_x = modal_rect.x + side_pad
    start_y = modal_rect.y + max(90, min(130, modal_height // 5))
    footer_height = max(52, min(78, modal_height // 9))
    footer_top = modal_rect.bottom - footer_height
    rows = math.ceil(len(UPGRADE_CATALOG) / cols)
    available_grid_height = max(1, footer_top - start_y - gap * (rows - 1))
    box_height = max(1, available_grid_height // rows)
    for index, upgrade in enumerate(UPGRADE_CATALOG):
        col = index % cols
        row = index // cols
        rect = pygame.Rect(
            start_x + col * (box_width + gap),
            start_y + row * (box_height + gap),
            box_width,
            box_height,
        )
        locked_reason = upgrade_lock_reason(player, upgrade)
        fill = (20, 32, 58) if locked_reason is None else (12, 17, 28)
        border = (65, 82, 120) if locked_reason is None else (35, 42, 62)
        title_color = TEXT_COLOR if locked_reason is None else MUTED_TEXT
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)
        previous_clip = screen.get_clip()
        clip_rect = rect.inflate(-4, -4)
        if clip_rect.width <= 0 or clip_rect.height <= 0:
            clip_rect = rect
        screen.set_clip(clip_rect)
        action_height = max(22, min(44, box_height // 4))
        action_rect = pygame.Rect(rect.x + 2, rect.bottom - action_height - 2, rect.width - 4, action_height)
        content_gap = max(4, min(16, box_height // 12))
        content_rect = pygame.Rect(rect.x, rect.y, rect.width, max(1, action_rect.y - rect.y - content_gap))
        icon_size = max(1, min(content_rect.height, max(34, int(box_width * 0.38))))
        art_rect = pygame.Rect(content_rect.x, content_rect.y, icon_size, icon_size)
        pygame.draw.rect(screen, (26, 36, 58), art_rect, border_radius=8)
        icon_name = upgrade.get("icon", "")
        if upgrade_is_progress_locked(player, upgrade):
            icon_name = disabled_icon_name(icon_name)
        icon = load_ui_image(BASE_DIR / "gfx" / "upgrades" / icon_name)
        if icon is not None:
            scaled_icon = pygame.transform.smoothscale(icon, (art_rect.width, art_rect.height))
            screen.blit(scaled_icon, art_rect)
        pygame.draw.rect(screen, (71, 88, 124), art_rect, 1, border_radius=8)
        detail_x = art_rect.right + max(6, min(12, box_width // 28))
        line_gap = max(14, small_font.get_height() + 3)
        detail_y = content_rect.y + max(4, min(14, content_rect.height // 12))
        draw_text(screen, upgrade["name"], small_font, title_color, (detail_x, detail_y))
        draw_text(screen, f"{upgrade['cost']} credits", small_font, MUTED_TEXT, (detail_x, detail_y + line_gap))
        if upgrade.get("color_choice"):
            current_color = color_value(upgrade_color(player, upgrade["id"]))
            if current_color is not None:
                swatch_size = max(10, min(18, small_font.get_height()))
                swatch_rect = pygame.Rect(rect.right - swatch_size - 14, detail_y + line_gap + 1, swatch_size, swatch_size)
                pygame.draw.rect(screen, current_color, swatch_rect, border_radius=3)
                pygame.draw.rect(screen, (225, 235, 255), swatch_rect, 2, border_radius=3)
        status = locked_reason or "Available"
        draw_text(screen, status, small_font, ACCENT if locked_reason is None else LOCKED_SELECTED, (detail_x, detail_y + line_gap * 2))
        draw_text(screen, upgrade["requirement"], small_font, MUTED_TEXT, (detail_x, detail_y + line_gap * 3))
        if upgrade_shows_purchased(player, upgrade):
            purchased_surface = small_font.render("PURCHASED", True, ACCENT)
            screen.blit(purchased_surface, purchased_surface.get_rect(center=action_rect.center))
        elif upgrade["id"] in ("extra_life", "shield_charge"):
            button_gap = max(4, min(8, action_rect.width // 24))
            button_width = max(1, (action_rect.width - button_gap) // 2)
            sell_rect = pygame.Rect(action_rect.x, action_rect.y, button_width, action_rect.height)
            buy_rect = pygame.Rect(action_rect.right - button_width, action_rect.y, button_width, action_rect.height)
            sell_enabled = upgrade_can_sell(player, upgrade)
            draw_sell_button(screen, sell_rect, small_font, sell_rect.collidepoint(mouse_pos), sell_enabled)
            draw_buy_button(screen, buy_rect, small_font, buy_rect.collidepoint(mouse_pos))
            if sell_enabled:
                action_rects.append(("sell", index, sell_rect))
            action_rects.append(("buy", index, buy_rect))
        else:
            draw_buy_button(screen, action_rect, small_font, action_rect.collidepoint(mouse_pos))
            action_rects.append(("buy", index, action_rect))
        screen.set_clip(previous_clip)

    footer_rect = pygame.Rect(modal_rect.x + 2, footer_top, modal_rect.width - 4, footer_height - 2)
    pygame.draw.rect(screen, (10, 18, 34), footer_rect)
    pygame.draw.line(screen, (43, 57, 89), (footer_rect.x, footer_rect.y), (footer_rect.right, footer_rect.y), 1)
    close_rect = pygame.Rect(modal_rect.right - 150, footer_top + 20, 118, 38)
    draw_modal_button(screen, close_rect, "Close", small_font, True, False)
    draw_text(screen, "Press BUY to purchase or SELL to refund. Esc closes.", small_font, MUTED_TEXT, (modal_rect.x + 32, footer_top + 30))
    return action_rects, close_rect


def confirm_purchase_modal(screen, clock, upgrade, player):
    title_font = pygame.font.SysFont("arial", 38, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 18)
    confirm_rect = pygame.Rect(0, 0, 0, 0)
    cancel_rect = pygame.Rect(0, 0, 0, 0)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_y):
                    return True
                if event.key in (pygame.K_n, pygame.K_BACKSPACE):
                    return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if confirm_rect.collidepoint(mouse_pos):
                    return True
                if cancel_rect.collidepoint(mouse_pos):
                    return False

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        draw_modal_backdrop(screen)
        rect = pygame.Rect(0, 0, min(560, width - 80), 250)
        rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=8)
        draw_text(screen, "CONFIRM PURCHASE", title_font, TEXT_COLOR, (rect.x + 28, rect.y + 24))
        draw_text(screen, upgrade["name"], body_font, TEXT_COLOR, (rect.x + 32, rect.y + 88))
        draw_text(screen, f"Cost: {upgrade['cost']} credits    Available: {player_credits(player)}", body_font, MUTED_TEXT, (rect.x + 32, rect.y + 122))
        confirm_rect = pygame.Rect(rect.x + 32, rect.bottom - 62, 170, 42)
        cancel_rect = pygame.Rect(rect.right - 202, rect.bottom - 62, 170, 42)
        draw_modal_button(screen, confirm_rect, "Purchase", body_font, True, True)
        draw_modal_button(screen, cancel_rect, "Cancel", body_font, True, False)
        pygame.display.flip()
        clock.tick(60)


def insufficient_funds_modal(screen, clock, upgrade, player):
    title_font = pygame.font.SysFont("arial", 38, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    ok_rect = pygame.Rect(0, 0, 0, 0)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ok_rect.collidepoint(event.pos):
                    return None

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        draw_modal_backdrop(screen)
        rect = pygame.Rect(0, 0, min(600, width - 80), 260)
        rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), rect, border_radius=8)
        pygame.draw.rect(screen, LOCKED_SELECTED, rect, 2, border_radius=8)
        draw_text(screen, "NOT ENOUGH FUNDS", title_font, LOCKED_SELECTED, (rect.x + 28, rect.y + 24))
        draw_text(screen, f"{upgrade['name']} costs {upgrade['cost']} credits.", body_font, TEXT_COLOR, (rect.x + 32, rect.y + 92))
        draw_text(screen, f"You have {player_credits(player)} credits.", body_font, MUTED_TEXT, (rect.x + 32, rect.y + 126))
        draw_text(screen, "Destroy more drones to earn more credits.", body_font, MUTED_TEXT, (rect.x + 32, rect.y + 160))
        ok_rect = pygame.Rect(rect.right - 174, rect.bottom - 62, 142, 42)
        draw_modal_button(screen, ok_rect, "OK", body_font, True, True)
        pygame.display.flip()
        clock.tick(60)


def upgrade_locked_modal(screen, clock, upgrade, reason):
    title_font = pygame.font.SysFont("arial", 38, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    ok_rect = pygame.Rect(0, 0, 0, 0)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ok_rect.collidepoint(event.pos):
                    return None

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        draw_modal_backdrop(screen)
        rect = pygame.Rect(0, 0, min(600, width - 80), 260)
        rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), rect, border_radius=8)
        pygame.draw.rect(screen, LOCKED_SELECTED, rect, 2, border_radius=8)
        draw_text(screen, "UPGRADE LOCKED", title_font, LOCKED_SELECTED, (rect.x + 28, rect.y + 24))
        draw_text(screen, upgrade["name"], body_font, TEXT_COLOR, (rect.x + 32, rect.y + 92))
        draw_text(screen, reason, body_font, MUTED_TEXT, (rect.x + 32, rect.y + 128))
        draw_text(screen, "Keep progressing to unlock this upgrade.", body_font, MUTED_TEXT, (rect.x + 32, rect.y + 162))
        ok_rect = pygame.Rect(rect.right - 174, rect.bottom - 62, 142, 42)
        draw_modal_button(screen, ok_rect, "OK", body_font, True, True)
        pygame.display.flip()
        clock.tick(60)


def sell_upgrade_modal(screen, clock, upgrade, player):
    max_quantity = max_sell_quantity(player, upgrade)
    if max_quantity <= 0:
        return None
    title_font = pygame.font.SysFont("arial", 38, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    large_font = pygame.font.SysFont("arial", 42, bold=True)
    quantity = 1
    up_rect = pygame.Rect(0, 0, 0, 0)
    down_rect = pygame.Rect(0, 0, 0, 0)
    sell_rect = pygame.Rect(0, 0, 0, 0)
    cancel_rect = pygame.Rect(0, 0, 0, 0)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_UP, pygame.K_w):
                    quantity = min(max_quantity, quantity + 1)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    quantity = max(1, quantity - 1)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return quantity
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if up_rect.collidepoint(event.pos):
                    quantity = min(max_quantity, quantity + 1)
                elif down_rect.collidepoint(event.pos):
                    quantity = max(1, quantity - 1)
                elif sell_rect.collidepoint(event.pos):
                    return quantity
                elif cancel_rect.collidepoint(event.pos):
                    return None

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        draw_modal_backdrop(screen)
        rect = pygame.Rect(0, 0, min(560, width - 80), 360)
        rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), rect, border_radius=8)
        pygame.draw.rect(screen, (219, 92, 101), rect, 2, border_radius=8)
        draw_text(screen, "SELL UPGRADE", title_font, TEXT_COLOR, (rect.x + 28, rect.y + 24))
        draw_text(screen, upgrade["name"], body_font, MUTED_TEXT, (rect.x + 32, rect.y + 82))
        draw_text(
            screen,
            f"Refund: {upgrade_sell_value(upgrade)} credits each    Available to sell: {max_quantity}",
            body_font,
            MUTED_TEXT,
            (rect.x + 32, rect.y + 116),
        )

        picker_center_x = rect.centerx
        up_rect = pygame.Rect(0, rect.y + 154, 74, 42)
        up_rect.centerx = picker_center_x
        value_rect = pygame.Rect(0, up_rect.bottom + 8, 130, 58)
        value_rect.centerx = picker_center_x
        down_rect = pygame.Rect(0, value_rect.bottom + 8, 74, 42)
        down_rect.centerx = picker_center_x
        draw_modal_button(screen, up_rect, "▲", large_font, quantity < max_quantity, False)
        pygame.draw.rect(screen, (20, 32, 58), value_rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT, value_rect, 2, border_radius=8)
        value_surface = large_font.render(str(quantity), True, TEXT_COLOR)
        screen.blit(value_surface, value_surface.get_rect(center=value_rect.center))
        draw_modal_button(screen, down_rect, "▼", large_font, quantity > 1, False)

        sell_rect = pygame.Rect(rect.x + 32, rect.bottom - 62, 170, 42)
        cancel_rect = pygame.Rect(rect.right - 202, rect.bottom - 62, 170, 42)
        draw_modal_button(screen, sell_rect, "Sell", body_font, True, True)
        draw_modal_button(screen, cancel_rect, "Cancel", body_font, True, False)
        pygame.display.flip()
        clock.tick(60)


def color_choice_modal(screen, clock, upgrade):
    title_font = pygame.font.SysFont("arial", 38, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 18)
    selected = 0
    color_rects = []
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % len(UPGRADE_COLORS)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % len(UPGRADE_COLORS)
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 4) % len(UPGRADE_COLORS)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 4) % len(UPGRADE_COLORS)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return UPGRADE_COLORS[selected][0]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(color_rects):
                    if rect.collidepoint(event.pos):
                        return UPGRADE_COLORS[index][0]

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        draw_modal_backdrop(screen)
        rect = pygame.Rect(0, 0, min(620, width - 80), 390)
        rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=8)
        draw_text(screen, "CHOOSE COLOR", title_font, TEXT_COLOR, (rect.x + 28, rect.y + 24))
        draw_text(screen, upgrade["name"], body_font, MUTED_TEXT, (rect.x + 32, rect.y + 82))
        color_rects = []
        swatch_size = 58
        gap = 22
        start_x = rect.x + 52
        start_y = rect.y + 130
        for index, (name, color) in enumerate(UPGRADE_COLORS):
            col = index % 4
            row = index // 4
            swatch_rect = pygame.Rect(start_x + col * (swatch_size + gap), start_y + row * 82, swatch_size, swatch_size)
            color_rects.append(swatch_rect)
            pygame.draw.rect(screen, color, swatch_rect, border_radius=6)
            pygame.draw.rect(screen, ACCENT if index == selected else (65, 82, 120), swatch_rect, 3, border_radius=6)
            draw_text(screen, name, small_font, TEXT_COLOR, (swatch_rect.x, swatch_rect.bottom + 6))
        draw_text(screen, "Esc cancels.", small_font, MUTED_TEXT, (rect.x + 32, rect.bottom - 40))
        pygame.display.flip()
        clock.tick(60)


def upgrades_modal_loop(screen, clock, players, player):
    title_font = pygame.font.SysFont("arial", 42, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 20)
    action_rects = []
    close_rect = pygame.Rect(0, 0, 0, 0)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if close_rect.collidepoint(event.pos):
                    return None
                for action, index, rect in action_rects:
                    if rect.collidepoint(event.pos):
                        if action == "sell":
                            result = attempt_upgrade_sale(screen, clock, players, player, UPGRADE_CATALOG[index])
                        else:
                            result = attempt_upgrade_purchase(screen, clock, players, player, UPGRADE_CATALOG[index])
                        if result == "quit":
                            return "quit"
                        break

        screen = pygame.display.get_surface()
        action_rects, close_rect = draw_upgrades_modal(screen, title_font, body_font, small_font, player)
        pygame.display.flip()
        clock.tick(60)


def attempt_upgrade_purchase(screen, clock, players, player, upgrade):
    lock_reason = upgrade_lock_reason(player, upgrade)
    if lock_reason == "Need credits":
        return insufficient_funds_modal(screen, clock, upgrade, player)
    if lock_reason is not None:
        return upgrade_locked_modal(screen, clock, upgrade, lock_reason)
    confirmed = confirm_purchase_modal(screen, clock, upgrade, player)
    if confirmed == "quit":
        return "quit"
    if not confirmed:
        return None
    color_name = None
    if upgrade.get("color_choice"):
        color_name = color_choice_modal(screen, clock, upgrade)
        if color_name == "quit":
            return "quit"
        if color_name is None:
            return None
    apply_upgrade_purchase(player, upgrade, color_name)
    save_players(players)
    return None


def attempt_upgrade_sale(screen, clock, players, player, upgrade):
    if not upgrade_can_sell(player, upgrade):
        return upgrade_locked_modal(screen, clock, upgrade, "Nothing to sell")
    quantity = sell_upgrade_modal(screen, clock, upgrade, player)
    if quantity == "quit":
        return "quit"
    if not quantity:
        return None
    apply_upgrade_sale(player, upgrade, quantity)
    save_players(players)
    return None


def menu_loop(screen, clock, players, player):
    title_font = pygame.font.SysFont("arial", 54, bold=True)
    item_font = pygame.font.SysFont("arial", 30, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 18)

    selected = 0
    stars = create_star_field()
    mission_rects = []
    upgrades_button_rect = None
    upgrades_image = load_ui_image(BASE_DIR / "gfx" / "upgrades" / "upgrades.png")
    mock_battle = create_mock_battle()
    last_wheel_scroll_time = 0
    pending_reward_modals = []

    while True:
        update_star_field(stars, clock.get_time() / 1000)
        unlocked_count = unlocked_lesson_count(player)
        upgrades_available = 2 in set(player.get("completed_lessons", []))
        if not upgrades_available:
            upgrades_button_rect = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                if event.key == pygame.K_q:
                    return "quit"
                if event.key == pygame.K_ESCAPE:
                    return "players"
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(LESSONS)
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(LESSONS)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected < unlocked_count:
                        completed_index = selected
                        lesson_number = LESSONS[completed_index]["number"]
                        was_completed = lesson_number in set(player.get("completed_lessons", []))
                        result = run_lesson(screen, clock, LESSONS[completed_index], player)
                        save_players(players)
                        if result == "quit":
                            return "quit"
                        if result == "won":
                            mark_lesson_complete(player, lesson_number)
                            pending_reward_modals.extend(
                                collect_mission_reward_modals(player, lesson_number, not was_completed)
                            )
                            save_players(players)
                            selected = min(completed_index + 1, unlocked_lesson_count(player) - 1)
                        pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if upgrades_button_rect is not None and upgrades_button_rect.collidepoint(event.pos):
                    result = upgrades_modal_loop(screen, clock, players, player)
                    if result == "quit":
                        return "quit"
                    pygame.event.clear((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
                    continue
                for index, rect in mission_rects:
                    if rect.collidepoint(event.pos):
                        selected = index
                        if index < unlocked_count:
                            lesson_number = LESSONS[index]["number"]
                            was_completed = lesson_number in set(player.get("completed_lessons", []))
                            result = run_lesson(screen, clock, LESSONS[index], player)
                            save_players(players)
                            if result == "quit":
                                return "quit"
                            if result == "won":
                                mark_lesson_complete(player, lesson_number)
                                pending_reward_modals.extend(
                                    collect_mission_reward_modals(player, lesson_number, not was_completed)
                                )
                                save_players(players)
                                selected = min(index + 1, unlocked_lesson_count(player) - 1)
                            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
                        break
            if event.type == pygame.MOUSEWHEEL:
                step, last_wheel_scroll_time = should_apply_menu_wheel(event, last_wheel_scroll_time)
                if step:
                    selected = (selected + step) % len(LESSONS)

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        content_width = min(820, max(620, width - 120))
        content_left = (width - content_width) / 2
        text_left = content_left + 20
        screen.fill(BG_COLOR)
        draw_star_field(screen, stars)
        update_and_draw_mock_battle(screen, mock_battle, clock, content_left, content_left + content_width)
        if upgrades_available:
            upgrades_button_rect = pygame.Rect(content_left + content_width - 80, 128, 80, 80)
            draw_square_image_button(screen, upgrades_button_rect, upgrades_image)
        else:
            upgrades_button_rect = None
        draw_text(screen, "TYPE FIGHTER", title_font, TEXT_COLOR, (text_left, 90))
        draw_text(
            screen,
            f"{player['name']}    Rank: {player_rank(player)}    Unlocked: {unlocked_count}/{len(LESSONS)}    Credits: {player_credits(player)}",
            body_font,
            MUTED_TEXT,
            (text_left + 4, 160),
        )
        draw_text(screen, "Select a training mission. Press ␣ or Enter to launch.", body_font, MUTED_TEXT, (text_left + 4, 190))

        list_top = 265
        item_gap = 110
        visible_rows = max(1, (height - list_top - 92) // item_gap)
        first_visible = max(0, min(selected - visible_rows + 1, len(LESSONS) - visible_rows))
        list_height = visible_rows * item_gap - 24
        list_width = content_width - 24 if len(LESSONS) > visible_rows else content_width
        mission_rects = []
        for index, lesson in enumerate(LESSONS):
            if not first_visible <= index < first_visible + visible_rows:
                continue
            x, y = text_left, list_top + (index - first_visible) * item_gap
            is_selected = index == selected
            is_locked = index >= unlocked_count
            card_color = (20, 32, 58) if is_selected else (13, 22, 42)
            border_color = ACCENT if is_selected else (43, 57, 89)
            border_width = 2
            title_color = TEXT_COLOR
            summary_color = MUTED_TEXT
            if is_locked and is_selected:
                card_color = (38, 31, 27)
                border_color = LOCKED_SELECTED
                border_width = 3
                title_color = LOCKED_SELECTED
                summary_color = (231, 194, 111)
            elif is_locked:
                card_color = (11, 16, 30)
                border_color = (35, 42, 62)
                title_color = MUTED_TEXT
            card_rect = pygame.Rect(content_left, y - 22, list_width, 86)
            mission_rects.append((index, card_rect))
            pygame.draw.rect(screen, card_color, card_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, card_rect, border_width, border_radius=8)
            if is_selected:
                pygame.draw.rect(screen, border_color, (card_rect.x, card_rect.y + 10, 5, card_rect.height - 20), border_radius=3)
            summary = "Locked: complete the previous lesson first." if is_locked else lesson["summary"]
            draw_text(screen, lesson["title"], item_font, title_color, (x, y - 4))
            draw_text(screen, summary, body_font, summary_color, (x, y + 36))

        scrollbar_rect = pygame.Rect(content_left + content_width - 12, list_top - 22, 8, list_height)
        draw_scrollbar(screen, scrollbar_rect, len(LESSONS), visible_rows, first_visible)

        draw_text(screen, "Esc: Players  |  F11: Max size  |  Q: Quit", small_font, MUTED_TEXT, (text_left + 4, height - 58))
        if pending_reward_modals:
            result = show_reward_modal_queue(screen, clock, pending_reward_modals)
            if result == "quit":
                return "quit"
            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
            continue
        pygame.display.flip()
        clock.tick(60)


def set_window_metadata():
    pygame.display.set_caption("Type Fighter")
    for icon_name in ("type-fighter-icon.png", "type-fighter-icon.ico"):
        try:
            pygame.display.set_icon(pygame.image.load(str(BASE_DIR / "gfx" / icon_name)))
            return
        except (OSError, pygame.error):
            pass


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass

    set_window_metadata()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    if hasattr(pygame.display, "set_minimum_size"):
        pygame.display.set_minimum_size(*MIN_SCREEN_SIZE)
    clock = pygame.time.Clock()

    try:
        while True:
            selection = player_select_loop(screen, clock)
            if selection == "quit":
                break
            players, player = selection
            result = menu_loop(screen, clock, players, player)
            if result == "quit":
                break
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
