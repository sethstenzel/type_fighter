from dataclasses import dataclass
import json
import math
import random
from pathlib import Path

import pygame

from display_helpers import (
    SCREEN_SIZE as BASE_SCREEN_SIZE,
    enforce_16_9_window,
    is_letterboxed_fullscreen,
    set_fullscreen_16_9,
    set_windowed_16_9,
)
from lessons.key_render import display_key, render_inline_center, render_inline_text, render_key_label
from lessons.lesson_config import lesson_new_keys
from player_limits import MAX_PLAYER_LIVES


BG_COLOR = (5, 9, 20)
TEXT_COLOR = (232, 240, 255)
MUTED_TEXT = (140, 154, 184)
ACCENT = (72, 209, 204)
ONE_SHOT_DRONE_COLOR = (246, 216, 79)
TWO_SHOT_DRONE_COLOR = (240, 158, 74)
THREE_SHOT_DRONE_COLOR = (219, 92, 101)
MEGA_DRONE_COLOR = (153, 92, 214)
FINAL_BOSS_COLOR = (122, 77, 184)
FINAL_BOSS_SHIELD_COLOR = (116, 211, 255)
MEGA_SHOT_COLOR = (185, 250, 255)
BULLET_COLOR = (112, 241, 255)
SHOT_TRAIL_COLOR = (92, 190, 255)
SHIP_COLOR = (112, 170, 255)
EXPLOSION_COLOR = (255, 218, 125)
POD_ROTATION_SECONDS = 15
POD_IMAGE_SIZE = 204
PLAYER_COLLISION_RADIUS = 36
TURRET_IMAGE_SIZE = 108
DRONE_PIXELS_PER_ROTATION = 60
TURRET_TURN_SPEED = 25
TURRET_FIRE_ANGLE_THRESHOLD = 0.08
TURRET_FIRE_DELAY_MS = 90
SHOT_IMAGE_SIZE = 22
SHOT_TRAIL_INTERVAL_MS = 12
SHOT_ROTATIONS_PER_SECOND = 2
DEFENSE_DRONE_COLOR = (145, 150, 156)
DEFENSE_DRONE_RADIUS = 14
DEFENSE_DRONE_ORBIT_RADIUS = POD_IMAGE_SIZE // 2 + 42
DEFENSE_DRONE_ORBIT_SECONDS = 10
DEFENSE_DRONE_FIRE_INTERVAL_MS = 6000
DEFENSE_DRONE_SHOT_SPEED = 560
DEFENSE_DRONE_SHOT_RADIUS = 4
DEFENSE_DRONE_COLLISION_RADIUS = 16
DEFENSE_DRONE_LINE_OF_SIGHT_BLOCK_RADIUS = POD_IMAGE_SIZE // 2
DEFENSE_DRONE_ACCURACY_GRACE_MS = 3000

START_SPAWN_INTERVAL_MS = 6000
MIN_SPAWN_INTERVAL_MS = 2000
MIN_DRONE_SPAWN_RATE = 0.1
MAX_DRONE_SPAWN_RATE = 0.5
SPAWN_RATE_CHANGE_MS = 15000
KILLS_PER_DIFFICULTY_TIER = 5
STARTING_LIVES = 3
ENERGY_SAVER_BONUS_CREDITS = 50
DRONE_SPEED_BONUS_PER_TIER = 6
MINI_BOSS_INTERVAL = 10
MEGA_DRONE_HP = 5
MEGA_ATTACK_INTERVAL_MS = 3000
MEGA_PIXELS_PER_ROTATION = 135
MEGA_DRONE_RADIUS = 63
FINAL_BOSS_ROTATION_SECONDS = 5
BOSS_SHOT_RADIUS = 11
MINI_BOSS_SHOT_RADIUS = 20
NORMAL_DRONE_IMAGE_SCALE = 2
BOSS_SHOT_IMAGE_RADIUS = 44
BOSS_SHOT_SPEED = 190
FINAL_BOSS_SHOT_SPEED = 142
FINAL_BOSS_HP = 1
FINAL_BOSS_RADIUS = 87
FINAL_BOSS_IMAGE_SIZE = FINAL_BOSS_RADIUS * 2
FINAL_BOSS_SHIELD_MAX = 3
FINAL_BOSS_SHIELD_DOWN_MS = 15000
FINAL_BOSS_SHIELD_RECHARGE_MS = 5000
FINAL_BOSS_ATTACK_INTERVAL_MS = 4000
FINAL_BOSS_SEMI_BOSS_FIRST_SPAWN_MS = 20000
FINAL_BOSS_SEMI_BOSS_SPAWN_INTERVAL_MS = 20000
FINAL_BOSS_APPROACH_SPEED = 90
FINAL_BOSS_ORBIT_SECONDS = 10
FINAL_BOSS_PLAYER_X_RATIO = 0.78
FINAL_BOSS_ENTRY_PROGRESS = 0.30
FINAL_BOSS_VERTICAL_MIN_RATIO = 0.15
FINAL_BOSS_VERTICAL_MAX_RATIO = 0.85
FINAL_BOSS_PLAYER_PAN_SPEED = FINAL_BOSS_APPROACH_SPEED
FINAL_BOSS_ORBIT_SWITCH_MIN_MS = 10000
FINAL_BOSS_ORBIT_SWITCH_MAX_MS = 30000
MINI_BOSS_STRAFE_RANGE = 95
MINI_BOSS_STRAFE_SPEED_SCALE = 0.45
MINI_BOSS_CENTER_DISTANCE_SCALE = 0.25
NEW_KEY_ONLY_DRONES_PER_MISSION = 15
FINAL_BOSS_NEW_KEY_SPAWN_WEIGHT = 0.7
PLAYER_SHIELD_MAX_CHARGES = 3
PLAYER_SHIELD_START_LESSON = 7
PLAYER_SHIELD_RECHARGE_MS = 20000 # TODO: Pretty sure this is is old code. Check
PLAYER_ACTIVE_SHIELD_COLOR = (116, 211, 255)
PLAYER_ACTIVE_SHIELD_DURATION_MS = 9000
PLAYER_ACTIVE_SHIELD_FADE_START_MS = 6000
PLAYER_ACTIVE_SHIELD_EXTRA_HITS = 2
MEGA_CHARGE_MAX_BLOCKS = 5
MEGA_RECHARGE_INTERVAL_MS = 1000
MEGA_RECHARGE_DELAY_MS = 1000
MEGA_SHIELD_MIN_LEVEL = 3
MEGA_FINAL_KILL_LEVEL = 5
POWER_UP_DURATION_MS = 5000
POWER_UP_WARNING_MS = 2000
MISSION_HINT_IMAGE_SIZE = 200
MISSION_BRIEFING_SCROLL_END_BUFFER_SECONDS = 8
MISSION_BRIEFING_FALLBACK_SCROLL_SECONDS = 120
MAX_LIFE_POWER_UPS_PER_MISSION = 4
POWER_UP_MIN_INTERVAL_MS = 18000
POWER_UP_MAX_INTERVAL_MS = 32000
POWER_UP_POD_EXCLUSION_RADIUS = POD_IMAGE_SIZE // 2 + 70
POWER_UP_COLOR = (88, 214, 141)
SHIELD_POWER_UP_COLOR = (116, 211, 255)
BG_MUSIC_VOLUME = 0.35
BG_MUSIC_FADE_IN_MS = 1800
BG_MUSIC_FADE_OUT_MS = 700
STAR_COUNT = 150
STAR_DRIFT_SPEED = 10
SPECIAL_KEY_LABELS = {
    pygame.K_SPACE: "space",
    pygame.K_RETURN: "enter",
    pygame.K_BACKSPACE: "backspace",
    pygame.K_ESCAPE: "escape",
    pygame.K_TAB: "tab",
    pygame.K_CAPSLOCK: "caps lock",
    pygame.K_LSHIFT: "shift",
    pygame.K_RSHIFT: "shift",
    pygame.K_LCTRL: "control",
    pygame.K_RCTRL: "control",
    pygame.K_LALT: "alt",
    pygame.K_RALT: "alt",
}


@dataclass
class Drone:
    pos: pygame.Vector2
    letter: str
    hp: int
    max_hp: int
    radius: int
    speed: float
    is_mega: bool = False
    is_boss_shot: bool = False
    next_shot_time: int = 0
    rotation: float = 0
    incoming_damage: int = 0
    level_value: float = 1.0
    target_pos: pygame.Vector2 | None = None
    is_drifting: bool = False
    strafe_axis: pygame.Vector2 | None = None
    strafe_direction: int = 1
    strafe_offset: float = 0


@dataclass
class Bullet:
    pos: pygame.Vector2
    vel: pygame.Vector2
    target: Drone | None
    next_trail_time: int = 0
    rotation: float = 0


@dataclass
class MegaShot:
    pos: pygame.Vector2
    vel: pygame.Vector2
    charge_level: int
    target: object | None
    radius: int = 10
    rotation: float = 0
    next_trail_time: int = 0


@dataclass
class DefenseDrone:
    angle: float
    next_fire_time: int = 0
    active: bool = True
    last_shot_key: str | None = None
    last_shot_grace_until: int = 0


@dataclass
class DefenseShot:
    pos: pygame.Vector2
    vel: pygame.Vector2
    target: Drone | None
    next_trail_time: int = 0


@dataclass
class PendingShot:
    target: object | None
    damage: int
    created_at: int
    mega_charge_level: int = 0


@dataclass
class FinalBoss:
    pos: pygame.Vector2
    target_pos: pygame.Vector2
    letter: str
    hp: int = FINAL_BOSS_HP
    radius: int = FINAL_BOSS_RADIUS
    shield: int = FINAL_BOSS_SHIELD_MAX
    rotation: float = 0
    orbit_angle: float = 0
    orbit_radius: float = 0
    orbit_direction: int = 1
    is_orbiting: bool = False
    next_shot_time: int = 0
    next_orbit_switch_time: int = 0
    shield_down_since: int | None = None
    next_shield_recharge_time: int | None = None
    next_semi_boss_spawn_time: int = 0


@dataclass
class PowerUp:
    pos: pygame.Vector2
    letters: tuple[str, str]
    expires_at: int
    kind: str = "life"
    progress: int = 0


@dataclass
class Particle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    ttl: float


@dataclass
class ShotTrailParticle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    ttl: float
    max_ttl: float
    radius: float


@dataclass
class Star:
    x_ratio: float
    y_ratio: float
    radius: int
    alpha: int
    speed_scale: float


def play_audio(path):
    if not pygame.mixer.get_init():
        return
    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()
    except pygame.error:
        pass


def stop_audio():
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()


def toggle_fullscreen():
    screen = pygame.display.get_surface()
    if is_letterboxed_fullscreen() or screen.get_flags() & pygame.FULLSCREEN:
        return set_windowed_16_9(BASE_SCREEN_SIZE)
    return set_fullscreen_16_9()


def enforce_min_window_size(screen):
    return enforce_16_9_window(screen)


def load_sound(path, volume=1.0):
    if not pygame.mixer.get_init():
        return None
    try:
        sound = pygame.mixer.Sound(str(path))
        sound.set_volume(volume)
        return sound
    except pygame.error:
        return None


def play_sound(sound):
    if sound is not None:
        sound.play()


def play_looping_sound(sound, fade_ms=0):
    if sound is None:
        return None
    return sound.play(loops=-1, fade_ms=fade_ms)


def stop_looping_sound(channel, fade_ms=0):
    if channel is None:
        return
    if fade_ms:
        channel.fadeout(fade_ms)
    else:
        channel.stop()


def load_image(path):
    try:
        return pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        return None


def load_pod_variant_image(pod_dir, base_name, color_name=None, fallback_name=None):
    fallback_name = fallback_name or f"{base_name}.png"
    if color_name:
        image = load_image(pod_dir / f"{base_name}_{color_name}.png")
        if image is not None:
            return image
    return load_image(pod_dir / fallback_name)


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def load_json_object(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def audio_duration_ms(path):
    if not pygame.mixer.get_init():
        return 0
    try:
        return int(pygame.mixer.Sound(str(path)).get_length() * 1000)
    except pygame.error:
        return 0


def wrap_text(text, font, max_width):
    lines = []
    for paragraph in text.splitlines():
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


def draw_wrapped_text(surface, text, font, color, rect, line_spacing=6):
    y = rect.y
    line_height = font.get_linesize() + line_spacing
    max_lines = max(1, rect.height // line_height)
    lines = wrap_text(text, font, rect.width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            while lines[-1] and font.size(lines[-1] + "...")[0] > rect.width:
                lines[-1] = lines[-1][:-1].rstrip()
            lines[-1] = lines[-1] + "..."
    for line in lines:
        surface.blit(font.render(line, True, color), (rect.x, y))
        y += line_height


def draw_wrapped_centered_text(surface, text, font, color, rect, line_spacing=6):
    y = rect.y
    line_height = font.get_linesize() + line_spacing
    max_lines = max(1, rect.height // line_height)
    lines = wrap_text(text, font, rect.width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            while lines[-1] and font.size(lines[-1] + "...")[0] > rect.width:
                lines[-1] = lines[-1][:-1].rstrip()
            lines[-1] = lines[-1] + "..."
    for line in lines:
        line_surface = font.render(line, True, color)
        surface.blit(line_surface, line_surface.get_rect(center=(rect.centerx, y + line_surface.get_height() / 2)))
        y += line_height


def draw_scrollable_text(surface, text, font, color, rect, scroll_y, line_spacing=6):
    line_height = font.get_height() + line_spacing
    lines = wrap_text(text, font, rect.width - 44)
    max_scroll = max(0, len(lines) * line_height - rect.height + 44)
    scroll_y = max(0, min(scroll_y, max_scroll))
    pygame.draw.rect(surface, (8, 15, 30), rect, border_radius=6)
    pygame.draw.rect(surface, (42, 58, 92), rect, 1, border_radius=6)
    clip = surface.get_clip()
    surface.set_clip(rect.inflate(-20, -20))
    y = rect.y + 16 - scroll_y
    for line in lines:
        if rect.y - line_height <= y <= rect.bottom:
            render_inline_text(surface, line, font, color, (rect.x + 18, y))
        y += line_height
    surface.set_clip(clip)
    if max_scroll:
        track_rect = pygame.Rect(rect.right - 8, rect.y + 6, 4, rect.height - 12)
        pygame.draw.rect(surface, (30, 42, 68), track_rect, border_radius=2)
        visible_height = max(1, rect.height - 44)
        content_height = max(visible_height, len(lines) * line_height)
        thumb_height = max(18, int(track_rect.height * visible_height / content_height))
        travel = max(1, track_rect.height - thumb_height)
        thumb_y = track_rect.y + int(travel * scroll_y / max_scroll)
        pygame.draw.rect(surface, ACCENT, (track_rect.x, thumb_y, track_rect.width, thumb_height), border_radius=2)
    return max_scroll


def event_to_lesson_key(event):
    if event.key in SPECIAL_KEY_LABELS:
        return SPECIAL_KEY_LABELS[event.key]
    event_unicode = getattr(event, "unicode", "")
    if event_unicode and event_unicode.strip():
        return event_unicode.lower()
    return None


def screen_center(screen):
    width, height = screen.get_size()
    return pygame.Vector2(width / 2, height / 2)


def difficulty_tier(destroyed):
    return int(destroyed) // KILLS_PER_DIFFICULTY_TIER


def lesson_drone_target(lesson_number):
    if lesson_number <= 2:
        return 30
    if lesson_number <= 4:
        return 40
    return 46 + lesson_number


def mini_bosses_enabled(lesson_number):
    return lesson_number >= 3


def mega_shot_enabled(lesson_number):
    return lesson_number >= 5


def player_mega_shot_available(player, lesson_number):
    if mega_shot_enabled(lesson_number):
        return True
    if not isinstance(player, dict):
        return False
    completed = set(player.get("completed_lessons", []))
    return all(number in completed for number in range(1, 5))


def final_boss_enabled(lesson_number):
    return lesson_number >= 5


def mission_target_keys(valid_keys, lesson_number, mega_available=False):
    return tuple(
        key
        for key in valid_keys
        if not ((mega_shot_enabled(lesson_number) or mega_available) and key == "space")
    )


def player_shield_enabled(lesson_number):
    return lesson_number >= PLAYER_SHIELD_START_LESSON


def player_shield_available(player, lesson_number):
    if player_shield_enabled(lesson_number):
        return True
    if not isinstance(player, dict):
        return False
    completed = set(player.get("completed_lessons", []))
    return all(number in completed for number in range(1, PLAYER_SHIELD_START_LESSON))


def player_upgrade_ids(player):
    if not isinstance(player, dict):
        return set()
    pod = player.get("pod", {})
    upgrades = pod.get("upgrades", []) if isinstance(pod, dict) else []
    ids = set()
    for upgrade in upgrades:
        if isinstance(upgrade, str):
            ids.add(upgrade)
        elif isinstance(upgrade, dict) and isinstance(upgrade.get("id"), str):
            ids.add(upgrade["id"])
    return ids


def player_upgrade_color(player, upgrade_id):
    if not isinstance(player, dict):
        return None
    pod = player.get("pod", {})
    upgrades = pod.get("upgrades", []) if isinstance(pod, dict) else []
    for upgrade in reversed(upgrades):
        if isinstance(upgrade, dict) and upgrade.get("id") == upgrade_id:
            color = upgrade.get("color")
            if isinstance(color, str) and color.strip():
                return color.strip().lower().replace(" ", "_")
    return None


def player_shield_max_charges(player):
    max_charges = PLAYER_SHIELD_MAX_CHARGES
    upgrades = player_upgrade_ids(player)
    if "extra_shield_slot_1" in upgrades:
        max_charges += 1
    if "extra_shield_slot_2" in upgrades:
        max_charges += 1
    return max_charges


def player_defense_drone_count(player):
    upgrades = player_upgrade_ids(player)
    count = 0
    if "defense_drone" in upgrades:
        count += 1
    if "second_defense_drone" in upgrades:
        count += 1
    return count


def final_boss_projectile_count(lesson_number):
    return 3


def mini_boss_numbers_for_lesson(lesson_number, drone_target):
    if not mini_bosses_enabled(lesson_number):
        return set()
    return set(range(MINI_BOSS_INTERVAL, drone_target + 1, MINI_BOSS_INTERVAL))


def active_mini_boss_count(drones):
    return sum(1 for drone in drones if drone.is_mega)


def drone_rotation_radians_per_second(drone):
    pixels_per_rotation = MEGA_PIXELS_PER_ROTATION if drone.is_mega else DRONE_PIXELS_PER_ROTATION
    return math.tau * max(0, drone.speed) / pixels_per_rotation


def drone_counts_for_level(drone):
    return drone.level_value > 0


def active_level_value(drones):
    return sum(drone.level_value for drone in drones if drone_counts_for_level(drone))


def should_spawn_mission_drone(lesson_number, spawned_count, destroyed, drones, drone_target):
    return spawned_count < drone_target or destroyed + active_level_value(drones) < drone_target


def spawn_rate_multiplier(lesson_number):
    if lesson_number > 30:
        return 1.75
    if lesson_number > 25:
        return 1.60
    if lesson_number > 20:
        return 1.50
    if lesson_number > 15:
        return 1.45
    if lesson_number > 10:
        return 1.35
    if lesson_number > 5:
        return 1.25
    return 1.0


def random_spawn_interval(lesson_number):
    drones_per_second = random.uniform(MIN_DRONE_SPAWN_RATE, MAX_DRONE_SPAWN_RATE)
    drones_per_second *= spawn_rate_multiplier(lesson_number)
    return int(1000 / drones_per_second)


def drone_hp():
    roll = random.random()
    if roll < 0.12:
        return 3
    if roll < 0.38:
        return 2
    return 1


def drone_radius_for_hp(hp):
    if hp >= 3:
        return 30
    if hp == 2:
        return 27
    return 22


def spawn_position(screen):
    width, height = screen.get_size()
    side = random.choice(("top", "right", "bottom", "left"))
    margin = 60
    if side == "top":
        return pygame.Vector2(random.randint(0, width), -margin)
    elif side == "right":
        return pygame.Vector2(width + margin, random.randint(0, height))
    elif side == "bottom":
        return pygame.Vector2(random.randint(0, width), height + margin)
    return pygame.Vector2(-margin, random.randint(0, height))


def lesson_focus_keys(lesson_number, valid_keys):
    targetable_keys = tuple(valid_keys)
    focus_keys = [key for key in lesson_new_keys(lesson_number) if key in targetable_keys]
    return tuple(focus_keys[:2] or targetable_keys)


def random_spawn_key(valid_keys, blocked_key=None, preferred_keys=(), preferred_weight=0.0):
    available_keys = [key for key in valid_keys if key != blocked_key]
    weighted_keys = [key for key in preferred_keys if key in available_keys]
    if weighted_keys and random.random() < preferred_weight:
        return random.choice(weighted_keys)
    return random.choice(available_keys or list(valid_keys))


def spawn_drone(drones, screen, destroyed, valid_keys, is_mega=False, spawn_keys=None):
    pos = spawn_position(screen)
    hp = drone_hp()
    speed_bonus = difficulty_tier(destroyed) * DRONE_SPEED_BONUS_PER_TIER
    target_pos = None
    strafe_axis = None
    if is_mega:
        hp = MEGA_DRONE_HP
        center = screen_center(screen)
        width, height = screen.get_size()
        approach_distance = min(width, height) * MINI_BOSS_CENTER_DISTANCE_SCALE
        from_center = pos - center
        if from_center.length_squared() == 0:
            from_center = pygame.Vector2(0, -1)
        target_pos = center + from_center.normalize() * approach_distance
        approach = center - target_pos
        if approach.length_squared() == 0:
            strafe_axis = pygame.Vector2(1, 0)
        else:
            approach = approach.normalize()
            strafe_axis = pygame.Vector2(-approach.y, approach.x)
    drone = Drone(
        pos=pos,
        letter=random_spawn_key(spawn_keys or valid_keys),
        hp=hp,
        max_hp=hp,
        radius=MEGA_DRONE_RADIUS if is_mega else drone_radius_for_hp(hp),
        speed=(random.uniform(38, 52) if is_mega else random.uniform(50, 75)) + speed_bonus,
        is_mega=is_mega,
        target_pos=target_pos,
        strafe_axis=strafe_axis,
        strafe_direction=random.choice((-1, 1)),
    )
    drones.append(drone)
    return drone


def spawn_next_drone(drones, screen, destroyed, valid_keys, spawned_count, mini_boss_numbers, focus_keys=()):
    spawned_count += 1
    spawn_keys = focus_keys if spawned_count <= NEW_KEY_ONLY_DRONES_PER_MISSION else valid_keys
    drone = spawn_drone(
        drones,
        screen,
        destroyed,
        valid_keys,
        is_mega=spawned_count in mini_boss_numbers,
        spawn_keys=spawn_keys,
    )
    return drone, spawned_count


def split_regular_drone(drones, drone):
    if drone.is_mega or drone.max_hp <= 1 or drone.hp < 1:
        return
    child_hp = max(1, drone.hp)
    spread = max(18, drone.radius * 0.7)
    for offset in (-spread, spread):
        child = Drone(
            pos=drone.pos + pygame.Vector2(offset, random.uniform(-spread, spread)),
            letter=drone.letter,
            hp=child_hp,
            max_hp=child_hp,
            radius=drone_radius_for_hp(child_hp),
            speed=drone.speed * random.uniform(0.96, 1.08),
            level_value=drone.level_value / 2,
        )
        drones.append(child)


def next_power_up_time(now):
    return now + random.randint(POWER_UP_MIN_INTERVAL_MS, POWER_UP_MAX_INTERVAL_MS)


def point_in_blocked_power_up_area(pos, blocked_center, blocked_radius, blocked_rects):
    if blocked_center is not None and pos.distance_to(blocked_center) < blocked_radius:
        return True
    return any(rect.collidepoint(pos.x, pos.y) for rect in blocked_rects)


def spawn_power_up(
    screen,
    valid_keys,
    now,
    shield_enabled=False,
    shield_charges=0,
    max_shield_charges=PLAYER_SHIELD_MAX_CHARGES,
    life_enabled=True,
    blocked_center=None,
    blocked_radius=POWER_UP_POD_EXCLUSION_RADIUS,
    blocked_rects=(),
):
    width, height = screen.get_size()
    margin = 90
    power_up_keys = [key for key in valid_keys if len(key) == 1 and key.isalpha()] or list(valid_keys)
    keys = random.choices(power_up_keys, k=2)
    can_spawn_shield = shield_enabled and shield_charges < max_shield_charges
    if can_spawn_shield and (not life_enabled or random.random() < 0.5):
        kind = "shield"
    elif life_enabled:
        kind = "life"
    else:
        return None
    pos = pygame.Vector2(
        random.randint(margin, max(margin, width - margin)),
        random.randint(margin, max(margin, height - margin)),
    )
    for _ in range(40):
        if not point_in_blocked_power_up_area(pos, blocked_center, blocked_radius, blocked_rects):
            break
        pos = pygame.Vector2(
            random.randint(margin, max(margin, width - margin)),
            random.randint(margin, max(margin, height - margin)),
        )
    return PowerUp(
        pos=pos,
        letters=(keys[0], keys[1]),
        expires_at=now + POWER_UP_DURATION_MS,
        kind=kind,
    )


def spawn_final_boss_semi_boss(drones, final_boss, center, valid_keys, focus_keys=()):
    direction = center - final_boss.pos
    if direction.length_squared() == 0:
        direction = pygame.Vector2(1, 0)
    direction = direction.normalize()
    spawn_pos = final_boss.pos.copy()
    target_pos = final_boss.pos + direction * (final_boss.radius + MEGA_DRONE_RADIUS * 2.4)
    strafe_axis = pygame.Vector2(-direction.y, direction.x)
    drone = Drone(
        pos=spawn_pos,
        letter=random_spawn_key(
            valid_keys,
            final_boss.letter,
            focus_keys,
            FINAL_BOSS_NEW_KEY_SPAWN_WEIGHT,
        ),
        hp=MEGA_DRONE_HP,
        max_hp=MEGA_DRONE_HP,
        radius=MEGA_DRONE_RADIUS,
        speed=random.uniform(38, 52),
        is_mega=True,
        target_pos=target_pos,
        strafe_axis=strafe_axis,
        strafe_direction=random.choice((-1, 1)),
        level_value=0,
    )
    drones.append(drone)
    return drone


def handle_power_up_key(power_up, pressed_key):
    if power_up is None:
        return None, False
    if pressed_key == power_up.letters[power_up.progress]:
        power_up.progress += 1
        return power_up.kind if power_up.progress >= len(power_up.letters) else None, True
    power_up.progress = 0
    return None, False


def can_target_drone(drone):
    if drone.is_mega:
        return drone.hp - drone.incoming_damage > 0
    return drone.incoming_damage == 0


def nearest_drone_for_key(drones, key, center):
    matches = [drone for drone in drones if drone.letter == key and can_target_drone(drone)]
    if not matches:
        return None
    return min(matches, key=lambda drone: drone.pos.distance_squared_to(center))


def angle_delta(current, target):
    return (target - current + math.pi) % math.tau - math.pi


def rotate_toward_angle(current, target, max_step):
    delta = angle_delta(current, target)
    if abs(delta) <= max_step:
        return target
    return current + max_step * (1 if delta > 0 else -1)


def target_is_available(target, drones, final_boss):
    if isinstance(target, Drone):
        return target in drones
    return isinstance(target, FinalBoss) and target is final_boss


def target_angle(target, center):
    direction = target.pos - center
    if direction.length_squared() == 0:
        direction = pygame.Vector2(0, -1)
    else:
        direction = direction.normalize()
    return math.atan2(direction.y, direction.x)


def queue_shot_at(drones, pending_shots, key, center, now):
    target = nearest_drone_for_key(drones, key, center)
    if target is None:
        return False
    target.incoming_damage += 1
    pending_shots.append(PendingShot(target=target, damage=1, created_at=now))
    return True


def mega_damage(charge_level):
    level = max(1, min(MEGA_CHARGE_MAX_BLOCKS, charge_level))
    return 2 ** (level - 1)


def mega_shot_speed(charge_level):
    level = max(1, min(MEGA_CHARGE_MAX_BLOCKS, charge_level))
    speed_multipliers = {
        2: 1.10,
        3: 1.20,
        4: 1.40,
        5: 1.80,
    }
    return 820 * speed_multipliers.get(level, 1.0)


def mega_target(drones, final_boss, key, center):
    if final_boss is not None and key == final_boss.letter:
        return final_boss
    return nearest_drone_for_key(drones, key, center)


def queue_mega_shot(drones, final_boss, pending_shots, key, center, charge_level, now):
    target = mega_target(drones, final_boss, key, center)
    if target is None:
        return False
    charge_level = max(1, min(MEGA_CHARGE_MAX_BLOCKS, charge_level))
    damage = mega_damage(charge_level)
    if isinstance(target, Drone):
        target.incoming_damage += damage
    pending_shots.append(PendingShot(target=target, damage=damage, created_at=now, mega_charge_level=charge_level))
    return True


def release_pending_shot(pending_shot):
    if isinstance(pending_shot.target, Drone):
        pending_shot.target.incoming_damage = max(
            0,
            pending_shot.target.incoming_damage - pending_shot.damage,
        )


def fire_pending_shot(pending_shot, bullets, mega_shots, center):
    target = pending_shot.target
    direction = target.pos - center
    if direction.length_squared() == 0:
        direction = pygame.Vector2(0, -1)
    else:
        direction = direction.normalize()

    if pending_shot.mega_charge_level:
        charge_level = pending_shot.mega_charge_level
        mega_shots.append(
            MegaShot(
                pos=center + direction * 34,
                vel=direction * mega_shot_speed(charge_level),
                charge_level=charge_level,
                target=target,
                radius=8 + charge_level * 2,
            )
        )
    else:
        bullets.append(Bullet(center + direction * 28, direction * 560, target))

    return math.atan2(direction.y, direction.x)


def bullet_is_offscreen(bullet, screen):
    width, height = screen.get_size()
    margin = 80
    return (
        bullet.pos.x < -margin
        or bullet.pos.x > width + margin
        or bullet.pos.y < -margin
        or bullet.pos.y > height + margin
    )


def drone_color(drone):
    if drone.is_mega:
        return MEGA_DRONE_COLOR
    if drone.max_hp >= 3:
        return THREE_SHOT_DRONE_COLOR
    if drone.max_hp == 2:
        return TWO_SHOT_DRONE_COLOR
    return ONE_SHOT_DRONE_COLOR


def drone_image(drone, drone_images):
    if drone.is_mega:
        return drone_images.get("semi_boss")
    if drone.is_boss_shot:
        return drone_images.get("yellow")
    if drone.max_hp >= 3:
        return drone_images.get("red")
    if drone.max_hp == 2:
        return drone_images.get("orange")
    return drone_images.get("yellow")


def scaled_drone_image(drone, drone_images, image_cache):
    image = drone_image(drone, drone_images)
    if image is None:
        return None
    if drone.is_boss_shot:
        size = BOSS_SHOT_IMAGE_RADIUS * 2
    elif drone.is_mega:
        size = drone.radius * 2
    else:
        size = max(1, int(drone.radius * 2 * NORMAL_DRONE_IMAGE_SCALE))
    cache_key = (id(image), size)
    if cache_key not in image_cache:
        image_cache[cache_key] = pygame.transform.smoothscale(image, (size, size))
    return image_cache[cache_key]


def rotated_drone_image(drone, drone_images, image_cache):
    image = scaled_drone_image(drone, drone_images, image_cache)
    if image is None:
        return None
    return pygame.transform.rotate(image, -math.degrees(drone.rotation))


def pentagon_points(center, radius, rotation=-math.pi / 2):
    return [
        (
            center.x + math.cos(rotation + index * math.tau / 5) * radius,
            center.y + math.sin(rotation + index * math.tau / 5) * radius,
        )
        for index in range(5)
    ]


def polygon_points(center, radius, sides, rotation=-math.pi / 2):
    return [
        (
            center.x + math.cos(rotation + index * math.tau / sides) * radius,
            center.y + math.sin(rotation + index * math.tau / sides) * radius,
        )
        for index in range(sides)
    ]


def spawn_final_boss(screen, now, valid_keys, player_center, focus_keys=()):
    width, height = screen.get_size()
    spawn_pos = pygame.Vector2(-FINAL_BOSS_RADIUS - 28, height / 2)
    target_x = spawn_pos.x + (player_center.x - spawn_pos.x) * FINAL_BOSS_ENTRY_PROGRESS
    target_pos = pygame.Vector2(target_x, height / 2)
    return FinalBoss(
        pos=spawn_pos,
        target_pos=target_pos,
        letter=random.choice(focus_keys or valid_keys),
        orbit_angle=0,
        orbit_radius=0,
        orbit_direction=random.choice((-1, 1)),
        next_shot_time=0,
        next_orbit_switch_time=0,
        next_semi_boss_spawn_time=now + FINAL_BOSS_SEMI_BOSS_FIRST_SPAWN_MS,
    )


def update_final_boss_movement(final_boss, screen, dt, now):
    width, height = screen.get_size()
    if not final_boss.is_orbiting:
        travel = final_boss.target_pos - final_boss.pos
        distance = travel.length()
        if distance <= FINAL_BOSS_APPROACH_SPEED * dt:
            final_boss.pos = final_boss.target_pos.copy()
            final_boss.is_orbiting = True
            final_boss.orbit_angle = 0 if final_boss.orbit_direction > 0 else math.pi
        elif distance > 0:
            final_boss.pos += travel.normalize() * FINAL_BOSS_APPROACH_SPEED * dt
        return

    final_boss.orbit_angle += final_boss.orbit_direction * math.tau * dt / FINAL_BOSS_ORBIT_SECONDS
    min_y = height * FINAL_BOSS_VERTICAL_MIN_RATIO + final_boss.radius
    max_y = height * FINAL_BOSS_VERTICAL_MAX_RATIO - final_boss.radius
    center_y = (min_y + max_y) / 2
    amplitude = max(0, (max_y - min_y) / 2)
    final_boss.pos = pygame.Vector2(
        final_boss.target_pos.x,
        center_y + math.sin(final_boss.orbit_angle) * amplitude,
    )


def update_final_boss_shield(final_boss, now):
    return


def fire_mega_drone(drones, boss, center, valid_keys, blocked_key=None, focus_keys=()):
    direction = center - boss.pos
    if direction.length_squared() == 0:
        direction = pygame.Vector2(0, 1)
    direction = direction.normalize()
    drones.append(
        Drone(
            pos=boss.pos + direction * (boss.radius + BOSS_SHOT_IMAGE_RADIUS + 4),
            letter=random_spawn_key(
                valid_keys,
                blocked_key,
                focus_keys,
                FINAL_BOSS_NEW_KEY_SPAWN_WEIGHT,
            ),
            hp=1,
            max_hp=1,
            radius=BOSS_SHOT_IMAGE_RADIUS,
            speed=BOSS_SHOT_SPEED,
            is_boss_shot=True,
            level_value=0,
        )
    )


def fire_final_boss_drones(drones, final_boss, center, valid_keys, count=1, focus_keys=()):
    direction = center - final_boss.pos
    if direction.length_squared() == 0:
        direction = pygame.Vector2(0, 1)
    direction = direction.normalize()
    side = pygame.Vector2(-direction.y, direction.x)
    spread_step = math.radians(24)
    start_angle = -spread_step * (count - 1) / 2
    for index in range(count):
        shot_direction = direction.rotate_rad(start_angle + spread_step * index)
        side_offset = side * ((index - (count - 1) / 2) * BOSS_SHOT_IMAGE_RADIUS * 1.35)
        drones.append(
            Drone(
                pos=(
                    final_boss.pos
                    + shot_direction * (final_boss.radius + BOSS_SHOT_IMAGE_RADIUS + 6)
                    + side_offset
                ),
                letter=random_spawn_key(
                    valid_keys,
                    final_boss.letter,
                    focus_keys,
                    FINAL_BOSS_NEW_KEY_SPAWN_WEIGHT,
                ),
                hp=1,
                max_hp=1,
                radius=BOSS_SHOT_IMAGE_RADIUS,
                speed=FINAL_BOSS_SHOT_SPEED,
                is_boss_shot=True,
                level_value=0,
            )
        )


def update_drone_position(drone, center, dt):
    if drone.is_mega and drone.target_pos is not None:
        if not drone.is_drifting:
            travel = drone.target_pos - drone.pos
            distance = travel.length()
            if distance <= drone.speed * dt:
                drone.pos = drone.target_pos.copy()
                drone.is_drifting = True
            elif distance > 0:
                drone.pos += travel.normalize() * drone.speed * dt
            return

        axis = drone.strafe_axis or pygame.Vector2(1, 0)
        step = drone.speed * MINI_BOSS_STRAFE_SPEED_SCALE * dt * drone.strafe_direction
        drone.pos += axis * step
        drone.strafe_offset += step
        if abs(drone.strafe_offset) >= MINI_BOSS_STRAFE_RANGE:
            drone.strafe_direction *= -1
            drone.strafe_offset = max(-MINI_BOSS_STRAFE_RANGE, min(MINI_BOSS_STRAFE_RANGE, drone.strafe_offset))
        return

    direction = center - drone.pos
    if direction.length_squared() > 0:
        drone.pos += direction.normalize() * drone.speed * dt


def explode(particles, pos, count=18):
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(70, 210)
        particles.append(
            Particle(
                pos=pos.copy(),
                vel=pygame.Vector2(math.cos(angle), math.sin(angle)) * speed,
                ttl=random.uniform(0.55, 1.0),
            )
        )


def add_shot_trail(shot_trails, shot, now, radius_scale=1.0):
    if now < shot.next_trail_time or shot.vel.length_squared() == 0:
        return

    shot_radius = getattr(shot, "radius", 7)
    trail_scale = max(1.0, shot_radius / 7)
    direction = shot.vel.normalize()
    origin = shot.pos
    side = pygame.Vector2(-direction.y, direction.x)
    for _ in range(max(4, int(4 * trail_scale))):
        drift = -direction * random.uniform(14, 32) * trail_scale + side * random.uniform(-15, 15) * trail_scale
        ttl = random.uniform(0.28, 0.48)
        shot_trails.append(
            ShotTrailParticle(
                pos=origin + side * random.uniform(-5, 5) * trail_scale,
                vel=drift,
                ttl=ttl,
                max_ttl=ttl,
                radius=random.uniform(2.0, 4.0) * trail_scale * radius_scale,
            )
        )
    shot.next_trail_time = now + max(6, int(SHOT_TRAIL_INTERVAL_MS / min(2.0, trail_scale)))


def draw_shot_trails(screen, shot_trails):
    for particle in shot_trails:
        alpha_scale = max(0, min(1, particle.ttl / particle.max_ttl))
        radius = max(1, int(particle.radius * alpha_scale))
        size = radius * 2 + 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        alpha = int(135 * alpha_scale)
        pygame.draw.circle(surface, (*SHOT_TRAIL_COLOR, alpha), (size // 2, size // 2), radius)
        screen.blit(surface, surface.get_rect(center=particle.pos))


def draw_bullet(screen, bullet, shot_image=None):
    if shot_image is not None:
        image = shot_image
        angle = math.degrees(bullet.rotation)
        if bullet.vel.length_squared() > 0:
            angle += math.degrees(math.atan2(-bullet.vel.y, bullet.vel.x))
        image = pygame.transform.rotozoom(shot_image, angle, 1.0)
        screen.blit(image, image.get_rect(center=bullet.pos))
    else:
        pygame.draw.circle(screen, BULLET_COLOR, bullet.pos, 5)


def draw_mega_shot(screen, mega_shot, shot_image=None):
    if shot_image is not None:
        angle = math.degrees(mega_shot.rotation)
        if mega_shot.vel.length_squared() > 0:
            angle += math.degrees(math.atan2(-mega_shot.vel.y, mega_shot.vel.x))
        scale = max(1.0, (mega_shot.radius * 2) / SHOT_IMAGE_SIZE)
        image = pygame.transform.rotozoom(shot_image, angle, scale)
        screen.blit(image, image.get_rect(center=mega_shot.pos))
    else:
        pygame.draw.circle(screen, MEGA_SHOT_COLOR, mega_shot.pos, mega_shot.radius)
        pygame.draw.circle(screen, (255, 255, 255), mega_shot.pos, mega_shot.radius, 2)


def defense_drone_position(player_center, defense_drone):
    return player_center + pygame.Vector2(
        math.cos(defense_drone.angle),
        math.sin(defense_drone.angle),
    ) * DEFENSE_DRONE_ORBIT_RADIUS


def draw_defense_drone(screen, defense_drone, player_center, defense_drone_image=None):
    if not defense_drone.active:
        return
    pos = defense_drone_position(player_center, defense_drone)
    rotation = -defense_drone.angle * 4 + math.pi / 2
    if defense_drone_image is not None:
        rotated_image = pygame.transform.rotozoom(defense_drone_image, math.degrees(rotation), 1.0)
        screen.blit(rotated_image, rotated_image.get_rect(center=pos))
        return
    points = polygon_points(pos, DEFENSE_DRONE_RADIUS, 3, rotation)
    pygame.draw.polygon(screen, DEFENSE_DRONE_COLOR, points)
    pygame.draw.polygon(screen, (224, 228, 232), points, 2)


def draw_defense_shot(screen, shot):
    pygame.draw.circle(screen, BULLET_COLOR, shot.pos, DEFENSE_DRONE_SHOT_RADIUS)


def draw_ship(screen, turret_angle, pod_rotation, turret_image=None, pod_image=None, center=None):
    if center is None:
        center = screen_center(screen)
    if pod_image is not None:
        rotated_pod = pygame.transform.rotozoom(pod_image, -math.degrees(pod_rotation), 1.0)
        screen.blit(rotated_pod, rotated_pod.get_rect(center=center))
    else:
        rotated_points = []
        for x, y in ((0, -30), (-25, 23), (25, 23)):
            point = pygame.Vector2(x, y).rotate_rad(pod_rotation) + center
            rotated_points.append((point.x, point.y))
        points = [
            rotated_points[0],
            rotated_points[1],
            rotated_points[2],
        ]
        pygame.draw.polygon(screen, SHIP_COLOR, points)
        pygame.draw.polygon(screen, (225, 243, 255), points, 2)
    if turret_image is not None:
        rotated = pygame.transform.rotozoom(turret_image, -math.degrees(turret_angle) - 90, 1.0)
        screen.blit(rotated, rotated.get_rect(center=center))
    else:
        barrel_direction = pygame.Vector2(math.cos(turret_angle), math.sin(turret_angle))
        turret_base = center + barrel_direction * 2
        turret_tip = center + barrel_direction * 36
        pygame.draw.line(screen, ACCENT, turret_base, turret_tip, 8)
        pygame.draw.circle(screen, (225, 243, 255), turret_base, 11)
        pygame.draw.circle(screen, ACCENT, turret_base, 7)


def power_up_alpha(power_up, now):
    time_left = power_up.expires_at - now
    if time_left > POWER_UP_WARNING_MS:
        return 255
    phase = max(0, time_left) / POWER_UP_WARNING_MS
    blink = (math.sin(now / 95) + 1) / 2
    return int(95 + 160 * phase * blink)


def draw_power_up(screen, power_up, now):
    if power_up is None:
        return
    size = 74
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    alpha = power_up_alpha(power_up, now)
    color = SHIELD_POWER_UP_COLOR if power_up.kind == "shield" else POWER_UP_COLOR
    edge_color = (226, 255, 235) if power_up.kind == "life" else (225, 246, 255)
    center = pygame.Vector2(size / 2, size / 2)
    if power_up.kind == "shield":
        shape_rect = pygame.Rect(0, 0, 56, 56)
        shape_rect.center = center
        pygame.draw.rect(surface, color, shape_rect, border_radius=4)
        pygame.draw.rect(surface, edge_color, shape_rect, 3, border_radius=4)
    else:
        points = (
            (center.x, 7),
            (size - 7, center.y),
            (center.x, size - 7),
            (7, center.y),
        )
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, edge_color, points, 3)

    label_text = " ".join(display_key(key) for key in power_up.letters)
    label_font = pygame.font.SysFont("arial", 24, bold=True)
    render_inline_center(surface, label_text, label_font, (5, 24, 12), center)

    if power_up.progress:
        pip_rect = pygame.Rect(12, size - 14, 24, 4)
        pygame.draw.rect(surface, (5, 24, 12), pip_rect)
    surface.set_alpha(alpha)
    screen.blit(surface, surface.get_rect(center=power_up.pos))


def draw_final_boss(screen, final_boss, final_boss_image=None):
    if final_boss is None:
        return
    if final_boss.shield > 0:
        shield_alpha = 55 + final_boss.shield * 55
        shield_surface = pygame.Surface((final_boss.radius * 3, final_boss.radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(
            shield_surface,
            (*FINAL_BOSS_SHIELD_COLOR, shield_alpha),
            (final_boss.radius * 3 // 2, final_boss.radius * 3 // 2),
            final_boss.radius + 18,
            6,
        )
        screen.blit(
            shield_surface,
            shield_surface.get_rect(center=final_boss.pos),
        )

    if final_boss_image is not None:
        rotated_image = pygame.transform.rotate(final_boss_image, -math.degrees(final_boss.rotation))
        screen.blit(rotated_image, rotated_image.get_rect(center=final_boss.pos))
    else:
        points = polygon_points(final_boss.pos, final_boss.radius, 6, final_boss.rotation - math.pi / 2)
        pygame.draw.polygon(screen, FINAL_BOSS_COLOR, points)
        pygame.draw.polygon(screen, (229, 214, 255), points, 3)
    label_font = pygame.font.SysFont("arial", 46, bold=True)
    render_key_label(screen, final_boss.letter, label_font, (8, 10, 18), final_boss.pos, final_boss.radius * 1.25)


def draw_mega_bar(screen, font, mega_text, charge_blocks=0, active=False, center_x=None):
    if not mega_text:
        return
    width, _ = screen.get_size()
    if center_x is None:
        center_x = width / 2
    block_size = 22
    gap = 5
    bar_width = MEGA_CHARGE_MAX_BLOCKS * block_size + (MEGA_CHARGE_MAX_BLOCKS - 1) * gap
    bar_rect = pygame.Rect(0, 0, bar_width, block_size)
    bar_rect.center = (center_x, 51)

    frame_color = (158, 93, 98) if active else (82, 58, 62)
    empty_color = (43, 28, 34)
    fill_color = (166, 82, 90) if active else (92, 70, 74)

    for index in range(MEGA_CHARGE_MAX_BLOCKS):
        block_rect = pygame.Rect(
            bar_rect.x + index * (block_size + gap),
            bar_rect.y,
            block_size,
            block_size,
        )
        pygame.draw.rect(screen, empty_color, block_rect, border_radius=4)
        pygame.draw.rect(screen, frame_color, block_rect, 2, border_radius=4)
        if index < charge_blocks:
            pygame.draw.rect(screen, fill_color, block_rect.inflate(-6, -6), border_radius=3)

    text_color = (218, 136, 142) if active else (118, 90, 96)
    text_surface = font.render(mega_text, True, text_color)
    screen.blit(text_surface, text_surface.get_rect(center=(center_x, 28)))


def draw_player_shield_bar(screen, font, charges, enabled, y_offset=0, max_charges=PLAYER_SHIELD_MAX_CHARGES, center_x=None):
    if not enabled:
        return
    width, _ = screen.get_size()
    if center_x is None:
        center_x = width / 2
    block_size = 22
    gap = 5
    max_charges = max(1, max_charges)
    bar_width = max_charges * block_size + (max_charges - 1) * gap
    bar_rect = pygame.Rect(0, 0, bar_width, block_size)
    bar_rect.center = (center_x, 51 + y_offset)

    frame_color = (70, 154, 190)
    empty_color = (22, 34, 48)
    for index in range(max_charges):
        block_rect = pygame.Rect(
            bar_rect.x + index * (block_size + gap),
            bar_rect.y,
            block_size,
            block_size,
        )
        pygame.draw.rect(screen, empty_color, block_rect, border_radius=4)
        pygame.draw.rect(screen, frame_color, block_rect, 2, border_radius=4)
        if index < charges:
            shield_surface = pygame.Surface((block_size, block_size), pygame.SRCALPHA)
            pygame.draw.circle(
                shield_surface,
                (*FINAL_BOSS_SHIELD_COLOR, 160),
                (block_size // 2, block_size // 2),
                block_size // 2 - 3,
                4,
            )
            screen.blit(shield_surface, block_rect)

    text_surface = font.render("Shield", True, FINAL_BOSS_SHIELD_COLOR if charges else (80, 95, 110))
    if not charges:
        text_surface.set_alpha(155)
    screen.blit(text_surface, text_surface.get_rect(center=(center_x, 28 + y_offset)))


def draw_active_player_shield(screen, center, expires_at, hits_remaining, now):
    if hits_remaining <= 0 or now >= expires_at:
        return

    fade_start_at = expires_at - (PLAYER_ACTIVE_SHIELD_DURATION_MS - PLAYER_ACTIVE_SHIELD_FADE_START_MS)
    if now <= fade_start_at:
        alpha = 175
    else:
        fade_duration = max(1, expires_at - fade_start_at)
        alpha = int(175 * max(0, expires_at - now) / fade_duration)

    radius = POD_IMAGE_SIZE // 2 + 9
    size = radius * 2 + 8
    shield_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(
        shield_surface,
        (*PLAYER_ACTIVE_SHIELD_COLOR, alpha),
        (size // 2, size // 2),
        radius,
        3,
    )
    screen.blit(shield_surface, shield_surface.get_rect(center=center))


def draw_hud(screen, font, destroyed, drone_target, score, lives):
    width, _ = screen.get_size()
    left = f"Drones destroyed: {int(destroyed)}/{drone_target}"
    right = f"Score: {score}"
    life = f"Lives: {lives}"
    screen.blit(font.render(left, True, TEXT_COLOR), (22, 18))
    score_surface = font.render(right, True, TEXT_COLOR)
    screen.blit(score_surface, (width - score_surface.get_width() - 22, 18))
    life_surface = font.render(life, True, MUTED_TEXT)
    screen.blit(life_surface, (width - life_surface.get_width() - 22, 52))


def create_star_field(count=STAR_COUNT):
    return [
        Star(
            x_ratio=random.random(),
            y_ratio=random.random(),
            radius=1 if random.random() < 0.9 else 2,
            alpha=random.randint(48, 105),
            speed_scale=random.uniform(0.55, 1.35),
        )
        for _ in range(count)
    ]


def update_star_field(stars, dt):
    for star in stars:
        star.y_ratio = (star.y_ratio + STAR_DRIFT_SPEED * star.speed_scale * dt / BASE_SCREEN_SIZE[1]) % 1
        star.x_ratio = (star.x_ratio + STAR_DRIFT_SPEED * 0.18 * star.speed_scale * dt / BASE_SCREEN_SIZE[0]) % 1


def draw_star_field(screen, stars):
    width, height = screen.get_size()
    for star in stars:
        x = int(star.x_ratio * width)
        y = int(star.y_ratio * height)
        color = (180, 210, 255, star.alpha)
        if star.radius == 1:
            star_surface = pygame.Surface((2, 2), pygame.SRCALPHA)
            star_surface.fill(color)
        else:
            star_surface = pygame.Surface((5, 5), pygame.SRCALPHA)
            pygame.draw.circle(star_surface, color, (2, 2), 2)
        screen.blit(star_surface, (x, y))


def draw_end_screen(
    screen,
    clock,
    won,
    destroyed,
    drone_target,
    score,
    hits_taken,
    credits_earned,
    accurate_inputs,
    inaccurate_inputs,
    inaccurate_keys,
):
    title_font = pygame.font.SysFont("arial", 56, bold=True)
    body_font = pygame.font.SysFont("arial", 26)
    small_font = pygame.font.SysFont("arial", 20)
    title = "MISSION COMPLETE" if won else "MISSION FAILED"
    destroyed_count = int(min(destroyed, drone_target))
    accuracy_inputs = accurate_inputs + inaccurate_inputs
    accuracy_percent = 100 if accuracy_inputs == 0 else round(accurate_inputs * 100 / accuracy_inputs)
    rows = [
        ("Points", str(score)),
        ("Hits taken", str(hits_taken)),
        ("Drones destroyed", f"{destroyed_count}/{drone_target}"),
        ("Accuracy", f"{accuracy_percent}%"),
        ("Accurate keys", str(accurate_inputs)),
        ("Inaccurate keys", str(inaccurate_inputs)),
        ("Credits earned", str(credits_earned)),
    ]
    if 0 < inaccurate_inputs < 5:
        rows.insert(-1, ("Incorrect keys", ", ".join(display_key(key) for key in inaccurate_keys)))
    prompt = "Press ␣ to return to the menu"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                started_space_charge = False
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                if event.key == pygame.K_SPACE:
                    return "won" if won else "lost"
                if event.key == pygame.K_ESCAPE:
                    return "won" if won else "lost"

        screen.fill(BG_COLOR)
        width, height = screen.get_size()
        modal_rect = pygame.Rect(0, 0, min(600, width - 80), min(640, height - 32))
        modal_rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), modal_rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT if won else THREE_SHOT_DRONE_COLOR, modal_rect, 2, border_radius=8)
        title_surface = title_font.render(title, True, ACCENT if won else THREE_SHOT_DRONE_COLOR)
        screen.blit(title_surface, title_surface.get_rect(center=(width / 2, modal_rect.y + 72)))
        for index, (label, value) in enumerate(rows):
            y = modal_rect.y + 132 + index * 40
            label_surface = body_font.render(label, True, MUTED_TEXT)
            value_surface = body_font.render(value, True, TEXT_COLOR)
            screen.blit(label_surface, (modal_rect.x + 58, y))
            screen.blit(value_surface, (modal_rect.right - value_surface.get_width() - 58, y))
        if won and hits_taken == 0:
            render_inline_center(screen, "No Damage Taken Bonus: +25 credits", small_font, ACCENT, (width / 2, modal_rect.bottom - 126))
        if won and inaccurate_inputs == 0:
            render_inline_center(screen, "Energy Saver Bonus: +50 credits", small_font, ACCENT, (width / 2, modal_rect.bottom - 92))
        render_inline_center(screen, prompt, body_font, MUTED_TEXT, (width / 2, modal_rect.bottom - 45))
        pygame.display.flip()
        clock.tick(60)


def draw_button(surface, rect, text, font, selected=False):
    fill = (27, 42, 74) if selected else (14, 24, 45)
    border = ACCENT if selected else (65, 82, 120)
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, 2, border_radius=8)
    label = font.render(text, True, TEXT_COLOR)
    surface.blit(label, label.get_rect(center=rect.center))


def load_mission_hint_images(lesson_dir, lesson_number):
    hint_images = []
    for index in range(1, 4):
        image = load_image(lesson_dir / f"mission_hint_l{lesson_number}_{index}.png")
        if image is not None:
            hint_images.append((index, image))
    return hint_images


def mission_hint_text(hint_texts, index):
    return str(hint_texts.get(f"mission_hint_{index}", "")).strip()


def draw_mission_briefing_modal(screen, lesson_number, instructions_text, hint_images, hint_texts, instruction_scroll):
    width, height = screen.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((2, 5, 13, 210))
    screen.blit(overlay, (0, 0))

    title_font = pygame.font.SysFont("arial", 42, bold=True)
    body_font = pygame.font.SysFont("arial", 21)
    hint_font = pygame.font.SysFont("arial", 17)
    button_font = pygame.font.SysFont("arial", 26, bold=True)

    modal_width = min(width - 64, 980)
    modal_height = min(height - 32, 740)
    modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
    modal_rect.center = (width / 2, height / 2)

    pygame.draw.rect(screen, (10, 18, 36), modal_rect, border_radius=8)
    pygame.draw.rect(screen, ACCENT, modal_rect, 2, border_radius=8)

    title = title_font.render(f"Lesson {lesson_number}", True, TEXT_COLOR)
    screen.blit(title, title.get_rect(center=(width / 2, modal_rect.y + 52)))

    content_margin = 44
    button_rect = pygame.Rect(0, modal_rect.bottom - 78, 190, 48)
    button_rect.centerx = modal_rect.centerx

    image_size = 0
    image_y = 0
    if hint_images:
        available_width = modal_rect.width - content_margin * 2
        gap = 24
        image_size = min(MISSION_HINT_IMAGE_SIZE, int((available_width - gap * (len(hint_images) - 1)) / len(hint_images)))
        image_size = max(96, image_size)
        image_y = max(modal_rect.y + 190, button_rect.y - image_size - 110)
    text_bottom = image_y - 18 if hint_images else button_rect.y - 18
    text_rect = pygame.Rect(
        modal_rect.x + content_margin,
        modal_rect.y + 96,
        modal_rect.width - content_margin * 2,
        max(70, text_bottom - (modal_rect.y + 96)),
    )
    max_instruction_scroll = draw_scrollable_text(
        screen,
        instructions_text,
        body_font,
        MUTED_TEXT,
        text_rect,
        instruction_scroll,
    )

    if hint_images:
        available_width = modal_rect.width - content_margin * 2
        gap = 24
        total_width = len(hint_images) * image_size + (len(hint_images) - 1) * gap
        x = modal_rect.centerx - total_width / 2
        for index, image in hint_images:
            rect = pygame.Rect(int(x), int(image_y), image_size, image_size)
            scaled = pygame.transform.smoothscale(image, (image_size, image_size))
            screen.blit(scaled, rect)
            hint_text = mission_hint_text(hint_texts, index)
            hint_rect = pygame.Rect(rect.x, rect.bottom + 8, rect.width, button_rect.y - rect.bottom - 34)
            if hint_text:
                draw_wrapped_centered_text(screen, hint_text, hint_font, MUTED_TEXT, hint_rect, line_spacing=2)
            x += image_size + gap

    draw_button(screen, button_rect, "Start", button_font, True)
    return button_rect, max_instruction_scroll


def pause_menu(screen, clock):
    title_font = pygame.font.SysFont("arial", 54, bold=True)
    button_font = pygame.font.SysFont("arial", 28, bold=True)
    small_font = pygame.font.SysFont("arial", 18)
    selected = 0
    actions = ("resume", "restart", "menu")
    labels = ("Resume", "Restart Level", "Exit Level")

    while True:
        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        button_width = min(360, max(260, width - 220))
        button_height = 58
        button_gap = 18
        total_height = len(actions) * button_height + (len(actions) - 1) * button_gap
        start_y = height / 2 - total_height / 2 + 20
        buttons = []
        for index in range(len(actions)):
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.center = (width / 2, start_y + index * (button_height + button_gap))
            buttons.append(rect)

        mouse_pos = pygame.mouse.get_pos()
        for index, rect in enumerate(buttons):
            if rect.collidepoint(mouse_pos):
                selected = index

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                    break
                if event.key == pygame.K_ESCAPE:
                    return "resume"
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(actions)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(actions)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return actions[selected]
                if event.key == pygame.K_r:
                    return "restart"
                if event.key == pygame.K_x:
                    return "menu"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(buttons):
                    if rect.collidepoint(event.pos):
                        return actions[index]

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((2, 5, 13, 205))
        screen.blit(overlay, (0, 0))
        title = title_font.render("PAUSED", True, TEXT_COLOR)
        screen.blit(title, title.get_rect(center=(width / 2, height / 2 - total_height / 2 - 62)))
        for index, rect in enumerate(buttons):
            draw_button(screen, rect, labels[index], button_font, selected == index)
        hint = "Esc: Resume  |  R: Restart  |  X: Exit level  |  F11: Max size"
        render_inline_center(screen, hint, small_font, MUTED_TEXT, (width / 2, height - 54))
        pygame.display.flip()
        clock.tick(60)


class MissionEngine:
    def __init__(self, screen, clock, base_dir, lesson_dir_name, valid_keys, player=None):
        self.screen = screen
        self.clock = clock
        self.base_dir = base_dir
        self.player = player
        self.lesson_dir_name = lesson_dir_name
        self.valid_keys = valid_keys
        self.lesson_dir = Path(base_dir) / "lessons" / lesson_dir_name
        self.sfx_dir = Path(base_dir) / "sfx"
        self.gfx_dir = Path(base_dir) / "gfx"
        self.pod_gfx_dir = self.gfx_dir / "pod"
        self.drone_gfx_dir = self.gfx_dir / "drones"
        self.lesson_number = int(lesson_dir_name.split("_")[-1])
        self.player_splash_color = player_upgrade_color(player, "drone_splash_color")
        self.shot_charge_color = player_upgrade_color(player, "ammo_charge_color")
        self.player_mega_shot_available = player_mega_shot_available(player, self.lesson_number)
        self.player_shields_available = player_shield_available(player, self.lesson_number)
        self.max_shield_charges = player_shield_max_charges(player)
        self.target_keys = mission_target_keys(valid_keys, self.lesson_number, self.player_mega_shot_available)
        self.focus_keys = lesson_focus_keys(self.lesson_number, self.target_keys)
        self.drone_target = lesson_drone_target(self.lesson_number)
        self.mini_boss_numbers = mini_boss_numbers_for_lesson(self.lesson_number, self.drone_target)
        self.instructions_audio_path = self.lesson_dir / f"lesson_{self.lesson_number}_instructions.wav"
        self.instructions_audio_duration_ms = audio_duration_ms(self.instructions_audio_path)
        self.instructions_text = read_text(self.lesson_dir / f"lesson_{self.lesson_number}_instructions.txt")
        self.hint_images = load_mission_hint_images(self.lesson_dir, self.lesson_number)
        self.hint_texts = load_json_object(self.lesson_dir / f"mission_hints_l{self.lesson_number}.json")
        self.laser_sound = load_sound(self.sfx_dir / "laser.ogg", 0.55)
        self.explosion_sound = load_sound(self.sfx_dir / "explosion.ogg", 0.75)
        self.health_sound = load_sound(self.sfx_dir / "health.ogg", 0.85)
        self.shield_up_sound = load_sound(self.sfx_dir / "shield_up.wav", 0.85)
        self.split_sound = load_sound(self.sfx_dir / "split.ogg", 0.75)
        self.boss_sound = load_sound(self.sfx_dir / "boss.ogg", 0.85)
        self.victory_sound = load_sound(self.sfx_dir / "victory.wav", 0.9)
        self.bg_music = load_sound(self.sfx_dir / "bg_music.wav", BG_MUSIC_VOLUME)
        self.bg_music_channel = play_looping_sound(self.bg_music, BG_MUSIC_FADE_IN_MS)
        self.turret_image = load_pod_variant_image(self.pod_gfx_dir, "turret", self.player_splash_color)
        if self.turret_image is not None:
            self.turret_image = pygame.transform.smoothscale(self.turret_image, (TURRET_IMAGE_SIZE, TURRET_IMAGE_SIZE))
        self.pod_image = load_pod_variant_image(self.pod_gfx_dir, "pod", self.player_splash_color)
        if self.pod_image is not None:
            self.pod_image = pygame.transform.smoothscale(self.pod_image, (POD_IMAGE_SIZE, POD_IMAGE_SIZE))
        self.shot_image = load_pod_variant_image(self.pod_gfx_dir, "shot", self.shot_charge_color)
        if self.shot_image is not None:
            self.shot_image = pygame.transform.smoothscale(self.shot_image, (SHOT_IMAGE_SIZE, SHOT_IMAGE_SIZE))
        self.defense_drone_image = load_pod_variant_image(
            self.pod_gfx_dir,
            "defense_drone",
            self.player_splash_color,
            "defense_drone_image.png",
        )
        if self.defense_drone_image is not None:
            defense_drone_size = DEFENSE_DRONE_RADIUS * 2
            self.defense_drone_image = pygame.transform.smoothscale(
                self.defense_drone_image,
                (defense_drone_size, defense_drone_size),
            )
        self.final_boss_image = load_image(self.drone_gfx_dir / "final-boss.png")
        if self.final_boss_image is not None:
            self.final_boss_image = pygame.transform.smoothscale(
                self.final_boss_image,
                (FINAL_BOSS_IMAGE_SIZE, FINAL_BOSS_IMAGE_SIZE),
            )
        self.drone_images = {
            "yellow": load_image(self.drone_gfx_dir / "yellow_drone.png"),
            "orange": load_image(self.drone_gfx_dir / "orange_drone.png"),
            "red": load_image(self.drone_gfx_dir / "red_drone.png"),
            "semi_boss": load_image(self.drone_gfx_dir / "semi-boss.png"),
        }
        self.drone_image_cache = {}

        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.drones = []
        self.bullets = []
        self.mega_shots = []
        defense_drone_count = player_defense_drone_count(player)
        self.defense_drones = [
            DefenseDrone(
                angle=index * math.pi,
                next_fire_time=pygame.time.get_ticks() + DEFENSE_DRONE_FIRE_INTERVAL_MS,
            )
            for index in range(defense_drone_count)
        ]
        self.defense_shots = []
        self.pending_shots = []
        self.shot_trails = []
        self.power_up = None
        self.life_power_ups_spawned = 0
        self.final_boss = None
        self.particles = []
        self.stars = create_star_field()
        self.destroyed = 0
        self.spawned_count = 0
        self.score = 0
        self.hits_taken = 0
        self.accurate_inputs = 0
        self.inaccurate_inputs = 0
        self.inaccurate_keys = []
        self.credits_awarded = False
        self.lives = max(STARTING_LIVES, self._player_int("lives", STARTING_LIVES, 1, MAX_PLAYER_LIVES))
        self.shield_charges = self._player_int("shield_charges", 0, 0, self.max_shield_charges)
        self.active_shield_hits = 0
        self.active_shield_expires_at = 0
        self._save_player_resources()
        self.turret_angle = -math.pi / 2
        self.pod_rotation = 0
        self.player_center = screen_center(self.screen)
        self.space_held = False
        self.mega_charge_blocks = MEGA_CHARGE_MAX_BLOCKS
        self.next_mega_recharge_time = 0
        self.current_spawn_interval_ms = random_spawn_interval(self.lesson_number)
        self.next_spawn_rate_change_time = pygame.time.get_ticks() + SPAWN_RATE_CHANGE_MS
        self.next_spawn_time = pygame.time.get_ticks()
        self.next_power_up_spawn_time = next_power_up_time(self.next_spawn_time)

    def _run_mission_briefing(self):
        play_audio(self.instructions_audio_path)
        previous_mouse_visible = pygame.mouse.get_visible()
        pygame.mouse.set_visible(True)
        briefing_started_at = pygame.time.get_ticks()
        start_button = pygame.Rect(0, 0, 0, 0)
        instruction_scroll = 0
        max_instruction_scroll = 0
        audio_seconds = self.instructions_audio_duration_ms / 1000 if self.instructions_audio_duration_ms > 0 else MISSION_BRIEFING_FALLBACK_SCROLL_SECONDS
        scroll_duration = max(1, audio_seconds - MISSION_BRIEFING_SCROLL_END_BUFFER_SECONDS)
        scroll_speed = 0
        try:
            while True:
                now = pygame.time.get_ticks()
                dt = self.clock.tick(60) / 1000
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        stop_audio()
                        return "quit"
                    if event.type == pygame.VIDEORESIZE:
                        self.screen = enforce_min_window_size(self.screen)
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_F11:
                            self.screen = toggle_fullscreen()
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            instruction_scroll = min(max_instruction_scroll, instruction_scroll + 42)
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            instruction_scroll = max(0, instruction_scroll - 42)
                        elif event.key == pygame.K_PAGEDOWN:
                            instruction_scroll = min(max_instruction_scroll, instruction_scroll + 210)
                        elif event.key == pygame.K_PAGEUP:
                            instruction_scroll = max(0, instruction_scroll - 210)
                        elif event.key == pygame.K_SPACE:
                            stop_audio()
                            self._shift_gameplay_timers(pygame.time.get_ticks() - briefing_started_at)
                            return "start"
                    if event.type == pygame.MOUSEWHEEL:
                        instruction_scroll = max(0, min(max_instruction_scroll, instruction_scroll - event.y * 36))
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if start_button.collidepoint(event.pos):
                            stop_audio()
                            self._shift_gameplay_timers(pygame.time.get_ticks() - briefing_started_at)
                            return "start"

                instruction_scroll = min(max_instruction_scroll, instruction_scroll + scroll_speed * dt)
                self._draw_frame(now, present=False)
                start_button, max_instruction_scroll = draw_mission_briefing_modal(
                    self.screen,
                    self.lesson_number,
                    self.instructions_text,
                    self.hint_images,
                    self.hint_texts,
                    instruction_scroll,
                )
                scroll_speed = max_instruction_scroll / scroll_duration if max_instruction_scroll else 0
                instruction_scroll = max(0, min(instruction_scroll, max_instruction_scroll))
                pygame.display.flip()
        finally:
            pygame.mouse.set_visible(previous_mouse_visible)

    def _player_int(self, key, default, minimum=0, maximum=None):
        if self.player is None:
            value = default
        else:
            value = self.player.get(key, default)
        if not isinstance(value, int):
            value = default
        value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def _save_player_resources(self):
        if self.player is None:
            return
        self.player["lives"] = max(1, min(MAX_PLAYER_LIVES, self.lives))
        self.player["shield_charges"] = max(0, min(self.max_shield_charges, self.shield_charges))

    def _add_lifetime_score(self):
        if self.player is None:
            return
        lifetime_score = self.player.get("lifetime_score", 0)
        if not isinstance(lifetime_score, int):
            lifetime_score = 0
        self.player["lifetime_score"] = max(0, lifetime_score) + self.score

    def _calculate_credits_earned(self, won):
        credits = int(min(self.destroyed, self.drone_target))
        if won:
            credits += 50
            if self.hits_taken == 0:
                credits += 25
            if self.inaccurate_inputs == 0:
                credits += ENERGY_SAVER_BONUS_CREDITS
        return credits

    def _award_credits(self, credits_earned):
        if self.player is None or self.credits_awarded:
            return
        current_credits = self.player.get("credits", 0)
        if not isinstance(current_credits, int):
            current_credits = 0
        self.player["credits"] = max(0, current_credits) + credits_earned
        self.credits_awarded = True

    def _shield_is_active(self, now):
        return self.active_shield_hits > 0 and now < self.active_shield_expires_at

    def _clear_active_shield(self):
        self.active_shield_hits = 0
        self.active_shield_expires_at = 0

    def _absorb_player_hit_with_shield(self, now):
        if self._shield_is_active(now):
            self.active_shield_hits -= 1
            if self.active_shield_hits <= 0:
                self._clear_active_shield()
            return True

        self._clear_active_shield()
        if not self.player_shields_available or self.shield_charges <= 0:
            return False

        self.shield_charges -= 1
        self.active_shield_hits = PLAYER_ACTIVE_SHIELD_EXTRA_HITS
        self.active_shield_expires_at = now + PLAYER_ACTIVE_SHIELD_DURATION_MS
        self._save_player_resources()
        play_sound(self.shield_up_sound)
        return True

    def _finish(self, result):
        self._save_player_resources()
        return result

    def _record_accurate_input(self):
        self.accurate_inputs += 1

    def _record_inaccurate_input(self):
        self.inaccurate_inputs += 1

    def _record_inaccurate_key(self, key):
        self._record_inaccurate_input()
        if len(self.inaccurate_keys) < 4:
            self.inaccurate_keys.append(key)

    def _defense_drone_accuracy_grace_active(self, pressed_key, now):
        if pressed_key is None:
            return False
        return any(
            defense_drone.last_shot_key == pressed_key and now <= defense_drone.last_shot_grace_until
            for defense_drone in self.defense_drones
        )

    def _show_end_screen(self, won):
        self._save_player_resources()
        credits_earned = self._calculate_credits_earned(won)
        self._award_credits(credits_earned)
        if won:
            self._add_lifetime_score()
        return draw_end_screen(
            self.screen,
            self.clock,
            won,
            self.destroyed,
            self.drone_target,
            self.score,
            self.hits_taken,
            credits_earned,
            self.accurate_inputs,
            self.inaccurate_inputs,
            self.inaccurate_keys,
        )

    def _boss_player_target_center(self):
        width, height = self.screen.get_size()
        return pygame.Vector2(width * FINAL_BOSS_PLAYER_X_RATIO, height / 2)

    def _update_player_center(self, dt):
        target = self._boss_player_target_center() if self.final_boss is not None else screen_center(self.screen)
        travel = target - self.player_center
        distance = travel.length()
        max_step = FINAL_BOSS_PLAYER_PAN_SPEED * dt
        if distance <= max_step or distance == 0:
            self.player_center = target
        else:
            self.player_center += travel.normalize() * max_step

    def _boss_perspective_ready(self):
        if self.final_boss is None:
            return False
        return self.player_center.distance_to(self._boss_player_target_center()) <= 2

    def _shift_gameplay_timers(self, elapsed_ms):
        if elapsed_ms <= 0:
            return
        self.next_mega_recharge_time = self._shift_timer(self.next_mega_recharge_time, elapsed_ms)
        self.next_spawn_rate_change_time = self._shift_timer(self.next_spawn_rate_change_time, elapsed_ms)
        self.next_spawn_time = self._shift_timer(self.next_spawn_time, elapsed_ms)
        self.next_power_up_spawn_time = self._shift_timer(self.next_power_up_spawn_time, elapsed_ms)
        self.active_shield_expires_at = self._shift_timer(self.active_shield_expires_at, elapsed_ms)
        if self.power_up is not None:
            self.power_up.expires_at += elapsed_ms
        if self.final_boss is not None:
            self.final_boss.next_shot_time = self._shift_timer(self.final_boss.next_shot_time, elapsed_ms)
            self.final_boss.next_orbit_switch_time = self._shift_timer(
                self.final_boss.next_orbit_switch_time,
                elapsed_ms,
            )
            self.final_boss.next_semi_boss_spawn_time = self._shift_timer(
                self.final_boss.next_semi_boss_spawn_time,
                elapsed_ms,
            )
            if self.final_boss.shield_down_since is not None:
                self.final_boss.shield_down_since += elapsed_ms
            if self.final_boss.next_shield_recharge_time is not None:
                self.final_boss.next_shield_recharge_time += elapsed_ms
        for drone in self.drones:
            drone.next_shot_time = self._shift_timer(drone.next_shot_time, elapsed_ms)
        for defense_drone in self.defense_drones:
            defense_drone.next_fire_time = self._shift_timer(defense_drone.next_fire_time, elapsed_ms)
            defense_drone.last_shot_grace_until = self._shift_timer(defense_drone.last_shot_grace_until, elapsed_ms)
        for bullet in self.bullets:
            bullet.next_trail_time = self._shift_timer(bullet.next_trail_time, elapsed_ms)
        for mega_shot in self.mega_shots:
            mega_shot.next_trail_time = self._shift_timer(mega_shot.next_trail_time, elapsed_ms)
        for pending_shot in self.pending_shots:
            pending_shot.created_at += elapsed_ms

    @staticmethod
    def _shift_timer(value, elapsed_ms):
        return value + elapsed_ms if value else value

    def _begin_frame(self):
        dt = self.clock.tick(60) / 1000
        now = pygame.time.get_ticks()
        self._update_player_center(dt)
        self.pod_rotation = (self.pod_rotation + math.tau * dt / POD_ROTATION_SECONDS) % math.tau
        if now >= self.next_spawn_rate_change_time:
            self.current_spawn_interval_ms = random_spawn_interval(self.lesson_number)
            self.next_spawn_rate_change_time = now + SPAWN_RATE_CHANGE_MS
        update_star_field(self.stars, dt)
        if self.player_mega_shot_available and self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS:
            if self.next_mega_recharge_time and now >= self.next_mega_recharge_time:
                self.mega_charge_blocks += 1
                self.next_mega_recharge_time = (
                    now + MEGA_RECHARGE_INTERVAL_MS
                    if self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS
                    else 0
                )
        return dt, now

    def _start_final_boss_encounter(self, now):
        for drone in self.drones:
            explode(self.particles, drone.pos, 12)
        self.drones.clear()
        while self.pending_shots:
            release_pending_shot(self.pending_shots.pop(0))
        self.bullets.clear()
        self.mega_shots.clear()
        self.final_boss = spawn_final_boss(
            self.screen,
            now,
            self.target_keys,
            self._boss_player_target_center(),
            self.focus_keys,
        )
        play_sound(self.boss_sound)

    def _power_up_blocked_rects(self):
        width, height = self.screen.get_size()
        rects = [
            pygame.Rect(0, 0, 340, 58),
            pygame.Rect(max(0, width - 340), 0, 340, 88),
            pygame.Rect(0, max(0, height - 68), width, 68),
        ]
        if self.player_mega_shot_available:
            rects.append(pygame.Rect(width / 2 - 260, 8, 520, 82))
        if self.player_shields_available:
            rects.append(pygame.Rect(width / 2 - 260, 8, 520, 82))
        return rects

    def _spawn_entities(self, now):
        has_no_standard_play_drones = (
            self.final_boss is None
            and not self.drones
            and self.destroyed < self.drone_target
        )
        if (
            self.final_boss is None
            and should_spawn_mission_drone(
                self.lesson_number,
                self.spawned_count,
                self.destroyed,
                self.drones,
                self.drone_target,
            )
            and (now >= self.next_spawn_time or has_no_standard_play_drones)
        ):
            drone, self.spawned_count = spawn_next_drone(
                self.drones,
                self.screen,
                self.destroyed,
                self.target_keys,
                self.spawned_count,
                self.mini_boss_numbers,
                self.focus_keys,
            )
            if drone.is_mega:
                play_sound(self.boss_sound)
            self.next_spawn_time = now + self.current_spawn_interval_ms

        if self.power_up is not None and now >= self.power_up.expires_at:
            self.power_up = None
            self.next_power_up_spawn_time = next_power_up_time(now)
        if self.power_up is None and now >= self.next_power_up_spawn_time:
            self.power_up = spawn_power_up(
                self.screen,
                self.target_keys,
                now,
                player_shield_enabled(self.lesson_number),
                self.shield_charges,
                self.max_shield_charges,
                self.life_power_ups_spawned < MAX_LIFE_POWER_UPS_PER_MISSION,
                self.player_center,
                blocked_rects=self._power_up_blocked_rects(),
            )
            if self.power_up is None:
                self.next_power_up_spawn_time = next_power_up_time(now)
            elif self.power_up.kind == "life":
                self.life_power_ups_spawned += 1

        if (
            final_boss_enabled(self.lesson_number)
            and self.final_boss is None
            and self.destroyed >= self.drone_target
            and active_mini_boss_count(self.drones) == 0
        ):
            self._start_final_boss_encounter(now)

    def _draw_frame(self, now, present=True):
        self.screen = pygame.display.get_surface()
        if self.active_shield_hits > 0 and now >= self.active_shield_expires_at:
            self._clear_active_shield()
        self.screen.fill(BG_COLOR)
        width, height = self.screen.get_size()
        draw_star_field(self.screen, self.stars)

        for particle in self.particles:
            alpha_scale = max(0, min(1, particle.ttl))
            radius = max(2, int(5 * alpha_scale))
            pygame.draw.circle(self.screen, EXPLOSION_COLOR, particle.pos, radius)

        draw_shot_trails(self.screen, self.shot_trails)

        for bullet in self.bullets:
            draw_bullet(self.screen, bullet, self.shot_image)

        for mega_shot in self.mega_shots:
            draw_mega_shot(self.screen, mega_shot, self.shot_image)

        for defense_shot in self.defense_shots:
            draw_defense_shot(self.screen, defense_shot)

        draw_power_up(self.screen, self.power_up, now)
        draw_final_boss(self.screen, self.final_boss, self.final_boss_image)

        for drone in self.drones:
            color = drone_color(drone)
            if drone.is_mega:
                image = rotated_drone_image(drone, self.drone_images, self.drone_image_cache)
                if image is None:
                    points = pentagon_points(drone.pos, drone.radius, drone.rotation - math.pi / 2)
                    pygame.draw.polygon(self.screen, color, points)
                    pygame.draw.polygon(self.screen, (245, 222, 255), points, 2)
                else:
                    self.screen.blit(image, image.get_rect(center=drone.pos))
            else:
                image = rotated_drone_image(drone, self.drone_images, self.drone_image_cache)
                if image is None:
                    pygame.draw.circle(self.screen, color, drone.pos, drone.radius)
                    pygame.draw.circle(self.screen, (255, 231, 214), drone.pos, drone.radius, 2)
                else:
                    self.screen.blit(image, image.get_rect(center=drone.pos))
            label_size = 18 if len(drone.letter) > 2 else 28
            label_font = pygame.font.SysFont("arial", label_size, bold=True)
            render_key_label(self.screen, drone.letter, label_font, (8, 10, 18), drone.pos, drone.radius * 1.45)

        draw_ship(self.screen, self.turret_angle, self.pod_rotation, self.turret_image, self.pod_image, self.player_center)
        for defense_drone in self.defense_drones:
            draw_defense_drone(self.screen, defense_drone, self.player_center, self.defense_drone_image)
        draw_active_player_shield(
            self.screen,
            self.player_center,
            self.active_shield_expires_at,
            self.active_shield_hits,
            now,
        )
        mega_text = ""
        mega_active = False
        if self.player_mega_shot_available:
            mega_text = "Mega shot"
            mega_active = self.mega_charge_blocks > 0
        width, _ = self.screen.get_size()
        if self.player_mega_shot_available and self.player_shields_available:
            mega_center_x = width / 2 - 112
            shield_center_x = width / 2 + 112
        else:
            mega_center_x = width / 2
            shield_center_x = width / 2
        draw_mega_bar(self.screen, self.font, mega_text, self.mega_charge_blocks, mega_active, mega_center_x)
        draw_player_shield_bar(
            self.screen,
            self.font,
            self.shield_charges,
            self.player_shields_available,
            0,
            self.max_shield_charges,
            shield_center_x,
        )
        draw_hud(self.screen, self.font, min(self.destroyed, self.drone_target), self.drone_target, self.score, self.lives)

        key_hint = ", ".join(display_key(key) for key in self.target_keys)
        hint = f"Press {key_hint} to fire. F11 toggles max size. Esc returns to menu."
        render_inline_text(self.screen, hint, pygame.font.SysFont("arial", 18), MUTED_TEXT, (22, height - 34))

        if present:
            pygame.display.flip()

    def _process_pending_shots(self, now, dt):
        while self.pending_shots and not target_is_available(self.pending_shots[0].target, self.drones, self.final_boss):
            release_pending_shot(self.pending_shots.pop(0))
        if self.pending_shots:
            center = self.player_center
            next_shot = self.pending_shots[0]
            aim_angle = target_angle(next_shot.target, center)
            self.turret_angle = rotate_toward_angle(self.turret_angle, aim_angle, TURRET_TURN_SPEED * dt)
            if (
                now - next_shot.created_at >= TURRET_FIRE_DELAY_MS
                and abs(angle_delta(self.turret_angle, aim_angle)) <= TURRET_FIRE_ANGLE_THRESHOLD
            ):
                self.turret_angle = fire_pending_shot(next_shot, self.bullets, self.mega_shots, center)
                self.pending_shots.pop(0)
                play_sound(self.laser_sound)

    def _update_final_boss(self, now, dt):
        if self.final_boss is None:
            return
        update_final_boss_movement(self.final_boss, self.screen, dt, now)
        self.final_boss.rotation = (self.final_boss.rotation + math.tau * dt / FINAL_BOSS_ROTATION_SECONDS) % math.tau
        update_final_boss_shield(self.final_boss, now)
        if self.final_boss.is_orbiting and self._boss_perspective_ready() and self.final_boss.next_shot_time == 0:
            self.final_boss.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS
        if (
            self.final_boss.is_orbiting
            and self._boss_perspective_ready()
            and self.final_boss.next_shot_time
            and now >= self.final_boss.next_shot_time
        ):
            fire_final_boss_drones(
                self.drones,
                self.final_boss,
                self.player_center,
                self.target_keys,
                final_boss_projectile_count(self.lesson_number),
                self.focus_keys,
            )
            self.final_boss.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS
        if self.final_boss.next_semi_boss_spawn_time and now >= self.final_boss.next_semi_boss_spawn_time:
            spawn_final_boss_semi_boss(
                self.drones,
                self.final_boss,
                self.player_center,
                self.target_keys,
                self.focus_keys,
            )
            play_sound(self.boss_sound)
            self.final_boss.next_semi_boss_spawn_time = now + FINAL_BOSS_SEMI_BOSS_SPAWN_INTERVAL_MS

    def _update_drones(self, now, dt):
        for drone in self.drones[:]:
            center = self.player_center
            update_drone_position(drone, center, dt)
            drone.rotation = (drone.rotation + drone_rotation_radians_per_second(drone) * dt) % math.tau
            if drone.is_mega and now >= drone.next_shot_time:
                blocked_key = self.final_boss.letter if self.final_boss is not None else None
                focus_keys = self.focus_keys if self.final_boss is not None else ()
                fire_mega_drone(self.drones, drone, center, self.target_keys, blocked_key, focus_keys)
                drone.next_shot_time = now + MEGA_ATTACK_INTERVAL_MS
            if drone.pos.distance_to(center) <= drone.radius + PLAYER_COLLISION_RADIUS:
                self.drones.remove(drone)
                explode(self.particles, drone.pos, 12)
                play_sound(self.explosion_sound)
                self.hits_taken += 1
                if self._absorb_player_hit_with_shield(now):
                    continue
                self.lives -= 1
                self._save_player_resources()
                if self.lives <= 0:
                    stop_looping_sound(self.bg_music_channel, BG_MUSIC_FADE_OUT_MS)
                    stop_audio()
                    explode(self.particles, center, 36)
                    return self._show_end_screen(False)
        return None

    def _update_particles(self, dt):
        for particle in self.particles[:]:
            particle.ttl -= dt
            if particle.ttl <= 0:
                self.particles.remove(particle)
                continue
            particle.pos += particle.vel * dt
            particle.vel *= 0.98

    def _update_shot_trails(self, dt):
        for particle in self.shot_trails[:]:
            particle.ttl -= dt
            if particle.ttl <= 0:
                self.shot_trails.remove(particle)
                continue
            particle.pos += particle.vel * dt
            particle.vel *= 0.92

    def _count_defense_drone_kill(self, drone):
        pos = drone.pos.copy()
        if drone in self.drones:
            self.drones.remove(drone)
        if drone_counts_for_level(drone):
            self.destroyed += drone.level_value
        self.score += 100
        explode(self.particles, pos)
        play_sound(self.explosion_sound)

    def _damage_drone_from_defense_shot(self, drone):
        if drone not in self.drones:
            return
        drone.incoming_damage = max(0, drone.incoming_damage - 1)
        drone.hp -= 1
        if drone.hp > 0 and not drone.is_mega:
            self.drones.remove(drone)
            split_regular_drone(self.drones, drone)
            play_sound(self.split_sound)
        elif drone.hp <= 0:
            self._count_defense_drone_kill(drone)

    def _defense_drone_has_line_of_sight(self, defense_pos, target_pos):
        segment = target_pos - defense_pos
        length_squared = segment.length_squared()
        if length_squared == 0:
            return True
        center_to_start = self.player_center - defense_pos
        projection = max(0, min(1, center_to_start.dot(segment) / length_squared))
        closest = defense_pos + segment * projection
        return closest.distance_to(self.player_center) > DEFENSE_DRONE_LINE_OF_SIGHT_BLOCK_RADIUS

    def _defense_drone_target(self, defense_pos):
        candidates = [
            drone
            for drone in self.drones
            if self._defense_drone_has_line_of_sight(defense_pos, drone.pos)
        ]
        return random.choice(candidates) if candidates else None

    def _update_defense_drones(self, now, dt):
        for defense_drone in self.defense_drones:
            if not defense_drone.active:
                continue
            defense_drone.angle = (defense_drone.angle + math.tau * dt / DEFENSE_DRONE_ORBIT_SECONDS) % math.tau
            defense_pos = defense_drone_position(self.player_center, defense_drone)

            for drone in self.drones[:]:
                if drone.pos.distance_to(defense_pos) <= drone.radius + DEFENSE_DRONE_COLLISION_RADIUS:
                    defense_drone.active = False
                    self._count_defense_drone_kill(drone)
                    explode(self.particles, defense_pos, 10)
                    break

            if not defense_drone.active:
                continue
            if now >= defense_drone.next_fire_time:
                target = self._defense_drone_target(defense_pos)
                if target is not None:
                    defense_drone.last_shot_key = target.letter
                    defense_drone.last_shot_grace_until = now + DEFENSE_DRONE_ACCURACY_GRACE_MS
                    direction = target.pos - defense_pos
                    if direction.length_squared() == 0:
                        direction = pygame.Vector2(0, -1)
                    else:
                        direction = direction.normalize()
                    target.incoming_damage += 1
                    self.defense_shots.append(
                        DefenseShot(
                            pos=defense_pos + direction * (DEFENSE_DRONE_RADIUS + DEFENSE_DRONE_SHOT_RADIUS + 2),
                            vel=direction * DEFENSE_DRONE_SHOT_SPEED,
                            target=target,
                        )
                    )
                    play_sound(self.laser_sound)
                defense_drone.next_fire_time = now + DEFENSE_DRONE_FIRE_INTERVAL_MS

    def _update_defense_shots(self, dt):
        for shot in self.defense_shots[:]:
            if shot.target not in self.drones:
                if shot.target is not None:
                    shot.target.incoming_damage = max(0, shot.target.incoming_damage - 1)
                shot.target = None
                add_shot_trail(self.shot_trails, shot, pygame.time.get_ticks())
                shot.pos += shot.vel * dt
                if bullet_is_offscreen(shot, self.screen):
                    self.defense_shots.remove(shot)
                continue

            target_vector = shot.target.pos - shot.pos
            if target_vector.length_squared() <= (shot.target.radius + DEFENSE_DRONE_SHOT_RADIUS) ** 2:
                target = shot.target
                self.defense_shots.remove(shot)
                self._damage_drone_from_defense_shot(target)
                continue

            if target_vector.length_squared() > 0:
                shot.vel = target_vector.normalize() * DEFENSE_DRONE_SHOT_SPEED
            add_shot_trail(self.shot_trails, shot, pygame.time.get_ticks())
            shot.pos += shot.vel * dt
            if bullet_is_offscreen(shot, self.screen):
                shot.target.incoming_damage = max(0, shot.target.incoming_damage - 1)
                self.defense_shots.remove(shot)

    def run(self):
        briefing_result = self._run_mission_briefing()
        if briefing_result == "quit":
            stop_looping_sound(self.bg_music_channel)
            return self._finish("quit")
        pygame.mouse.set_visible(False)
        pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))

        while True:
            dt, now = self._begin_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stop_looping_sound(self.bg_music_channel)
                    stop_audio()
                    return self._finish("quit")
                if event.type == pygame.VIDEORESIZE:
                    self.screen = enforce_min_window_size(self.screen)
                if event.type == pygame.KEYDOWN:
                    started_space_charge = False
                    if event.key == pygame.K_F11:
                        self.screen = toggle_fullscreen()
                    if event.key == pygame.K_ESCAPE:
                        pygame.mouse.set_visible(True)
                        if self.bg_music_channel is not None:
                            self.bg_music_channel.pause()
                        if pygame.mixer.get_init():
                            pygame.mixer.music.pause()
                        pause_started_at = pygame.time.get_ticks()
                        pause_result = pause_menu(self.screen, self.clock)
                        if pause_result == "resume":
                            self._shift_gameplay_timers(pygame.time.get_ticks() - pause_started_at)
                            pygame.mouse.set_visible(False)
                            if self.bg_music_channel is not None:
                                self.bg_music_channel.unpause()
                            if pygame.mixer.get_init():
                                pygame.mixer.music.unpause()
                            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN))
                            continue
                        stop_looping_sound(self.bg_music_channel, BG_MUSIC_FADE_OUT_MS)
                        stop_audio()
                        if pause_result == "quit":
                            return self._finish("quit")
                        if pause_result == "restart":
                            return self._finish("restart")
                        return self._finish("menu")
                    pressed_key = event_to_lesson_key(event)
                    if self.player_mega_shot_available and event.key == pygame.K_SPACE:
                        self.space_held = True
                        started_space_charge = True
                    collected_power_up, consumed_by_power_up = handle_power_up_key(self.power_up, pressed_key)
                    if collected_power_up:
                        if collected_power_up == "shield":
                            self.shield_charges = min(self.max_shield_charges, self.shield_charges + 1)
                        else:
                            self.lives = min(MAX_PLAYER_LIVES, self.lives + 1)
                        self._save_player_resources()
                        play_sound(self.health_sound)
                        self.power_up = None
                        self.next_power_up_spawn_time = next_power_up_time(now)
                    if consumed_by_power_up:
                        self._record_accurate_input()
                        continue
                    shot_queued = False
                    if pressed_key in self.target_keys:
                        if (
                            self.player_mega_shot_available
                            and self.space_held
                            and not started_space_charge
                            and self.mega_charge_blocks > 0
                        ):
                            final_boss_target = self.final_boss if self._boss_perspective_ready() else None
                            queued_mega = queue_mega_shot(
                                self.drones,
                                final_boss_target,
                                self.pending_shots,
                                pressed_key,
                                self.player_center,
                                self.mega_charge_blocks,
                                now,
                            )
                            if queued_mega:
                                self._record_accurate_input()
                                self.mega_charge_blocks = 0
                                self.next_mega_recharge_time = now + MEGA_RECHARGE_DELAY_MS
                                continue
                        shot_queued = queue_shot_at(self.drones, self.pending_shots, pressed_key, self.player_center, now)
                        if shot_queued:
                            self._record_accurate_input()
                    if (
                        pressed_key is not None
                        and not shot_queued
                        and not started_space_charge
                        and not self._defense_drone_accuracy_grace_active(pressed_key, now)
                    ):
                        self._record_inaccurate_key(pressed_key)
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        self.space_held = False

            self._process_pending_shots(now, dt)

            self._spawn_entities(now)

            if (
                not final_boss_enabled(self.lesson_number)
                and (self.lesson_number <= 2 or self.spawned_count >= self.drone_target)
                and self.destroyed >= self.drone_target
                and active_mini_boss_count(self.drones) == 0
            ):
                stop_looping_sound(self.bg_music_channel, BG_MUSIC_FADE_OUT_MS)
                stop_audio()
                play_sound(self.victory_sound)
                return self._show_end_screen(True)

            self._update_final_boss(now, dt)
            self._update_defense_drones(now, dt)
            result = self._update_drones(now, dt)
            if result is not None:
                return result
            self._update_defense_shots(dt)

            for bullet in self.bullets[:]:
                bullet.rotation = (bullet.rotation + math.tau * SHOT_ROTATIONS_PER_SECOND * dt) % math.tau
                if bullet.target not in self.drones:
                    bullet.target = None
                    add_shot_trail(self.shot_trails, bullet, now)
                    bullet.pos += bullet.vel * dt
                    if bullet_is_offscreen(bullet, self.screen):
                        self.bullets.remove(bullet)
                    continue

                if bullet.target is None:
                    add_shot_trail(self.shot_trails, bullet, now)
                    bullet.pos += bullet.vel * dt
                    if bullet_is_offscreen(bullet, self.screen):
                        self.bullets.remove(bullet)
                    continue

                target_vector = bullet.target.pos - bullet.pos
                if target_vector.length_squared() <= (bullet.target.radius + 7) ** 2:
                    bullet.target.incoming_damage = max(0, bullet.target.incoming_damage - 1)
                    bullet.target.hp -= 1
                    self.bullets.remove(bullet)
                    if bullet.target.hp > 0 and not bullet.target.is_mega and bullet.target in self.drones:
                        hit_drone = bullet.target
                        self.drones.remove(hit_drone)
                        split_regular_drone(self.drones, hit_drone)
                        play_sound(self.split_sound)
                        continue
                    if bullet.target.hp <= 0 and bullet.target in self.drones:
                        pos = bullet.target.pos.copy()
                        counts_for_level = drone_counts_for_level(bullet.target)
                        self.drones.remove(bullet.target)
                        if counts_for_level:
                            self.destroyed += bullet.target.level_value
                        self.score += 100
                        explode(self.particles, pos)
                        play_sound(self.explosion_sound)
                    continue

                if target_vector.length_squared() > 0:
                    bullet.vel = target_vector.normalize() * 650
                add_shot_trail(self.shot_trails, bullet, now)
                bullet.pos += bullet.vel * dt

            for mega_shot in self.mega_shots[:]:
                mega_shot.rotation = (mega_shot.rotation + math.tau * SHOT_ROTATIONS_PER_SECOND * dt) % math.tau
                if isinstance(mega_shot.target, Drone) and mega_shot.target not in self.drones:
                    mega_shot.target = None

                if mega_shot.target is None:
                    add_shot_trail(self.shot_trails, mega_shot, now, 0.5625)
                    mega_shot.pos += mega_shot.vel * dt
                    if bullet_is_offscreen(mega_shot, self.screen):
                        self.mega_shots.remove(mega_shot)
                    continue

                target_vector = mega_shot.target.pos - mega_shot.pos
                target_radius = getattr(mega_shot.target, "radius", 26)
                if target_vector.length_squared() <= (target_radius + mega_shot.radius) ** 2:
                    target = mega_shot.target
                    self.mega_shots.remove(mega_shot)
                    if isinstance(target, FinalBoss):
                        if target.shield > 0:
                            if mega_shot.charge_level >= MEGA_SHIELD_MIN_LEVEL:
                                target.shield -= 1
                                target.shield_down_since = now if target.shield == 0 else None
                                target.next_shield_recharge_time = None
                                explode(self.particles, target.pos, 12)
                                play_sound(self.explosion_sound)
                        elif mega_shot.charge_level >= MEGA_FINAL_KILL_LEVEL:
                            explode(self.particles, target.pos, 42)
                            play_sound(self.explosion_sound)
                            stop_looping_sound(self.bg_music_channel, BG_MUSIC_FADE_OUT_MS)
                            stop_audio()
                            play_sound(self.victory_sound)
                            return self._show_end_screen(True)
                        else:
                            target.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS
                        continue

                    if isinstance(target, Drone) and target in self.drones:
                        damage = mega_damage(mega_shot.charge_level)
                        target.incoming_damage = max(0, target.incoming_damage - damage)
                        target.hp -= damage
                        if target.hp > 0 and not target.is_mega:
                            self.drones.remove(target)
                            split_regular_drone(self.drones, target)
                            play_sound(self.split_sound)
                        elif target.hp <= 0:
                            pos = target.pos.copy()
                            counts_for_level = drone_counts_for_level(target)
                            self.drones.remove(target)
                            if counts_for_level:
                                self.destroyed += target.level_value
                            self.score += 100
                            explode(self.particles, pos)
                            play_sound(self.explosion_sound)
                        continue

                if target_vector.length_squared() > 0:
                    mega_shot.vel = target_vector.normalize() * mega_shot_speed(mega_shot.charge_level)
                add_shot_trail(self.shot_trails, mega_shot, now, 0.5625)
                mega_shot.pos += mega_shot.vel * dt

            self._update_particles(dt)
            self._update_shot_trails(dt)

            self._draw_frame(now)


def run_mission(screen, clock, base_dir, lesson_dir_name, valid_keys, player=None):
    previous_mouse_visible = pygame.mouse.get_visible()
    pygame.mouse.set_visible(False)
    try:
        return MissionEngine(screen, clock, base_dir, lesson_dir_name, valid_keys, player).run()
    finally:
        pygame.mouse.set_visible(previous_mouse_visible)
