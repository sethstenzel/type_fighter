import importlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import uuid

import pygame
from loguru import logger

from display_helpers import (
    MIN_SCREEN_SIZE,
    SCREEN_SIZE,
    enforce_16_9_window,
    is_letterboxed_fullscreen,
    set_fullscreen_16_9,
    set_windowed_16_9,
)
from lessons.lesson_config import LESSON_PROGRESS
from lessons.key_render import render_inline_text, render_key_label
from lessons import mission_engine
from lessons.mission_engine import (
    ONE_SHOT_DRONE_COLOR,
    create_star_field,
    draw_star_field,
    update_star_field,
)
import player_limits
import player_storage_sqlite
from game_config import (
    ACHIEVEMENTS,
    GAME_SETTINGS,
    UPGRADE_CATALOG,
    apply_config,
    load_game_data_db,
    save_game_data_db,
)
import cheats
import user_settings
from player_model import (
    DEFAULT_POD,
    UPGRADE_COLORS,
    apply_upgrade_purchase,
    apply_upgrade_sale,
    achievement_count,
    achievement_requirements_met as model_achievement_requirements_met,
    coerce_int,
    color_value,
    disabled_icon_name,
    has_achievement,
    has_upgrade,
    mark_lesson_complete,
    max_sell_quantity,
    mission_stats_are_high_score,
    mission_stats_are_perfect,
    mission_stats_are_quick,
    normalize_achievement_awards,
    normalize_lesson_number_list,
    normalize_mission_settings,
    normalize_pod_upgrades,
    normalize_string_list,
    normalized_achievement_ids,
    player_credits,
    player_lives,
    player_rank,
    player_shield_max_charges,
    record_latest_mission_achievement_progress,
    set_player_shield_base_charges,
    upgrade_can_sell,
    upgrade_color,
    upgrade_ids,
    upgrade_is_progress_locked,
    upgrade_lock_reason,
    upgrade_sell_value,
    upgrade_shows_purchased,
    unlocked_lesson_count as model_unlocked_lesson_count,
)
from versioning import CLIENT_VERSION


BG_COLOR = (8, 12, 24)
TEXT_COLOR = (230, 238, 255)
MUTED_TEXT = (138, 150, 178)
ACCENT = (72, 209, 204)
LOCKED_SELECTED = (245, 203, 92)
MENU_WHEEL_SCROLL_COOLDOWN_MS = 90
NAV_REPEAT_DELAY_MS = 200       # hold-to-repeat: delay before the first auto-repeat
NAV_REPEAT_INTERVAL_MS = 200    # hold-to-repeat: ~5 moves per second while held
STARTING_LIVES = 3
PLAYER_SHIELD_MAX_CHARGES = 3
def running_as_frozen_app():
    return getattr(sys, "frozen", False) or "__compiled__" in globals()


def app_base_dir():
    if running_as_frozen_app():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = app_base_dir()
APP_CONFIG_DIR = player_storage_sqlite.user_data_dir()
APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
PLAYERS_PATH = APP_CONFIG_DIR / "players.json"
GAME_DATA_DB_PATH = APP_CONFIG_DIR / "game_data.db"
is_fullscreen = True
ui_image_cache = {}
ui_sound_cache = {}
menu_music_channel = None
player_storage = {
    "server_url": "",
    "warning": "",
}


def apply_game_settings():
    global STARTING_LIVES, PLAYER_SHIELD_MAX_CHARGES
    STARTING_LIVES = max(1, int(GAME_SETTINGS["starting_lives"]))
    PLAYER_SHIELD_MAX_CHARGES = max(0, int(GAME_SETTINGS["player_shield_max_charges"]))
    set_player_shield_base_charges(PLAYER_SHIELD_MAX_CHARGES)
    player_limits.MAX_PLAYER_LIVES = max(STARTING_LIVES, int(GAME_SETTINGS["max_player_lives"]))
    mission_engine.apply_game_settings(GAME_SETTINGS)


def logging_enabled():
    return "--logging" in sys.argv or "--verbose-logging" in sys.argv or "--debug" in sys.argv


def setup_logging(verbose=False):
    logger.remove()
    log_path = APP_CONFIG_DIR / "type_fighter.log"
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        log_path,
        rotation="2 MB",
        retention=5,
        compression="zip",
        backtrace=True,
        diagnose=verbose,
        level=level,
    )
    if verbose:
        logger.add(sys.stderr, level="DEBUG", backtrace=True, diagnose=True)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical("Unhandled client exception")

    sys.excepthook = handle_exception
    logger.info("Type Fighter client logging started at {} level={}", log_path, level)


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


def draw_version_label(surface, font):
    width, height = surface.get_size()
    label = f"v{CLIENT_VERSION}"
    warning = player_storage.get("warning", "")
    if warning:
        label = f"{label}  |  {warning}"
    text = font.render(label, True, MUTED_TEXT)
    surface.blit(text, text.get_rect(bottomright=(width - 18, height - 18)))


def scrollbar_thumb_rect(track_rect, total_items, visible_items, first_visible):
    if total_items <= visible_items:
        return None
    visible_ratio = visible_items / total_items
    thumb_height = max(28, int(track_rect.height * visible_ratio))
    max_first_visible = max(1, total_items - visible_items)
    travel = track_rect.height - thumb_height
    thumb_y = track_rect.y + int(travel * first_visible / max_first_visible)
    return pygame.Rect(track_rect.x + 2, thumb_y, track_rect.width - 4, thumb_height)


def draw_scrollbar(surface, track_rect, total_items, visible_items, first_visible):
    thumb_rect = scrollbar_thumb_rect(track_rect, total_items, visible_items, first_visible)
    if thumb_rect is None:
        return None

    pygame.draw.rect(surface, (18, 27, 48), track_rect, border_radius=4)
    pygame.draw.rect(surface, (43, 57, 89), track_rect, 1, border_radius=4)
    pygame.draw.rect(surface, ACCENT, thumb_rect, border_radius=4)
    return thumb_rect


def drag_scroll_index(mouse_y, track_rect, thumb_height, total_items, visible_items, drag_offset):
    max_first_visible = max(0, total_items - visible_items)
    if max_first_visible <= 0:
        return 0
    travel = max(1, track_rect.height - thumb_height)
    thumb_y = max(track_rect.y, min(mouse_y - drag_offset, track_rect.y + travel))
    return int(round((thumb_y - track_rect.y) * max_first_visible / travel))


def keep_index_visible(index, first_visible, total_items, visible_items):
    max_first_visible = max(0, total_items - visible_items)
    first_visible = max(0, min(first_visible, max_first_visible))
    if index < first_visible:
        return max(0, min(index, max_first_visible))
    if index >= first_visible + visible_items:
        return max(0, min(index - visible_items + 1, max_first_visible))
    return first_visible


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
    battle["defense_drone_image"] = load_battle_image(pod_dir / "defense_drone_image.png", (28, 28))
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


def normalize_players(data):
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
        lives = coerce_int(item.get("lives", STARTING_LIVES), STARTING_LIVES)
        shield_charges = coerce_int(item.get("shield_charges", 0), 0)
        players.append(
            create_player_record(
                name[:24],
                player_id=item.get("id"),
                completed_lessons=completed_lessons,
                lives=max(1, min(player_limits.MAX_PLAYER_LIVES, lives)),
                shield_charges=max(0, shield_charges),
                lifetime_score=item.get("lifetime_score", 0),
                achievements=item.get("achievements", []),
                purchased_upgrade_ids=item.get("purchased_upgrade_ids", []),
                sold_lives=item.get("sold_lives", 0),
                sold_shields=item.get("sold_shields", 0),
                credits=item.get("credits", 0),
                perfect_lessons=item.get("perfect_lessons", []),
                high_score_lessons=item.get("high_score_lessons", []),
                quick_lessons=item.get("quick_lessons", []),
                time_stop_charges=item.get("time_stop_charges", 0),
                last_mission_stats=item.get("last_mission_stats", {}),
                mission_settings=item.get("mission_settings", {}),
                pod=item.get("pod", {}),
                updated_at=item.get("updated_at", ""),
                game_version=item.get("game_version", CLIENT_VERSION),
            )
        )
        seen_names.add(name.lower())
    return players


def load_local_players():
    return normalize_players(player_storage_sqlite.load_player_dbs())


def save_local_players(players):
    for player in players:
        if isinstance(player, dict):
            player_storage_sqlite.write_player_db(player, CLIENT_VERSION)


def load_players():
    return load_local_players()


def save_players(players):
    save_local_players(players)


def create_player_record(
    name,
    player_id=None,
    completed_lessons=None,
    lives=STARTING_LIVES,
    shield_charges=0,
    lifetime_score=0,
    achievements=None,
    purchased_upgrade_ids=None,
    sold_lives=0,
    sold_shields=0,
    credits=0,
    perfect_lessons=None,
    high_score_lessons=None,
    quick_lessons=None,
    time_stop_charges=0,
    last_mission_stats=None,
    mission_settings=None,
    pod=None,
    updated_at="",
    game_version=CLIENT_VERSION,
):
    lifetime_score = coerce_int(lifetime_score, 0)
    credits = coerce_int(credits, 0)
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
    achievement_awards = normalize_achievement_awards(achievements)
    if achievement_awards.get("fully_upgraded"):
        shield_cap += 1

    player = {
        "id": str(player_id or uuid.uuid4()),
        "name": name,
        "completed_lessons": completed_lessons or [],
        "lives": max(1, min(player_limits.MAX_PLAYER_LIVES, lives)),
        "shield_charges": max(0, min(shield_cap, shield_charges)),
        "lifetime_score": max(0, lifetime_score),
        "achievements": achievement_awards,
        "purchased_upgrade_ids": normalize_string_list(purchased_upgrade_ids),
        "sold_lives": max(0, coerce_int(sold_lives, 0)),
        "sold_shields": max(0, coerce_int(sold_shields, 0)),
        "credits": max(0, credits),
        "perfect_lessons": normalize_lesson_number_list(perfect_lessons),
        "high_score_lessons": normalize_lesson_number_list(high_score_lessons),
        "quick_lessons": normalize_lesson_number_list(quick_lessons),
        "time_stop_charges": max(0, coerce_int(time_stop_charges, 0)),
        "last_mission_stats": last_mission_stats if isinstance(last_mission_stats, dict) else {},
        "mission_settings": normalize_mission_settings(mission_settings),
        "updated_at": updated_at if isinstance(updated_at, str) and updated_at else player_storage_sqlite.utc_now(),
        "game_version": game_version if isinstance(game_version, str) and game_version else CLIENT_VERSION,
        "pod": {
            "color": pod_color,
            "type": pod_type,
            "upgrades": pod_upgrades,
        },
    }
    return player


def clean_player_name(name):
    return re.sub(r"\s+", " ", name).strip()[:24]


def unlocked_lesson_count(player):
    return model_unlocked_lesson_count(player, len(LESSONS))


def mark_lesson_perfect_if_applicable(player, lesson_number):
    stats = player.get("last_mission_stats")
    if not mission_stats_are_perfect(stats, lesson_number):
        return False
    perfect_lessons = set(normalize_lesson_number_list(player.get("perfect_lessons", [])))
    before_count = len(perfect_lessons)
    perfect_lessons.add(lesson_number)
    player["perfect_lessons"] = sorted(perfect_lessons)
    return len(perfect_lessons) != before_count


def load_lesson_module(module_name):
    return importlib.import_module(module_name)


def toggle_fullscreen():
    global is_fullscreen
    screen = pygame.display.get_surface()
    if is_letterboxed_fullscreen() or (screen is not None and screen.get_flags() & pygame.FULLSCREEN):
        is_fullscreen = False
        size = user_settings.window_size()
        surface = set_windowed_16_9(size)
        user_settings.set_display_state(False, surface.get_size())
        return surface
    is_fullscreen = True
    surface = set_fullscreen_16_9()
    user_settings.set_display_state(True)
    return surface


def enforce_min_window_size(screen):
    surface = enforce_16_9_window(screen)
    if not is_letterboxed_fullscreen() and not (surface.get_flags() & pygame.FULLSCREEN):
        user_settings.set_display_state(False, surface.get_size())
    return surface


def initial_display_surface():
    global is_fullscreen
    if user_settings.windowed():
        is_fullscreen = False
        return set_windowed_16_9(user_settings.window_size())
    is_fullscreen = True
    return set_fullscreen_16_9()


def run_lesson(screen, clock, lesson, player):
    stop_menu_music()
    intro = load_lesson_module(lesson["intro_module"])
    mission = load_lesson_module(lesson["mission_module"])

    intro_result = intro.run(screen, clock, BASE_DIR)
    if intro_result != "start":
        return intro_result

    while True:
        result = mission.run(screen, clock, BASE_DIR, player)
        if result != "restart":
            return result


def run_lesson_from_menu(screen, clock, lesson, player):
    result = run_lesson(screen, clock, lesson, player)
    if result != "quit":
        ensure_menu_music()
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
        draw_text(screen, "Esc: Back", small_font, MUTED_TEXT, (left, height - 58))
        draw_version_label(screen, small_font)
        pygame.display.flip()
        clock.tick(60)


def player_select_loop(screen, clock):
    ensure_menu_music()
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
    scrollbar_rect = pygame.Rect(0, 0, 0, 0)
    scrollbar_thumb = None
    scrollbar_drag_offset = 0
    dragging_scrollbar = False
    visible_rows = 1
    first_visible = 0
    suppress_hover_until_redraw = False
    nav_repeat_at = 0

    def navigate(step):
        nonlocal selected, delete_confirm, suppress_hover_until_redraw
        if not players:
            return
        selected = (selected + step) % len(players)
        play_menu_beep()
        delete_confirm = False
        suppress_hover_until_redraw = True

    while True:
        update_star_field(stars, clock.get_time() / 1000)
        if selected >= len(players):
            selected = max(0, len(players) - 1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_players(players)
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                elif event.key == pygame.K_q:
                    save_players(players)
                    return "quit"
                elif delete_confirm and event.key == pygame.K_y and players:
                    deleted = players.pop(selected)
                    player_storage_sqlite.delete_player_db(deleted)
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
                    navigate(1)
                elif event.key in (pygame.K_UP, pygame.K_w) and players:
                    navigate(-1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and players:
                    return players, players[selected]
            if event.type == pygame.MOUSEBUTTONDOWN and players:
                if event.button == 1:
                    if scrollbar_thumb is not None and scrollbar_thumb.collidepoint(event.pos):
                        dragging_scrollbar = True
                        scrollbar_drag_offset = event.pos[1] - scrollbar_thumb.y
                        continue
                    for index, rect in player_rects:
                        if rect.collidepoint(event.pos):
                            return players, players[index]
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_scrollbar = False
            if event.type == pygame.MOUSEMOTION and dragging_scrollbar and players:
                first_visible = drag_scroll_index(
                    event.pos[1],
                    scrollbar_rect,
                    scrollbar_thumb.height if scrollbar_thumb is not None else 28,
                    len(players),
                    visible_rows,
                    scrollbar_drag_offset,
                )
                new_selected = min(len(players) - 1, first_visible + max(0, visible_rows - 1))
                if new_selected != selected:
                    selected = new_selected
                    play_menu_beep()
                delete_confirm = False
            elif event.type == pygame.MOUSEMOTION and players:
                if suppress_hover_until_redraw:
                    continue
                for index, rect in player_rects:
                    if rect.collidepoint(event.pos):
                        if index != selected:
                            selected = index
                            play_menu_beep()
                            delete_confirm = False
                        break
            if event.type == pygame.MOUSEWHEEL and players:
                step, last_wheel_scroll_time = should_apply_menu_wheel(event, last_wheel_scroll_time)
                if step:
                    selected = (selected + step) % len(players)
                    play_menu_beep()
                    delete_confirm = False

        # Hold Up/Down (or W/S) to keep moving through the list (~3x/second).
        held = pygame.key.get_pressed()
        nav_dir = 1 if (held[pygame.K_DOWN] or held[pygame.K_s]) else (-1 if (held[pygame.K_UP] or held[pygame.K_w]) else 0)
        nav_now = pygame.time.get_ticks()
        if nav_dir == 0 or not players:
            nav_repeat_at = 0
        elif nav_repeat_at == 0:
            nav_repeat_at = nav_now + NAV_REPEAT_DELAY_MS
        elif nav_now >= nav_repeat_at:
            navigate(nav_dir)
            nav_repeat_at = nav_now + NAV_REPEAT_INTERVAL_MS

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
            scrollbar_thumb = draw_scrollbar(screen, scrollbar_rect, len(players), visible_rows, first_visible)
            if scrollbar_thumb is None:
                dragging_scrollbar = False

        if delete_confirm and players:
            message = f"Delete {players[selected]['name']}? Press Y to confirm or N to cancel."
            draw_text(screen, message, small_font, (245, 203, 92), (text_left + 4, height - 88))
        footer = "Enter/␣: Select  |  N: New  |  Delete: Delete  |  Q: Quit"
        draw_text(screen, footer, small_font, MUTED_TEXT, (text_left + 4, height - 58))
        draw_version_label(screen, small_font)
        pygame.display.flip()
        suppress_hover_until_redraw = False
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


def message_modal(screen, clock, title, message):
    title_font = pygame.font.SysFont("arial", 38, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    ok_rect = pygame.Rect(0, 0, 0, 0)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ok_rect.collidepoint(event.pos):
                    return None

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        screen.fill(BG_COLOR)
        draw_modal_backdrop(screen)
        rect = pygame.Rect(0, 0, min(660, width - 80), 290)
        rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), rect, border_radius=8)
        pygame.draw.rect(screen, LOCKED_SELECTED, rect, 2, border_radius=8)
        draw_text(screen, title, title_font, TEXT_COLOR, (rect.x + 28, rect.y + 28))
        text_rect = pygame.Rect(rect.x + 34, rect.y + 96, rect.width - 68, 92)
        draw_centered_wrapped_text(screen, message, body_font, MUTED_TEXT, text_rect)
        ok_rect = pygame.Rect(rect.right - 174, rect.bottom - 62, 142, 42)
        draw_modal_button(screen, ok_rect, "OK", body_font, True, True)
        pygame.display.flip()
        clock.tick(60)


def wrap_plain_text(text, font, max_width):
    # Word-wrap to max_width, preserving explicit newlines as paragraph breaks.
    lines = []
    for paragraph in str(text).split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
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


def draw_default_achievement_image(surface, rect):
    pygame.draw.rect(surface, (16, 28, 52), rect, border_radius=8)
    center = rect.center
    radius = max(20, min(rect.width, rect.height) // 3)
    ribbon_width = max(14, rect.width // 9)
    ribbon_top = center[1] + radius // 2
    left_ribbon = [
        (center[0] - ribbon_width - 8, ribbon_top),
        (center[0] - 4, ribbon_top),
        (center[0] - 10, rect.bottom - 22),
        (center[0] - ribbon_width - 18, rect.bottom - 8),
    ]
    right_ribbon = [
        (center[0] + 4, ribbon_top),
        (center[0] + ribbon_width + 8, ribbon_top),
        (center[0] + ribbon_width + 18, rect.bottom - 8),
        (center[0] + 10, rect.bottom - 22),
    ]
    pygame.draw.polygon(surface, (64, 118, 196), left_ribbon)
    pygame.draw.polygon(surface, (82, 151, 224), right_ribbon)
    pygame.draw.circle(surface, (236, 192, 82), center, radius)
    pygame.draw.circle(surface, (255, 226, 122), center, radius - max(5, radius // 8), 3)
    points = []
    inner = radius * 0.38
    outer = radius * 0.68
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        distance = outer if index % 2 == 0 else inner
        points.append((center[0] + math.cos(angle) * distance, center[1] + math.sin(angle) * distance))
    pygame.draw.polygon(surface, (255, 248, 208), points)


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


def ensure_menu_music():
    global menu_music_channel
    if not pygame.mixer.get_init():
        return
    if menu_music_channel is not None and menu_music_channel.get_busy():
        return
    menu_music = load_ui_sound(BASE_DIR / "sfx" / "game_intro_music.wav", 0.35)
    if menu_music is not None:
        menu_music_channel = menu_music.play(loops=-1, fade_ms=900)


def stop_menu_music(fade_ms=700):
    global menu_music_channel
    if menu_music_channel is None:
        return
    if fade_ms:
        menu_music_channel.fadeout(fade_ms)
    else:
        menu_music_channel.stop()
    menu_music_channel = None


def play_menu_beep():
    play_ui_sound(load_ui_sound(BASE_DIR / "sfx" / "beep.wav", 0.45))


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


def resolve_achievement_image_path(image_name):
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
        for base in (
            BASE_DIR / "gfx" / "achievements",
            BASE_DIR / "gfx",
            BASE_DIR,
        ):
            candidate = base / name
            if candidate.exists():
                return candidate
    return None


def disabled_image_name(image_name):
    if not isinstance(image_name, str) or not image_name.strip():
        return ""
    path = Path(image_name.strip())
    suffix = path.suffix or ".png"
    stem = path.stem if path.suffix else path.name
    return str(path.with_name(f"{stem}_disabled{suffix}"))


def achievement_by_id(achievement_id):
    for achievement in ACHIEVEMENTS:
        if achievement.get("id") == achievement_id:
            return achievement
    return None


def achievement_modal_payload(achievement):
    reward_credits = int(achievement.get("reward_credits", 0) or 0)
    score = int(achievement.get("score", 0) or 0)
    reward_bits = []
    if reward_credits:
        reward_bits.append(f"+{reward_credits} credits")
    if score:
        reward_bits.append(f"+{score} Score")
    text = str(achievement.get("text", "")).strip()
    if reward_bits:
        text = f"{text}\n\nReward: {', '.join(reward_bits)}" if text else f"Reward: {', '.join(reward_bits)}"
    return {
        "kind": "achievement",
        "title": str(achievement.get("name", "Achievement Unlocked")).strip() or "Achievement Unlocked",
        "text": text,
        "image_path": resolve_achievement_image_path(achievement.get("image", "")),
    }


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
    lifetime_score = player.get("lifetime_score", 0)
    if not isinstance(lifetime_score, int):
        lifetime_score = 0
    player["lifetime_score"] = max(0, lifetime_score) + int(achievement.get("score", 0) or 0)
    if achievement_id == "fully_upgraded":
        player["shield_charges"] = min(player_shield_max_charges(player), max(player.get("shield_charges", 0), 6))
    return achievement_modal_payload(achievement)


def achievement_requirements_met(player, lesson_number=None):
    return model_achievement_requirements_met(player, lesson_number, len(LESSONS[:36]))


def collect_new_achievement_modals(player, lesson_number=None):
    if lesson_number is not None:
        record_latest_mission_achievement_progress(player, lesson_number)
    else:
        stats = player.get("last_mission_stats")
        if isinstance(stats, dict) and isinstance(stats.get("lesson_number"), int):
            record_latest_mission_achievement_progress(player, stats["lesson_number"])
    queued = []
    for achievement_id in achievement_requirements_met(player, lesson_number):
        modal = award_achievement(player, achievement_id)
        if modal is not None:
            queued.append(modal)
    return queued


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


def collect_badge_unlock_modals(player, lesson_number):
    # Per-level medal unlock modals. Must run BEFORE collect_new_achievement_modals,
    # which marks the lessons (so "newly earned" detection works).
    queue = []
    stats = player.get("last_mission_stats", {})
    high_score_lessons = set(normalize_lesson_number_list(player.get("high_score_lessons", [])))
    if lesson_number not in high_score_lessons and mission_stats_are_high_score(stats, lesson_number):
        try:
            score = int(stats.get("score", 0) or 0)
            goal = int(stats.get("high_score_goal", 0) or 0)
        except (TypeError, ValueError):
            score, goal = 0, 0
        queue.append(
            {
                "kind": "achievement",
                "title": "High Scorer!",
                "text": (
                    "You earned the High Scorer medal for this level!\n\n"
                    f"Score needed: {goal}\n"
                    f"Your score: {score}"
                ),
                "image_path": BASE_DIR / "gfx" / "misc" / "high_scorer_medal.png",
            }
        )
    quick_lessons = set(normalize_lesson_number_list(player.get("quick_lessons", [])))
    if lesson_number not in quick_lessons and mission_stats_are_quick(stats, lesson_number):
        try:
            time_ms = int(stats.get("level_time_ms", 0) or 0)
            goal_ms = int(stats.get("quick_time_goal_ms", 0) or 0)
        except (TypeError, ValueError):
            time_ms, goal_ms = 0, 0
        queue.append(
            {
                "kind": "achievement",
                "title": "Quick Defender!",
                "text": (
                    "You earned the Quick Defender medal for this level!\n\n"
                    f"Time to beat: {goal_ms / 1000:.2f}s\n"
                    f"Your time: {time_ms / 1000:.2f}s"
                ),
                "image_path": BASE_DIR / "gfx" / "misc" / "quick_defender_medal.png",
            }
        )
    return queue


def collect_mission_reward_modals(player, lesson_number, include_unlocks=True):
    queue = []
    if include_unlocks:
        queue.extend(collect_lesson_unlock_modals(lesson_number))
        if lesson_number == mission_engine.TIME_STOP_UNLOCK_LESSON:
            queue.append(
                {
                    "kind": "achievement",
                    "title": "Time Stop Unlocked!",
                    "text": (
                        "You've unlocked Time Stop!\n\n"
                        "Tap Spacebar 3 times quickly to bend time and clean up the level "
                        "while everything else crawls.\n"
                        "Collect Time Stop power-ups (black hexagons) from level 27 on."
                    ),
                    "image_path": BASE_DIR / "gfx" / "misc" / "time_stop_medal.png",
                }
            )
    queue.extend(collect_badge_unlock_modals(player, lesson_number))
    queue.extend(collect_new_achievement_modals(player, lesson_number))
    return queue


def draw_achievement_tile(screen, rect, achievement, earned, title_font, body_font):
    fill = (18, 30, 55) if earned else (12, 18, 32)
    border = ACCENT if earned else (52, 62, 82)
    title_color = TEXT_COLOR if earned else MUTED_TEXT
    text_color = MUTED_TEXT if earned else (92, 102, 126)
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)

    image_name = achievement.get("image", "")
    if not earned:
        image_name = disabled_image_name(image_name)
    image = load_ui_image(resolve_achievement_image_path(image_name))
    image_rect = pygame.Rect(rect.x + 16, rect.y + 16, 84, 84)
    if image is not None:
        scaled = pygame.transform.smoothscale(image, image_rect.size)
        screen.blit(scaled, image_rect)
    else:
        draw_default_achievement_image(screen, image_rect)
        if not earned:
            dim = pygame.Surface(image_rect.size, pygame.SRCALPHA)
            dim.fill((0, 0, 0, 120))
            screen.blit(dim, image_rect)

    text_left = image_rect.right + 16
    status = "Earned" if earned else "Locked"
    draw_text(screen, str(achievement.get("name", "Achievement")), title_font, title_color, (text_left, rect.y + 18))
    draw_text(screen, status, body_font, ACCENT if earned else MUTED_TEXT, (text_left, rect.y + 48))
    text_rect = pygame.Rect(text_left, rect.y + 76, rect.right - text_left - 16, rect.bottom - rect.y - 88)
    lines = wrap_plain_text(str(achievement.get("text", "")), body_font, text_rect.width)
    y = text_rect.y
    for line in lines[:2]:
        rendered = body_font.render(line, True, text_color)
        screen.blit(rendered, (text_rect.x, y))
        y += body_font.get_linesize()


def achievements_modal_loop(screen, clock, player):
    title_font = pygame.font.SysFont("arial", 38, bold=True)
    tile_title_font = pygame.font.SysFont("arial", 20, bold=True)
    body_font = pygame.font.SysFont("arial", 16)
    button_font = pygame.font.SysFont("arial", 22, bold=True)
    earned_ids = set(normalized_achievement_ids(player.get("achievements", [])))
    scroll = 0
    close_rect = pygame.Rect(0, 0, 0, 0)
    background = screen.copy()
    achievement_rects = []
    hovered_achievement_id = None
    dragging_scrollbar = False
    scrollbar_drag_offset = 0
    track_rect = pygame.Rect(0, 0, 0, 0)
    thumb_rect = None
    visible_rows = 1

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    return None
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    scroll += 1
                    play_menu_beep()
                if event.key in (pygame.K_UP, pygame.K_w):
                    scroll -= 1
                    play_menu_beep()
            if event.type == pygame.MOUSEWHEEL:
                scroll -= event.y
                play_menu_beep()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if thumb_rect is not None and thumb_rect.collidepoint(event.pos):
                    dragging_scrollbar = True
                    scrollbar_drag_offset = event.pos[1] - thumb_rect.y
                    continue
                if close_rect.collidepoint(event.pos):
                    return None
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_scrollbar = False
            if event.type == pygame.MOUSEMOTION and dragging_scrollbar:
                new_scroll = drag_scroll_index(
                    event.pos[1],
                    track_rect,
                    thumb_rect.height if thumb_rect is not None else 36,
                    len(ACHIEVEMENTS),
                    visible_rows,
                    scrollbar_drag_offset,
                )
                if new_scroll != scroll:
                    scroll = new_scroll
                    play_menu_beep()
            elif event.type == pygame.MOUSEMOTION:
                next_hovered_id = None
                for achievement_id, rect in achievement_rects:
                    if rect.collidepoint(event.pos):
                        next_hovered_id = achievement_id
                        break
                if next_hovered_id is not None and next_hovered_id != hovered_achievement_id:
                    play_menu_beep()
                hovered_achievement_id = next_hovered_id

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        if background.get_size() == screen.get_size():
            screen.blit(background, (0, 0))
        else:
            screen.fill(BG_COLOR)
        draw_modal_backdrop(screen)
        modal_rect = pygame.Rect(0, 0, min(980, width - 80), min(760, height - 48))
        modal_rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), modal_rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT, modal_rect, 2, border_radius=8)

        draw_text(screen, "ACHIEVEMENTS", title_font, TEXT_COLOR, (modal_rect.x + 30, modal_rect.y + 24))
        earned_label = f"{len(earned_ids)}/{len(ACHIEVEMENTS)} earned"
        earned_surface = body_font.render(earned_label, True, MUTED_TEXT)
        screen.blit(earned_surface, earned_surface.get_rect(right=modal_rect.right - 30, y=modal_rect.y + 42))

        tile_gap = 12
        tile_height = 124
        list_top = modal_rect.y + 88
        list_bottom = modal_rect.bottom - 82
        visible_rows = max(1, (list_bottom - list_top + tile_gap) // (tile_height + tile_gap))
        max_scroll = max(0, len(ACHIEVEMENTS) - visible_rows)
        scroll = max(0, min(scroll, max_scroll))
        tile_width = modal_rect.width - 60
        clip_rect = pygame.Rect(modal_rect.x + 30, list_top, tile_width, list_bottom - list_top)
        achievement_rects = []
        previous_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        for visible_index, achievement in enumerate(ACHIEVEMENTS[scroll : scroll + visible_rows]):
            tile_rect = pygame.Rect(clip_rect.x, list_top + visible_index * (tile_height + tile_gap), tile_width, tile_height)
            achievement_id = achievement.get("id")
            achievement_rects.append((achievement_id, tile_rect))
            draw_achievement_tile(screen, tile_rect, achievement, achievement_id in earned_ids, tile_title_font, body_font)
        screen.set_clip(previous_clip)

        if max_scroll > 0:
            track_rect = pygame.Rect(modal_rect.right - 20, list_top, 6, list_bottom - list_top)
            thumb_height = max(36, int(track_rect.height * visible_rows / len(ACHIEVEMENTS)))
            thumb_y = track_rect.y + int((track_rect.height - thumb_height) * scroll / max_scroll)
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
            pygame.draw.rect(screen, (31, 42, 66), track_rect, border_radius=3)
            pygame.draw.rect(screen, ACCENT, thumb_rect, border_radius=3)
        else:
            thumb_rect = None
            dragging_scrollbar = False

        close_rect = pygame.Rect(modal_rect.right - 160, modal_rect.bottom - 58, 130, 40)
        draw_modal_button(screen, close_rect, "Close", button_font, True, True)
        pygame.display.flip()
        clock.tick(60)


def reward_modal_loop(screen, clock, reward, background):
    title_font = pygame.font.SysFont("arial", 40, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    button_font = pygame.font.SysFont("arial", 24, bold=True)
    ok_rect = pygame.Rect(0, 0, 0, 0)
    image = load_ui_image(reward.get("image_path")) if reward.get("image_path") else None
    if reward.get("kind") in ("unlock", "achievement"):
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
        elif reward.get("kind") == "achievement":
            draw_default_achievement_image(screen, image_rect)
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
    # Capture the clean scene ONCE. Re-copying per modal would snapshot the
    # previous modal's already-dimmed frame, stacking backdrops until the
    # background turns black after the first couple of modals.
    background = screen.copy()
    while queue:
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


def draw_buy_button(screen, rect, font, hovered=False, enabled=True):
    if not enabled:
        fill, border, color = (12, 17, 28), (35, 42, 62), MUTED_TEXT
    elif hovered:
        fill, border, color = (24, 56, 40), (88, 214, 141), TEXT_COLOR
    else:
        fill, border, color = (20, 40, 32), (65, 110, 90), TEXT_COLOR
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    pygame.draw.rect(screen, border, rect, 2, border_radius=6)
    label = font.render("Buy", True, color)
    screen.blit(label, label.get_rect(center=rect.center))


def draw_sell_button(screen, rect, font, hovered=False, enabled=True):
    if not enabled:
        fill, border, color = (12, 17, 28), (35, 42, 62), MUTED_TEXT
    elif hovered:
        fill, border, color = (58, 28, 32), (219, 92, 101), TEXT_COLOR
    else:
        fill, border, color = (44, 24, 28), (110, 60, 64), TEXT_COLOR
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    pygame.draw.rect(screen, border, rect, 2, border_radius=6)
    label = font.render("Sell", True, color)
    screen.blit(label, label.get_rect(center=rect.center))


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
        f"Credits: {player_credits(player)}    Rank: {player_rank(player)}    Lives: {player_lives(player)}    Shields: {player.get('shield_charges', 0)}/{player_shield_max_charges(player)}",
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
            buy_enabled = not (upgrade["id"] == "extra_life" and player_lives(player) >= player_limits.MAX_PLAYER_LIVES)
            draw_sell_button(screen, sell_rect, small_font, sell_rect.collidepoint(mouse_pos), sell_enabled)
            draw_buy_button(screen, buy_rect, small_font, buy_rect.collidepoint(mouse_pos) and buy_enabled, buy_enabled)
            if sell_enabled:
                action_rects.append(("sell", index, sell_rect))
            if buy_enabled:
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
                    new_quantity = min(max_quantity, quantity + 1)
                    if new_quantity != quantity:
                        quantity = new_quantity
                        play_menu_beep()
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    new_quantity = max(1, quantity - 1)
                    if new_quantity != quantity:
                        quantity = new_quantity
                        play_menu_beep()
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return quantity
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if up_rect.collidepoint(event.pos):
                    new_quantity = min(max_quantity, quantity + 1)
                    if new_quantity != quantity:
                        quantity = new_quantity
                        play_menu_beep()
                elif down_rect.collidepoint(event.pos):
                    new_quantity = max(1, quantity - 1)
                    if new_quantity != quantity:
                        quantity = new_quantity
                        play_menu_beep()
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
    hovered_color_index = None
    suppress_hover_until_redraw = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % len(UPGRADE_COLORS)
                    play_menu_beep()
                    suppress_hover_until_redraw = True
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % len(UPGRADE_COLORS)
                    play_menu_beep()
                    suppress_hover_until_redraw = True
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 4) % len(UPGRADE_COLORS)
                    play_menu_beep()
                    suppress_hover_until_redraw = True
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 4) % len(UPGRADE_COLORS)
                    play_menu_beep()
                    suppress_hover_until_redraw = True
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return UPGRADE_COLORS[selected][0]
            if event.type == pygame.MOUSEMOTION:
                if suppress_hover_until_redraw:
                    continue
                next_hovered_color = None
                for index, rect in enumerate(color_rects):
                    if rect.collidepoint(event.pos):
                        next_hovered_color = index
                        break
                if next_hovered_color is not None and next_hovered_color != hovered_color_index:
                    hovered_color_index = next_hovered_color
                    selected = next_hovered_color
                    play_menu_beep()
                elif next_hovered_color is None:
                    hovered_color_index = None
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
        suppress_hover_until_redraw = False
        clock.tick(60)


def upgrades_modal_loop(screen, clock, players, player):
    title_font = pygame.font.SysFont("arial", 42, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 20)
    action_rects = []
    close_rect = pygame.Rect(0, 0, 0, 0)
    hovered_action = None
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
            if event.type == pygame.MOUSEMOTION:
                next_hovered_action = None
                for action, index, rect in action_rects:
                    if rect.collidepoint(event.pos):
                        next_hovered_action = (action, index)
                        break
                if close_rect.collidepoint(event.pos):
                    next_hovered_action = ("close", -1)
                if next_hovered_action is not None and next_hovered_action != hovered_action:
                    play_menu_beep()
                hovered_action = next_hovered_action

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


def _draw_rhombus_badge(screen, center, radius, fill, edge):
    points = [
        (center[0], center[1] - radius),
        (center[0] + radius, center[1]),
        (center[0], center[1] + radius),
        (center[0] - radius, center[1]),
    ]
    pygame.draw.polygon(screen, fill, points)
    pygame.draw.polygon(screen, edge, points, 2)


def _draw_hexagon_badge(screen, center, radius, fill, edge):
    points = [
        (
            center[0] + radius * math.cos(math.pi / 6 + index * math.pi / 3),
            center[1] + radius * math.sin(math.pi / 6 + index * math.pi / 3),
        )
        for index in range(6)
    ]
    pygame.draw.polygon(screen, fill, points)
    pygame.draw.polygon(screen, edge, points, 2)


def draw_lesson_badges(screen, card_rect, lesson_number, player, font):
    # Earned-badge markers on a mission card, laid out right-to-left.
    badges = []
    if lesson_number in set(normalize_lesson_number_list(player.get("perfect_lessons", []))):
        badges.append(("P", "rhombus", (255, 190, 68), (255, 236, 156), (42, 28, 8)))
    if lesson_number in set(normalize_lesson_number_list(player.get("high_score_lessons", []))):
        badges.append(("H", "rhombus", (116, 211, 255), (208, 240, 255), (6, 28, 42)))
    if lesson_number in set(normalize_lesson_number_list(player.get("quick_lessons", []))):
        badges.append(("D", "hexagon", (88, 214, 141), (200, 245, 214), (6, 40, 22)))
    radius = 15
    cx = card_rect.right - 34
    for letter, shape, fill, edge, text_color in badges:
        center = (cx, card_rect.centery)
        if shape == "rhombus":
            _draw_rhombus_badge(screen, center, radius, fill, edge)
        else:
            _draw_hexagon_badge(screen, center, radius, fill, edge)
        label = font.render(letter, True, text_color)
        label_rect = label.get_rect(center=center)
        label_rect.centerx += 1
        label_rect.centery += 1
        screen.blit(label, label_rect)
        cx -= 40


def menu_loop(screen, clock, players, player):
    ensure_menu_music()
    title_font = pygame.font.SysFont("arial", 54, bold=True)
    item_font = pygame.font.SysFont("arial", 30, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 18)
    marker_font = pygame.font.SysFont("arial", 18, bold=True)

    selected = 0
    stars = create_star_field()
    mission_rects = []
    upgrades_button_rect = None
    achievements_button_rect = None
    upgrades_image = load_ui_image(BASE_DIR / "gfx" / "upgrades" / "upgrades.png")
    achievements_image = load_ui_image(BASE_DIR / "gfx" / "achievements" / "achievements.png")
    mock_battle = create_mock_battle()
    last_wheel_scroll_time = 0
    scrollbar_rect = pygame.Rect(0, 0, 0, 0)
    scrollbar_thumb = None
    scrollbar_drag_offset = 0
    dragging_scrollbar = False
    visible_rows = 1
    first_visible = 0
    suppress_hover_until_redraw = False
    nav_repeat_at = 0

    def navigate(step):
        nonlocal selected, first_visible, suppress_hover_until_redraw
        new_selected = max(0, min(len(LESSONS) - 1, selected + step))
        if new_selected != selected:
            selected = new_selected
            first_visible = keep_index_visible(selected, first_visible, len(LESSONS), visible_rows)
            play_menu_beep()
        suppress_hover_until_redraw = True

    # Login achievement check: award (and queue modals for) any achievements the
    # player now qualifies for -- including achievements added since they last
    # played -- the moment they enter the menu after selecting a profile.
    pending_reward_modals = collect_new_achievement_modals(player)
    if pending_reward_modals:
        save_players(players)

    while True:
        if player_storage.get("warning"):
            return "players"
        update_star_field(stars, clock.get_time() / 1000)
        unlocked_count = len(LESSONS) if cheats.is_enabled("11") else unlocked_lesson_count(player)
        upgrades_available = 2 in set(player.get("completed_lessons", []))
        if not upgrades_available:
            upgrades_button_rect = None
        achievements_available = achievement_count(player) > 0
        if not achievements_available:
            achievements_button_rect = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_players(players)
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                if event.key == pygame.K_q:
                    save_players(players)
                    return "quit"
                if event.key == pygame.K_ESCAPE:
                    save_players(players)
                    return "players"
                if event.key == pygame.K_o:
                    unlocked_lesson = max(1, unlocked_count)
                    unlocks = {
                        "disable_defense_drones": mission_engine.player_defense_drone_count(player) > 0,
                        "disable_mega_shot": mission_engine.player_mega_shot_available(player, unlocked_lesson),
                        "disable_shields": mission_engine.player_shield_available(player, unlocked_lesson),
                        "music_enabled": True,
                    }
                    result = mission_engine.mission_settings_modal(
                        screen,
                        clock,
                        player,
                        mission_engine.player_mission_settings(player),
                        unlocks,
                    )
                    save_players(players)
                    if result == "quit":
                        return "quit"
                    pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
                    continue
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    navigate(1)
                if event.key in (pygame.K_UP, pygame.K_w):
                    navigate(-1)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected < unlocked_count:
                        completed_index = selected
                        lesson_number = LESSONS[completed_index]["number"]
                        was_completed = lesson_number in set(player.get("completed_lessons", []))
                        result = run_lesson_from_menu(screen, clock, LESSONS[completed_index], player)
                        save_players(players)
                        if result == "quit":
                            return "quit"
                        if result == "won":
                            mark_lesson_complete(player, lesson_number)
                            mark_lesson_perfect_if_applicable(player, lesson_number)
                            pending_reward_modals.extend(
                                collect_mission_reward_modals(player, lesson_number, not was_completed)
                            )
                            save_players(players)
                            selected = min(completed_index + 1, unlocked_lesson_count(player) - 1)
                            first_visible = keep_index_visible(selected, first_visible, len(LESSONS), visible_rows)
                        pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if scrollbar_thumb is not None and scrollbar_thumb.collidepoint(event.pos):
                    dragging_scrollbar = True
                    scrollbar_drag_offset = event.pos[1] - scrollbar_thumb.y
                    continue
                if achievements_button_rect is not None and achievements_button_rect.collidepoint(event.pos):
                    result = achievements_modal_loop(screen, clock, player)
                    if result == "quit":
                        return "quit"
                    pygame.event.clear((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
                    continue
                if upgrades_button_rect is not None and upgrades_button_rect.collidepoint(event.pos):
                    result = upgrades_modal_loop(screen, clock, players, player)
                    if result == "quit":
                        return "quit"
                    new_achievement_modals = collect_new_achievement_modals(player)
                    if new_achievement_modals:
                        pending_reward_modals.extend(new_achievement_modals)
                        save_players(players)
                    pygame.event.clear((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
                    continue
                for index, rect in mission_rects:
                    if rect.collidepoint(event.pos):
                        selected = index
                        if index < unlocked_count:
                            lesson_number = LESSONS[index]["number"]
                            was_completed = lesson_number in set(player.get("completed_lessons", []))
                            result = run_lesson_from_menu(screen, clock, LESSONS[index], player)
                            save_players(players)
                            if result == "quit":
                                return "quit"
                            if result == "won":
                                mark_lesson_complete(player, lesson_number)
                                mark_lesson_perfect_if_applicable(player, lesson_number)
                                pending_reward_modals.extend(
                                    collect_mission_reward_modals(player, lesson_number, not was_completed)
                                )
                                save_players(players)
                                selected = min(index + 1, unlocked_lesson_count(player) - 1)
                                first_visible = keep_index_visible(selected, first_visible, len(LESSONS), visible_rows)
                            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
                        break
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_scrollbar = False
            if event.type == pygame.MOUSEMOTION and dragging_scrollbar:
                first_visible = drag_scroll_index(
                    event.pos[1],
                    scrollbar_rect,
                    scrollbar_thumb.height if scrollbar_thumb is not None else 28,
                    len(LESSONS),
                    visible_rows,
                    scrollbar_drag_offset,
                )
                new_selected = min(len(LESSONS) - 1, first_visible + max(0, visible_rows - 1))
                if new_selected != selected:
                    selected = new_selected
                    play_menu_beep()
            elif event.type == pygame.MOUSEMOTION:
                if suppress_hover_until_redraw:
                    continue
                for index, rect in mission_rects:
                    if rect.collidepoint(event.pos):
                        if index != selected:
                            selected = index
                            play_menu_beep()
                        break
            if event.type == pygame.MOUSEWHEEL:
                step, last_wheel_scroll_time = should_apply_menu_wheel(event, last_wheel_scroll_time)
                if step:
                    new_selected = max(0, min(len(LESSONS) - 1, selected + step))
                    if new_selected != selected:
                        selected = new_selected
                        first_visible = keep_index_visible(selected, first_visible, len(LESSONS), visible_rows)
                        play_menu_beep()

        # Hold Up/Down (or W/S) to keep moving through the mission list (~3x/second).
        held = pygame.key.get_pressed()
        nav_dir = 1 if (held[pygame.K_DOWN] or held[pygame.K_s]) else (-1 if (held[pygame.K_UP] or held[pygame.K_w]) else 0)
        nav_now = pygame.time.get_ticks()
        if nav_dir == 0:
            nav_repeat_at = 0
        elif nav_repeat_at == 0:
            nav_repeat_at = nav_now + NAV_REPEAT_DELAY_MS
        elif nav_now >= nav_repeat_at:
            navigate(nav_dir)
            nav_repeat_at = nav_now + NAV_REPEAT_INTERVAL_MS

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        content_width = min(820, max(620, width - 120))
        content_left = (width - content_width) / 2
        text_left = content_left + 20
        screen.fill(BG_COLOR)
        draw_star_field(screen, stars)
        update_and_draw_mock_battle(screen, mock_battle, clock, content_left, content_left + content_width)
        achievements_button_rect = None
        if upgrades_available:
            upgrades_button_rect = pygame.Rect(content_left + content_width - 80, 128, 80, 80)
            if achievements_available:
                achievements_button_rect = pygame.Rect(upgrades_button_rect.x - 92, upgrades_button_rect.y, 80, 80)
                if achievements_image is not None:
                    draw_square_image_button(screen, achievements_button_rect, achievements_image)
                else:
                    draw_default_achievement_image(screen, achievements_button_rect)
                    pygame.draw.rect(screen, ACCENT, achievements_button_rect, 2, border_radius=8)
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
        first_visible = keep_index_visible(selected, first_visible, len(LESSONS), visible_rows)
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
            draw_lesson_badges(screen, card_rect, lesson["number"], player, marker_font)

        scrollbar_rect = pygame.Rect(content_left + content_width - 12, list_top - 22, 8, list_height)
        scrollbar_thumb = draw_scrollbar(screen, scrollbar_rect, len(LESSONS), visible_rows, first_visible)
        if scrollbar_thumb is None:
            dragging_scrollbar = False

        draw_text(screen, "O: Options  |  Esc: Players  |  F11: Max size  |  Q: Quit", small_font, MUTED_TEXT, (text_left + 4, height - 58))
        draw_version_label(screen, small_font)
        if pending_reward_modals:
            result = show_reward_modal_queue(screen, clock, pending_reward_modals)
            if result == "quit":
                return "quit"
            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
            continue
        pygame.display.flip()
        suppress_hover_until_redraw = False
        clock.tick(60)


def set_window_metadata():
    pygame.display.set_caption("Type Fighter")
    for icon_name in ("type-fighter-icon.png", "type-fighter-icon.ico"):
        try:
            pygame.display.set_icon(pygame.image.load(str(BASE_DIR / "gfx" / icon_name)))
            return
        except (OSError, pygame.error):
            pass


def set_windows_app_id():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TypeFighter.TypeFighter.Alpha")
    except (AttributeError, OSError):
        pass


def main():
    load_game_data_db(GAME_DATA_DB_PATH)
    apply_game_settings()
    setup_logging(logging_enabled())
    if cheats.wants_listing(sys.argv):
        for cheat_id, description in sorted(cheats.AVAILABLE_CHEATS.items()):
            logger.info("cheat {}: {}", cheat_id, description)
    enabled_cheats, unknown_cheats = cheats.enable_from_argv(sys.argv)
    if enabled_cheats:
        logger.warning("CHEATS ENABLED: {}", ", ".join(sorted(enabled_cheats)))
    if unknown_cheats:
        logger.warning("Unknown cheats ignored: {}", ", ".join(unknown_cheats))
    set_windows_app_id()
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass

    set_window_metadata()
    screen = initial_display_surface()
    if hasattr(pygame.display, "set_minimum_size"):
        pygame.display.set_minimum_size(*MIN_SCREEN_SIZE)
    clock = pygame.time.Clock()

    try:
        while True:
            selection = player_select_loop(screen, clock)
            if selection == "quit":
                break
            players, player = selection
            cheats.apply_player_cheats(player)
            save_players(players)
            result = menu_loop(screen, clock, players, player)
            if result == "quit":
                break
    except Exception:
        logger.exception("Fatal client error")
        raise
    finally:
        logger.info("Type Fighter client shutting down")
        stop_menu_music(0)
        pygame.quit()


if __name__ == "__main__":
    main()
