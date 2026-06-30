from dataclasses import dataclass
import json
import math
import random
from pathlib import Path

import pygame
import cheats
import user_settings

from lessons.audio import (
    audio_duration_ms,
    load_first_sound,
    load_sound,
    play_audio,
    play_looping_sound,
    play_sound,
    stop_audio,
    stop_looping_sound,
)
from display_helpers import (
    SCREEN_SIZE as BASE_SCREEN_SIZE,
    enforce_16_9_window,
    is_letterboxed_fullscreen,
    set_fullscreen_16_9,
    set_windowed_16_9,
)
from lessons.key_render import display_key, render_inline_center, render_inline_text, render_key_label
from lessons.lesson_config import lesson_new_keys
import player_limits
from player_model import (
    DEFAULT_MISSION_SETTINGS,
    MAX_SPAWN_RATE_MULTIPLIER,
    MIN_SPAWN_RATE_MULTIPLIER,
    SPAWN_RATE_MULTIPLIER_STEP,
    normalize_mission_settings,
)


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
PLAYER_SPLASH_COLORS = {
    "red": (219, 92, 101),
    "orange": (240, 158, 74),
    "yellow": (246, 216, 79),
    "green": (88, 214, 141),
    "teal": (72, 209, 204),
    "cyan": (116, 211, 255),
    "blue": (112, 170, 255),
    "indigo": (112, 118, 255),
    "purple": (153, 92, 214),
    "pink": (238, 111, 176),
    "rose": (244, 124, 143),
    "gold": (255, 184, 77),
}
POD_ROTATION_SECONDS = 15
POD_IMAGE_SIZE = 204
PLAYER_COLLISION_RADIUS = 36
TURRET_IMAGE_SIZE = 108
DRONE_PIXELS_PER_ROTATION = 60
TURRET_TURN_SPEED = 25
TURRET_FIRE_ANGLE_THRESHOLD = 0.08
TURRET_FIRE_DELAY_MS = 90
# Cheat 14 auto-fire: engage drones within this fraction of half the screen
# height, toggled by tapping Left Ctrl this many times within the window.
AUTO_FIRE_RANGE_RATIO = 0.9
AUTO_FIRE_TOGGLE_TAPS = 5
AUTO_FIRE_TOGGLE_WINDOW_MS = 1500
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
# Defense drones only fire at enemies within this fraction of the smaller screen
# dimension from the pod, so they wait for drones to approach instead of picking
# off ones that are still far away / off screen.
DEFENSE_DRONE_ENGAGE_RANGE_RATIO = 0.9

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
FINAL_BOSS_COUNT_BY_LESSON = {}
MINI_BOSS_STRAFE_RANGE = 95
MINI_BOSS_STRAFE_SPEED_SCALE = 0.45
MINI_BOSS_CENTER_DISTANCE_SCALE = 0.25
NEW_KEY_ONLY_DRONES_PER_MISSION = 15
FINAL_BOSS_NEW_KEY_SPAWN_WEIGHT = 0.7
PLAYER_SHIELD_MAX_CHARGES = 3
PLAYER_SHIELD_START_LESSON = 3
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
MEGA_MINI_BOSS_KILL_LEVEL = 4
ACCURACY_SYSTEM_START_LESSON = 1
# --- Time Stop (see issue #19) ------------------------------------------
TIME_STOP_UNLOCK_LESSON = 26      # completing this lesson unlocks the ability
TIME_STOP_START_LESSON = 27       # power-ups only spawn from this lesson on
TIME_STOP_MAX_CHARGES = 3
TIME_STOP_DURATION_MS = 7000      # total time-stop duration
TIME_STOP_EXPAND_MS = 450         # ring sweep-out (freezes nearest objects first)
TIME_STOP_CONTRACT_MS = 1500      # slow recede at the end (un-freezes farthest first)
TIME_STOP_MIN_SPEED_SCALE = 0.0   # frozen objects' speed while inside the ring (0 = full stop)
TIME_STOP_POD_ROTATION_SCALE = 1.0 / 10.0  # pod + defense drones keep rotating at this fraction during a time stop
TIME_STOP_DOUBLE_TAP_MS = 600     # window for the 3 rapid spacebar taps
TIME_RING_COLOR = (170, 174, 184)     # grey ring
TIME_RING_INNER_COLOR = (210, 214, 222)
TIME_RING_ALPHA = 90                  # ring transparency (0-255)
TIME_STOP_POWER_UP_COLOR = (10, 10, 14)    # black hexagon
TIME_STOP_POWER_UP_EDGE = (236, 240, 255)  # white border
ACCURACY_MAX_CHARGES = 5
ACCURACY_RECHARGE_INTERVAL_MS = 3000
ACCURACY_THRESHOLD_BANDS = (
    (1, 3, 10, 10),
    (4, 9, 40, 30),
    (10, 19, 70, 60),
    (20, 29, 75, 65),
    (30, None, 80, 70),
)
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
BOSS_MUSIC_VOLUME = 0.42
BG_MUSIC_FADE_IN_MS = 1800
BG_MUSIC_FADE_OUT_MS = 700
BOSS_MUSIC_FADE_IN_MS = 1200
BOSS_MUSIC_FADE_OUT_MS = 700
BG_MUSIC_TRACK_COUNT = 3
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


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_boss_counts(counts):
    if not isinstance(counts, dict):
        return {}
    return {str(key): value for key, value in counts.items()}


def apply_game_settings(settings):
    global STARTING_LIVES, ENERGY_SAVER_BONUS_CREDITS, MAX_LIFE_POWER_UPS_PER_MISSION
    global POWER_UP_DURATION_MS, POWER_UP_WARNING_MS, POWER_UP_MIN_INTERVAL_MS, POWER_UP_MAX_INTERVAL_MS
    global PLAYER_SHIELD_MAX_CHARGES, PLAYER_SHIELD_START_LESSON
    global PLAYER_ACTIVE_SHIELD_DURATION_MS, PLAYER_ACTIVE_SHIELD_FADE_START_MS, PLAYER_ACTIVE_SHIELD_EXTRA_HITS
    global DEFENSE_DRONE_FIRE_INTERVAL_MS, DEFENSE_DRONE_ACCURACY_GRACE_MS
    global MEGA_CHARGE_MAX_BLOCKS, MEGA_RECHARGE_INTERVAL_MS, MEGA_RECHARGE_DELAY_MS
    global MEGA_SHIELD_MIN_LEVEL, MEGA_FINAL_KILL_LEVEL
    global FINAL_BOSS_ATTACK_INTERVAL_MS, FINAL_BOSS_SEMI_BOSS_FIRST_SPAWN_MS, FINAL_BOSS_SEMI_BOSS_SPAWN_INTERVAL_MS
    global FINAL_BOSS_COUNT_BY_LESSON
    global ACCURACY_THRESHOLD_BANDS
    global TIME_STOP_DURATION_MS, TIME_STOP_EXPAND_MS, TIME_STOP_CONTRACT_MS
    global TIME_STOP_MIN_SPEED_SCALE, TIME_STOP_MAX_CHARGES, TIME_STOP_START_LESSON
    global TIME_STOP_UNLOCK_LESSON, TIME_STOP_DOUBLE_TAP_MS, TIME_RING_ALPHA
    if not isinstance(settings, dict):
        return
    STARTING_LIVES = _safe_int(settings.get("starting_lives", STARTING_LIVES), STARTING_LIVES)
    player_limits.MAX_PLAYER_LIVES = _safe_int(
        settings.get("max_player_lives", player_limits.MAX_PLAYER_LIVES), player_limits.MAX_PLAYER_LIVES
    )
    PLAYER_SHIELD_MAX_CHARGES = _safe_int(settings.get("player_shield_max_charges", PLAYER_SHIELD_MAX_CHARGES), PLAYER_SHIELD_MAX_CHARGES)
    ENERGY_SAVER_BONUS_CREDITS = _safe_int(settings.get("energy_saver_bonus_credits", ENERGY_SAVER_BONUS_CREDITS), ENERGY_SAVER_BONUS_CREDITS)
    MAX_LIFE_POWER_UPS_PER_MISSION = _safe_int(settings.get("max_life_power_ups_per_mission", MAX_LIFE_POWER_UPS_PER_MISSION), MAX_LIFE_POWER_UPS_PER_MISSION)
    POWER_UP_DURATION_MS = _safe_int(settings.get("power_up_duration_ms", POWER_UP_DURATION_MS), POWER_UP_DURATION_MS)
    POWER_UP_WARNING_MS = _safe_int(settings.get("power_up_warning_ms", POWER_UP_WARNING_MS), POWER_UP_WARNING_MS)
    POWER_UP_MIN_INTERVAL_MS = _safe_int(settings.get("power_up_min_interval_ms", POWER_UP_MIN_INTERVAL_MS), POWER_UP_MIN_INTERVAL_MS)
    POWER_UP_MAX_INTERVAL_MS = _safe_int(settings.get("power_up_max_interval_ms", POWER_UP_MAX_INTERVAL_MS), POWER_UP_MAX_INTERVAL_MS)
    PLAYER_SHIELD_START_LESSON = _safe_int(settings.get("player_shield_start_lesson", PLAYER_SHIELD_START_LESSON), PLAYER_SHIELD_START_LESSON)
    PLAYER_ACTIVE_SHIELD_DURATION_MS = _safe_int(settings.get("player_active_shield_duration_ms", PLAYER_ACTIVE_SHIELD_DURATION_MS), PLAYER_ACTIVE_SHIELD_DURATION_MS)
    PLAYER_ACTIVE_SHIELD_FADE_START_MS = _safe_int(settings.get("player_active_shield_fade_start_ms", PLAYER_ACTIVE_SHIELD_FADE_START_MS), PLAYER_ACTIVE_SHIELD_FADE_START_MS)
    PLAYER_ACTIVE_SHIELD_EXTRA_HITS = _safe_int(settings.get("player_active_shield_extra_hits", PLAYER_ACTIVE_SHIELD_EXTRA_HITS), PLAYER_ACTIVE_SHIELD_EXTRA_HITS)
    DEFENSE_DRONE_FIRE_INTERVAL_MS = _safe_int(settings.get("defense_drone_fire_interval_ms", DEFENSE_DRONE_FIRE_INTERVAL_MS), DEFENSE_DRONE_FIRE_INTERVAL_MS)
    DEFENSE_DRONE_ACCURACY_GRACE_MS = _safe_int(settings.get("defense_drone_accuracy_grace_ms", DEFENSE_DRONE_ACCURACY_GRACE_MS), DEFENSE_DRONE_ACCURACY_GRACE_MS)
    MEGA_CHARGE_MAX_BLOCKS = _safe_int(settings.get("mega_charge_max_blocks", MEGA_CHARGE_MAX_BLOCKS), MEGA_CHARGE_MAX_BLOCKS)
    MEGA_RECHARGE_INTERVAL_MS = _safe_int(settings.get("mega_recharge_interval_ms", MEGA_RECHARGE_INTERVAL_MS), MEGA_RECHARGE_INTERVAL_MS)
    MEGA_RECHARGE_DELAY_MS = _safe_int(settings.get("mega_recharge_delay_ms", MEGA_RECHARGE_DELAY_MS), MEGA_RECHARGE_DELAY_MS)
    MEGA_SHIELD_MIN_LEVEL = _safe_int(settings.get("mega_shield_min_level", MEGA_SHIELD_MIN_LEVEL), MEGA_SHIELD_MIN_LEVEL)
    MEGA_FINAL_KILL_LEVEL = _safe_int(settings.get("mega_final_kill_level", MEGA_FINAL_KILL_LEVEL), MEGA_FINAL_KILL_LEVEL)
    FINAL_BOSS_ATTACK_INTERVAL_MS = _safe_int(settings.get("final_boss_attack_interval_ms", FINAL_BOSS_ATTACK_INTERVAL_MS), FINAL_BOSS_ATTACK_INTERVAL_MS)
    FINAL_BOSS_SEMI_BOSS_FIRST_SPAWN_MS = _safe_int(
        settings.get("final_boss_semi_boss_first_spawn_ms", FINAL_BOSS_SEMI_BOSS_FIRST_SPAWN_MS),
        FINAL_BOSS_SEMI_BOSS_FIRST_SPAWN_MS,
    )
    FINAL_BOSS_SEMI_BOSS_SPAWN_INTERVAL_MS = _safe_int(
        settings.get("final_boss_semi_boss_spawn_interval_ms", FINAL_BOSS_SEMI_BOSS_SPAWN_INTERVAL_MS),
        FINAL_BOSS_SEMI_BOSS_SPAWN_INTERVAL_MS,
    )
    counts = settings.get("final_boss_count_by_lesson", FINAL_BOSS_COUNT_BY_LESSON)
    FINAL_BOSS_COUNT_BY_LESSON = _normalize_boss_counts(counts)
    ACCURACY_THRESHOLD_BANDS = normalize_accuracy_threshold_bands(
        settings.get("accuracy_threshold_bands", ACCURACY_THRESHOLD_BANDS)
    )
    TIME_STOP_DURATION_MS = _safe_int(settings.get("time_stop_duration_ms", TIME_STOP_DURATION_MS), TIME_STOP_DURATION_MS)
    TIME_STOP_EXPAND_MS = _safe_int(settings.get("time_stop_expand_ms", TIME_STOP_EXPAND_MS), TIME_STOP_EXPAND_MS)
    TIME_STOP_CONTRACT_MS = _safe_int(settings.get("time_stop_contract_ms", TIME_STOP_CONTRACT_MS), TIME_STOP_CONTRACT_MS)
    TIME_STOP_MIN_SPEED_SCALE = _safe_float(settings.get("time_stop_min_speed_scale", TIME_STOP_MIN_SPEED_SCALE), TIME_STOP_MIN_SPEED_SCALE)
    TIME_STOP_MAX_CHARGES = _safe_int(settings.get("time_stop_max_charges", TIME_STOP_MAX_CHARGES), TIME_STOP_MAX_CHARGES)
    TIME_STOP_START_LESSON = _safe_int(settings.get("time_stop_start_lesson", TIME_STOP_START_LESSON), TIME_STOP_START_LESSON)
    TIME_STOP_UNLOCK_LESSON = _safe_int(settings.get("time_stop_unlock_lesson", TIME_STOP_UNLOCK_LESSON), TIME_STOP_UNLOCK_LESSON)
    TIME_STOP_DOUBLE_TAP_MS = _safe_int(settings.get("time_stop_double_tap_ms", TIME_STOP_DOUBLE_TAP_MS), TIME_STOP_DOUBLE_TAP_MS)
    TIME_RING_ALPHA = _safe_int(settings.get("time_ring_alpha", TIME_RING_ALPHA), TIME_RING_ALPHA)


def normalize_accuracy_threshold_bands(value):
    if not isinstance(value, (list, tuple)):
        return ACCURACY_THRESHOLD_BANDS
    bands = []
    for item in value:
        if isinstance(item, dict):
            start = item.get("start")
            end = item.get("end")
            warning_threshold = item.get("warning_threshold")
            limited_threshold = item.get("limited_threshold")
        elif isinstance(item, (list, tuple)) and len(item) == 4:
            start, end, warning_threshold, limited_threshold = item
        else:
            continue
        try:
            start = int(start)
            end = None if end is None else int(end)
            warning_threshold = int(warning_threshold)
            limited_threshold = int(limited_threshold)
        except (TypeError, ValueError):
            continue
        if start < 1 or (end is not None and end < start):
            continue
        if not 0 <= limited_threshold <= warning_threshold <= 100:
            continue
        bands.append((start, end, warning_threshold, limited_threshold))
    return tuple(bands) if bands else ACCURACY_THRESHOLD_BANDS


def accuracy_thresholds_for_lesson(lesson_number):
    for start, end, warning_threshold, limited_threshold in ACCURACY_THRESHOLD_BANDS:
        if lesson_number >= start and (end is None or lesson_number <= end):
            return warning_threshold, limited_threshold
    return 100, 100


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
    incoming_defense_damage: int = 0
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


class TimeStopRing:
    """Expanding/contracting time-stop ring emanating from the ship.

    Objects within the ring's current radius are frozen. The ring expands
    outward (freezing the nearest first), holds, then contracts (un-freezing
    the farthest first), so freeze and release sweep through the field.
    """

    def __init__(self, duration_ms, expand_ms, contract_ms, min_speed_scale, center, max_radius):
        self.duration_ms = max(1, int(duration_ms))
        self.expand_ms = max(1, int(expand_ms))
        self.contract_ms = max(1, int(contract_ms))
        # Always keep a hold phase, even if expand+contract were set too long.
        if self.expand_ms + self.contract_ms > self.duration_ms:
            total = self.expand_ms + self.contract_ms
            self.expand_ms = max(1, int(self.duration_ms * self.expand_ms / total))
            self.contract_ms = max(1, self.duration_ms - self.expand_ms)
        self.min_speed_scale = max(0.0, min(1.0, float(min_speed_scale)))
        self.center = pygame.Vector2(center)
        self.max_radius = max(1.0, float(max_radius))
        self.elapsed_ms = 0.0
        self.active = True

    def update(self, dt_ms):
        if not self.active:
            return
        self.elapsed_ms += dt_ms
        if self.elapsed_ms >= self.duration_ms:
            self.elapsed_ms = self.duration_ms
            self.active = False

    def radius(self):
        contract_start = self.duration_ms - self.contract_ms
        if self.elapsed_ms <= self.expand_ms:
            return self.max_radius * (self.elapsed_ms / self.expand_ms)
        if self.elapsed_ms < contract_start:
            return self.max_radius
        remaining = max(0.0, self.duration_ms - self.elapsed_ms)
        return self.max_radius * (remaining / self.contract_ms)

    def object_time_scale(self, distance, ring_radius=None):
        radius = self.radius() if ring_radius is None else ring_radius
        return self.min_speed_scale if distance <= radius else 1.0

    def is_contracting(self):
        return self.elapsed_ms >= (self.duration_ms - self.contract_ms)


def toggle_fullscreen():
    screen = pygame.display.get_surface()
    if is_letterboxed_fullscreen() or screen.get_flags() & pygame.FULLSCREEN:
        surface = set_windowed_16_9(user_settings.window_size())
        user_settings.set_display_state(False, surface.get_size())
        return surface
    surface = set_fullscreen_16_9()
    user_settings.set_display_state(True)
    return surface


def enforce_min_window_size(screen):
    surface = enforce_16_9_window(screen)
    if not is_letterboxed_fullscreen() and not (surface.get_flags() & pygame.FULLSCREEN):
        user_settings.set_display_state(False, surface.get_size())
    return surface


def load_image(path):
    try:
        return pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        return None


def bg_music_path(sfx_dir, lesson_number):
    track_number = ((lesson_number - 1) % BG_MUSIC_TRACK_COUNT) + 1
    return sfx_dir / f"bg_music_{track_number}.wav"


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
    track_rect = None
    thumb_rect = None
    if max_scroll:
        track_rect = pygame.Rect(rect.right - 8, rect.y + 6, 4, rect.height - 12)
        pygame.draw.rect(surface, (30, 42, 68), track_rect, border_radius=2)
        visible_height = max(1, rect.height - 44)
        content_height = max(visible_height, len(lines) * line_height)
        thumb_height = max(18, int(track_rect.height * visible_height / content_height))
        travel = max(1, track_rect.height - thumb_height)
        thumb_y = track_rect.y + int(travel * scroll_y / max_scroll)
        thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
        pygame.draw.rect(surface, ACCENT, thumb_rect, border_radius=2)
    return max_scroll, track_rect, thumb_rect


SHIFTED_SYMBOL_START_LESSON = 27


def event_to_lesson_key(event, lesson_number=1):
    if lesson_number >= SHIFTED_SYMBOL_START_LESSON and event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
        return None
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


def player_advanced_mega_shot_available(player, lesson_number):
    if lesson_number >= 20:
        return True
    if not isinstance(player, dict):
        return False
    return 19 in set(player.get("completed_lessons", []))


def final_boss_count(lesson_number):
    if lesson_number < 5:
        return 0
    configured = FINAL_BOSS_COUNT_BY_LESSON.get(str(lesson_number), 1)
    try:
        return max(0, int(configured))
    except (TypeError, ValueError):
        return 1


def final_boss_enabled(lesson_number):
    return final_boss_count(lesson_number) > 0


def mission_target_keys(valid_keys, lesson_number, mega_available=False):
    return tuple(
        key
        for key in valid_keys
        if not ((mega_shot_enabled(lesson_number) or mega_available) and key == "space")
        and not (lesson_number >= SHIFTED_SYMBOL_START_LESSON and key == "shift")
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


def time_stop_power_up_enabled(lesson_number):
    return lesson_number >= TIME_STOP_START_LESSON


def player_time_stop_available(player, lesson_number):
    # Unlocked once level 26 is completed; usable in any level afterward.
    if lesson_number > TIME_STOP_UNLOCK_LESSON:
        return True
    if not isinstance(player, dict):
        return False
    return TIME_STOP_UNLOCK_LESSON in set(player.get("completed_lessons", []))


# DEFAULT_MISSION_SETTINGS, the spawn-rate bounds, and normalize_mission_settings
# are defined in player_model and imported above, so there is a single source of
# truth shared by the data layer and the mission engine.


def player_mission_settings(player):
    if not isinstance(player, dict):
        return dict(DEFAULT_MISSION_SETTINGS)
    settings = normalize_mission_settings(player.get("mission_settings", {}))
    player["mission_settings"] = settings
    return settings


def player_upgrade_ids(player):
    if not isinstance(player, dict):
        return set()
    ids = {
        str(upgrade_id).strip()
        for upgrade_id in player.get("purchased_upgrade_ids", [])
        if str(upgrade_id).strip()
    }
    pod = player.get("pod", {})
    upgrades = pod.get("upgrades", []) if isinstance(pod, dict) else []
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


def player_splash_rgb(color_name):
    if isinstance(color_name, str) and color_name.strip():
        key = color_name.strip().lower().replace(" ", "_")
        return PLAYER_SPLASH_COLORS.get(key, PLAYER_SPLASH_COLORS["blue"])
    return PLAYER_SPLASH_COLORS["blue"]


def player_shield_max_charges(player):
    max_charges = PLAYER_SHIELD_MAX_CHARGES
    upgrades = player_upgrade_ids(player)
    if "extra_shield_slot_1" in upgrades:
        max_charges += 1
    if "extra_shield_slot_2" in upgrades:
        max_charges += 1
    achievements = player.get("achievements", []) if isinstance(player, dict) else []
    if "fully_upgraded" in achievements:
        max_charges += 1
    return max_charges


def player_defense_drone_count(player):
    upgrades = player_upgrade_ids(player)
    achievements = player.get("achievements", {}) if isinstance(player, dict) else {}
    earned_achievements = (
        {achievement_id for achievement_id, awarded in achievements.items() if awarded}
        if isinstance(achievements, dict)
        else set(achievements if isinstance(achievements, list) else [])
    )
    count = 0
    if "defense_drone" in upgrades:
        count += 1
    if "second_defense_drone" in upgrades:
        count += 1
    if "major_rank" in earned_achievements:
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
    pool = available_keys or list(valid_keys)
    return random.choice(pool) if pool else ""


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
        return []
    child_hp = max(1, drone.hp)
    spread = max(18, drone.radius * 0.7)
    children = []
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
        children.append(child)
    return children


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
    time_stop_enabled=False,
    time_stop_charges=0,
    max_time_stop_charges=TIME_STOP_MAX_CHARGES,
):
    width, height = screen.get_size()
    margin = 90
    power_up_keys = [key for key in valid_keys if len(key) == 1 and key.isalpha()] or list(valid_keys)
    if not power_up_keys:
        return None
    keys = random.choices(power_up_keys, k=2)
    kinds = []
    if shield_enabled and shield_charges < max_shield_charges:
        kinds.append("shield")
    if life_enabled:
        kinds.append("life")
    if time_stop_enabled and time_stop_charges < max_time_stop_charges:
        kinds.append("time_stop")
    if not kinds:
        return None
    kind = random.choice(kinds)
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
    return drone.incoming_damage < regular_drone_shot_capacity(drone)


def regular_drone_shot_capacity(drone):
    if drone.is_mega:
        return max(0, drone.hp)
    return max(1, (2 ** max(1, drone.hp)) - 1)


def drone_remaining_shot_capacity(drone):
    return max(0, regular_drone_shot_capacity(drone) - drone.incoming_damage)


def defense_drone_remaining_shot_capacity(drone):
    return max(0, regular_drone_shot_capacity(drone) - drone.incoming_defense_damage)


def nearest_drone_for_key(drones, key, center):
    matches = [drone for drone in drones if drone.letter == key and can_target_drone(drone)]
    if not matches:
        return None
    return min(matches, key=lambda drone: drone.pos.distance_squared_to(center))


def nearest_targetable_drone_in_range(drones, center, max_range):
    max_sq = max_range * max_range
    matches = [
        drone
        for drone in drones
        if can_target_drone(drone) and drone.pos.distance_squared_to(center) <= max_sq
    ]
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


def target_is_available(target, drones, final_bosses):
    if isinstance(target, Drone):
        return target in drones
    if isinstance(final_bosses, FinalBoss):
        final_bosses = [final_bosses]
    return isinstance(target, FinalBoss) and target in final_bosses


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


def mega_damage_for_target(target, charge_level):
    level = max(1, min(MEGA_CHARGE_MAX_BLOCKS, charge_level))
    if isinstance(target, Drone) and target.is_mega:
        return target.hp if level >= MEGA_MINI_BOSS_KILL_LEVEL else level + 1
    return mega_damage(level)


def mega_charge_required_for_target(target):
    if isinstance(target, FinalBoss):
        return MEGA_FINAL_KILL_LEVEL
    if isinstance(target, Drone):
        if target.is_mega:
            return MEGA_MINI_BOSS_KILL_LEVEL
        return max(1, min(MEGA_CHARGE_MAX_BLOCKS, target.max_hp))
    return MEGA_CHARGE_MAX_BLOCKS


MEGA_SHOT_SPEED_BASE = 820
MEGA_SHOT_SPEED_MULTIPLIERS = {
    2: 1.10,
    3: 1.20,
    4: 1.40,
    5: 1.80,
}


def mega_shot_speed(charge_level):
    level = max(1, min(MEGA_CHARGE_MAX_BLOCKS, charge_level))
    return MEGA_SHOT_SPEED_BASE * MEGA_SHOT_SPEED_MULTIPLIERS.get(level, 1.0)


# --- Scoring (see issue #15) ------------------------------------------------
DRONE_HIT_SCORE = 100          # per damaging hit on a regular (splitting) drone
MINI_BOSS_SCORE = 200          # purple semi-boss, awarded on kill
MINI_BOSS_MEGA_BONUS = 100     # extra for a one-Mega-Shot semi-boss kill
FINAL_BOSS_SCORE = 1000        # per final boss defeated
POWER_UP_SCORE = 100           # per power-up collected
HIGH_SCORE_FLAT_BONUS = 500    # the standalone flat term in the goal
HIGH_SCORE_BASE_BONUS = 2000   # the trailing "+ 2000" term in the goal


def regular_drone_clear_score(hp):
    # A splitting drone of N hp takes 2^N - 1 total hits to clear, each worth 100.
    return DRONE_HIT_SCORE * ((2 ** max(1, int(hp))) - 1)


def mega_kill_bonus(max_hp):
    hp = max(1, int(max_hp))
    if hp >= 3:
        return 100   # red
    if hp == 2:
        return 50    # orange
    return 0         # yellow / boss-shot


def high_score_goal(drone_target, power_up_count, final_boss_value, semi_boss_count):
    return (
        int(drone_target) * 100
        + int(power_up_count) * 100
        + HIGH_SCORE_FLAT_BONUS
        + int(final_boss_value)
        + int(semi_boss_count) * 200
        + HIGH_SCORE_BASE_BONUS
    )


# --- Level timing (see issue #16) -------------------------------------------
DEFAULT_QUICK_DEFENDER_MS = 60000   # placeholder; not yet tuned per level
QUICK_DEFENDER_TIME_GOALS = {}      # {lesson_number: milliseconds}; edit to tune


def quick_defender_goal_ms(lesson_number):
    return int(QUICK_DEFENDER_TIME_GOALS.get(lesson_number, DEFAULT_QUICK_DEFENDER_MS))


def format_mission_time(ms):
    total_seconds = max(0, int(ms) // 1000)
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


MAX_LEVEL_TIME_MS = 999990  # 999.99s; the level timer stops counting past this


def format_level_timer(ms):
    capped = min(MAX_LEVEL_TIME_MS, max(0, int(ms)))
    return f"T: {capped / 1000:.2f}"


def mega_target(drones, final_bosses, key, center):
    if isinstance(final_bosses, FinalBoss):
        final_bosses = [final_bosses]
    boss_matches = [boss for boss in (final_bosses or []) if boss.letter == key]
    if boss_matches:
        return min(boss_matches, key=lambda boss: boss.pos.distance_squared_to(center))
    return nearest_drone_for_key(drones, key, center)


def queue_mega_shot(drones, final_bosses, pending_shots, key, center, charge_level, now, advanced=False):
    target = mega_target(drones, final_bosses, key, center)
    if target is None:
        return 0
    charge_level = max(1, min(MEGA_CHARGE_MAX_BLOCKS, charge_level))
    if advanced:
        charge_level = min(charge_level, mega_charge_required_for_target(target))
    damage = mega_damage_for_target(target, charge_level)
    if isinstance(target, Drone):
        target.incoming_damage += damage
    pending_shots.append(PendingShot(target=target, damage=damage, created_at=now, mega_charge_level=charge_level))
    return charge_level


def release_pending_shot(pending_shot):
    if isinstance(pending_shot.target, Drone):
        pending_shot.target.incoming_damage = max(
            0,
            pending_shot.target.incoming_damage - pending_shot.damage,
        )


def reserve_split_child_target(children, damage=1):
    available = [child for child in children if drone_remaining_shot_capacity(child) >= damage]
    if not available:
        return None
    target = min(available, key=lambda child: (child.incoming_damage, child.pos.y))
    target.incoming_damage += damage
    return target


def reserve_split_child_defense_target(children, damage=1):
    available = [child for child in children if defense_drone_remaining_shot_capacity(child) >= damage]
    if not available:
        return None
    target = min(available, key=lambda child: (child.incoming_defense_damage, child.pos.y))
    target.incoming_defense_damage += damage
    return target


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


def spawn_final_boss(screen, now, valid_keys, player_center, focus_keys=(), index=0, total=1):
    width, height = screen.get_size()
    total = max(1, int(total))
    if total == 1:
        y = height / 2
    else:
        min_y = height * FINAL_BOSS_VERTICAL_MIN_RATIO + FINAL_BOSS_RADIUS
        max_y = height * FINAL_BOSS_VERTICAL_MAX_RATIO - FINAL_BOSS_RADIUS
        y = min_y + (max_y - min_y) * index / max(1, total - 1)
    spawn_pos = pygame.Vector2(-FINAL_BOSS_RADIUS - 28 - index * (FINAL_BOSS_RADIUS * 0.7), y)
    target_x = spawn_pos.x + (player_center.x - spawn_pos.x) * FINAL_BOSS_ENTRY_PROGRESS
    target_pos = pygame.Vector2(target_x, y)
    return FinalBoss(
        pos=spawn_pos,
        target_pos=target_pos,
        letter=random_spawn_key(valid_keys, preferred_keys=focus_keys, preferred_weight=1.0),
        orbit_angle=(index / total) * math.tau,
        orbit_radius=0,
        orbit_direction=1 if index % 2 == 0 else -1,
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


def draw_shot_trails(screen, shot_trails, color=SHOT_TRAIL_COLOR):
    for particle in shot_trails:
        alpha_scale = max(0, min(1, particle.ttl / particle.max_ttl))
        radius = max(1, int(particle.radius * alpha_scale))
        size = radius * 2 + 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        alpha = int(135 * alpha_scale)
        pygame.draw.circle(surface, (*color, alpha), (size // 2, size // 2), radius)
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


def draw_defense_shot(screen, shot, color=BULLET_COLOR):
    pygame.draw.circle(screen, color, shot.pos, DEFENSE_DRONE_SHOT_RADIUS)


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
    center = pygame.Vector2(size / 2, size / 2)
    label_color = (5, 24, 12)
    if power_up.kind == "shield":
        shape_rect = pygame.Rect(0, 0, 56, 56)
        shape_rect.center = center
        pygame.draw.rect(surface, SHIELD_POWER_UP_COLOR, shape_rect, border_radius=4)
        pygame.draw.rect(surface, (225, 246, 255), shape_rect, 3, border_radius=4)
    elif power_up.kind == "time_stop":
        radius = 30
        points = [
            (
                center.x + radius * math.cos(math.pi / 6 + index * math.pi / 3),
                center.y + radius * math.sin(math.pi / 6 + index * math.pi / 3),
            )
            for index in range(6)
        ]
        pygame.draw.polygon(surface, TIME_STOP_POWER_UP_COLOR, points)
        pygame.draw.polygon(surface, TIME_STOP_POWER_UP_EDGE, points, 3)
        label_color = (236, 240, 255)
    else:
        points = (
            (center.x, 7),
            (size - 7, center.y),
            (center.x, size - 7),
            (7, center.y),
        )
        pygame.draw.polygon(surface, POWER_UP_COLOR, points)
        pygame.draw.polygon(surface, (226, 255, 235), points, 3)

    label_text = " ".join(display_key(key) for key in power_up.letters)
    label_font = pygame.font.SysFont("arial", 24, bold=True)
    render_inline_center(surface, label_text, label_font, label_color, center)

    if power_up.progress:
        pip_rect = pygame.Rect(12, size - 14, 24, 4)
        pygame.draw.rect(surface, label_color, pip_rect)
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


def draw_time_stop_bar(screen, font, charges, enabled, y_offset=0, max_charges=TIME_STOP_MAX_CHARGES, center_x=None):
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

    frame_color = (150, 130, 210)
    empty_color = (24, 22, 40)
    ring_color = (200, 180, 255)
    for index in range(max_charges):
        block_rect = pygame.Rect(bar_rect.x + index * (block_size + gap), bar_rect.y, block_size, block_size)
        pygame.draw.rect(screen, empty_color, block_rect, border_radius=4)
        pygame.draw.rect(screen, frame_color, block_rect, 2, border_radius=4)
        if index < charges:
            icon = pygame.Surface((block_size, block_size), pygame.SRCALPHA)
            middle = block_size // 2
            for radius in (block_size // 2 - 3, block_size // 2 - 7):
                if radius > 0:
                    pygame.draw.circle(icon, (*ring_color, 210), (middle, middle), radius, 2)
            screen.blit(icon, block_rect)

    text_surface = font.render("Time Stop", True, ring_color if charges else (80, 78, 100))
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


def draw_hud(screen, font, destroyed, drone_target, score, lives, level_time_ms=None):
    width, _ = screen.get_size()
    left = f"Drones destroyed: {int(destroyed)}/{drone_target}"
    right = f"Score: {score}"
    life = f"Lives: {lives}"
    screen.blit(font.render(left, True, TEXT_COLOR), (22, 18))
    score_surface = font.render(right, True, TEXT_COLOR)
    if level_time_ms is None:
        score_x = width - score_surface.get_width() - 22
    else:
        # Timer sits to the right of the score in the top-right corner.
        timer_surface = font.render(format_level_timer(level_time_ms), True, TEXT_COLOR)
        timer_x = width - timer_surface.get_width() - 22
        score_x = timer_x - 24 - score_surface.get_width()
        screen.blit(timer_surface, (timer_x, 18))
    screen.blit(score_surface, (score_x, 18))
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
    bonus_points=0,
    level_time_ms=0,
):
    title_font = pygame.font.SysFont("arial", 56, bold=True)
    body_font = pygame.font.SysFont("arial", 24)
    small_font = pygame.font.SysFont("arial", 20)
    title = "MISSION COMPLETE" if won else "MISSION FAILED"
    destroyed_count = int(min(destroyed, drone_target))
    accuracy_inputs = accurate_inputs + inaccurate_inputs
    accuracy_percent = 100 if accuracy_inputs == 0 else round(accurate_inputs * 100 / accuracy_inputs)
    # `score` is the grand total (base + bonus). Show its components plus the total.
    base_points = max(0, score - bonus_points)
    rows = [
        ("Points", str(base_points)),
        ("Bonus points", str(bonus_points)),
        ("Total level score", str(score)),
        ("Time", format_mission_time(level_time_ms)),
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
        modal_rect = pygame.Rect(0, 0, min(620, width - 80), min(780, height - 24))
        modal_rect.center = (width / 2, height / 2)
        pygame.draw.rect(screen, (10, 18, 34), modal_rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT if won else THREE_SHOT_DRONE_COLOR, modal_rect, 2, border_radius=8)
        title_surface = title_font.render(title, True, ACCENT if won else THREE_SHOT_DRONE_COLOR)
        screen.blit(title_surface, title_surface.get_rect(center=(width / 2, modal_rect.y + 60)))
        for index, (label, value) in enumerate(rows):
            y = modal_rect.y + 116 + index * 34
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


def draw_checkbox(surface, rect, checked, enabled=True):
    border = ACCENT if enabled else (70, 76, 92)
    fill = (18, 30, 55) if enabled else (16, 18, 26)
    pygame.draw.rect(surface, fill, rect, border_radius=4)
    pygame.draw.rect(surface, border, rect, 2, border_radius=4)
    if checked:
        color = TEXT_COLOR if enabled else MUTED_TEXT
        pygame.draw.line(surface, color, (rect.x + 5, rect.centery), (rect.x + 11, rect.bottom - 6), 3)
        pygame.draw.line(surface, color, (rect.x + 11, rect.bottom - 6), (rect.right - 5, rect.y + 6), 3)


def draw_mission_settings_modal(screen, settings, unlocks, controls, title_font, body_font, small_font):
    width, height = screen.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((2, 5, 13, 210))
    screen.blit(overlay, (0, 0))
    modal_rect = pygame.Rect(0, 0, min(680, width - 80), min(560, height - 54))
    modal_rect.center = (width / 2, height / 2)
    pygame.draw.rect(screen, (10, 18, 34), modal_rect, border_radius=8)
    pygame.draw.rect(screen, ACCENT, modal_rect, 2, border_radius=8)
    title = title_font.render("MISSION OPTIONS", True, TEXT_COLOR)
    screen.blit(title, (modal_rect.x + 30, modal_rect.y + 26))

    rows = (
        ("disable_defense_drones", "Disable Defense Drones", "Requires at least one defense drone."),
        ("disable_mega_shot", "Disable Power Shot", "Requires Mega Shot to be unlocked."),
        ("disable_shields", "Disable Shields", "Requires shields to be unlocked."),
        ("music_enabled", "Music Loop", ""),
    )
    controls.clear()
    row_y = modal_rect.y + 102
    for key, label, locked_text in rows:
        enabled = unlocks.get(key, True)
        rect = pygame.Rect(modal_rect.x + 34, row_y + 3, 26, 26)
        controls[key] = rect
        checked = bool(settings[key])
        draw_checkbox(screen, rect, checked, enabled)
        text_color = TEXT_COLOR if enabled else MUTED_TEXT
        label_surface = body_font.render(label, True, text_color)
        screen.blit(label_surface, (rect.right + 14, row_y))
        if not enabled and locked_text:
            locked_surface = small_font.render(locked_text, True, (104, 112, 134))
            screen.blit(locked_surface, (rect.right + 16, row_y + 28))
        row_y += 58

    slider_y = row_y + 42
    slider_label = body_font.render(f"Spawn Rate: {settings['spawn_rate_multiplier']:.1f}x", True, TEXT_COLOR)
    screen.blit(slider_label, (modal_rect.x + 34, slider_y - 42))
    track_rect = pygame.Rect(modal_rect.x + 38, slider_y, modal_rect.width - 168, 8)
    pygame.draw.rect(screen, (43, 57, 89), track_rect, border_radius=4)
    normalized = (
        settings["spawn_rate_multiplier"] - MIN_SPAWN_RATE_MULTIPLIER
    ) / (MAX_SPAWN_RATE_MULTIPLIER - MIN_SPAWN_RATE_MULTIPLIER)
    knob_x = track_rect.x + int(track_rect.width * normalized)
    knob_rect = pygame.Rect(0, 0, 22, 34)
    knob_rect.center = (knob_x, track_rect.centery)
    pygame.draw.rect(screen, ACCENT, knob_rect, border_radius=6)
    controls["spawn_rate_track"] = track_rect
    controls["spawn_rate_knob"] = knob_rect
    min_label = small_font.render("1x", True, MUTED_TEXT)
    max_label = small_font.render("5x", True, MUTED_TEXT)
    screen.blit(min_label, (track_rect.x, track_rect.bottom + 12))
    screen.blit(max_label, (track_rect.right - max_label.get_width(), track_rect.bottom + 12))

    close_rect = pygame.Rect(modal_rect.right - 164, modal_rect.bottom - 64, 130, 42)
    controls["close"] = close_rect
    draw_button(screen, close_rect, "Done", body_font, True)
    hint = small_font.render("Click checkboxes, drag/click slider, or press Esc/O to close.", True, MUTED_TEXT)
    screen.blit(hint, (modal_rect.x + 34, modal_rect.bottom - 50))


def set_spawn_rate_from_mouse(settings, track_rect, mouse_x):
    if track_rect.width <= 0:
        return
    ratio = max(0, min(1, (mouse_x - track_rect.x) / track_rect.width))
    value = MIN_SPAWN_RATE_MULTIPLIER + ratio * (MAX_SPAWN_RATE_MULTIPLIER - MIN_SPAWN_RATE_MULTIPLIER)
    settings["spawn_rate_multiplier"] = max(
        MIN_SPAWN_RATE_MULTIPLIER,
        min(MAX_SPAWN_RATE_MULTIPLIER, round(round(value / SPAWN_RATE_MULTIPLIER_STEP) * SPAWN_RATE_MULTIPLIER_STEP, 1)),
    )


def save_mission_settings(player, settings):
    if isinstance(player, dict):
        player["mission_settings"] = dict(settings)


def mission_settings_modal(screen, clock, player, settings, unlocks):
    title_font = pygame.font.SysFont("arial", 40, bold=True)
    body_font = pygame.font.SysFont("arial", 23)
    small_font = pygame.font.SysFont("arial", 16)
    controls = {}
    dragging_slider = False
    background = screen.copy()
    while True:
        screen = pygame.display.get_surface()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.VIDEORESIZE:
                screen = enforce_min_window_size(screen)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_o, pygame.K_RETURN, pygame.K_SPACE):
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if controls.get("close") and controls["close"].collidepoint(event.pos):
                    return None
                if controls.get("spawn_rate_track") and controls["spawn_rate_track"].collidepoint(event.pos):
                    set_spawn_rate_from_mouse(settings, controls["spawn_rate_track"], event.pos[0])
                    save_mission_settings(player, settings)
                    dragging_slider = True
                    continue
                if controls.get("spawn_rate_knob") and controls["spawn_rate_knob"].collidepoint(event.pos):
                    dragging_slider = True
                    continue
                for key in ("disable_defense_drones", "disable_mega_shot", "disable_shields", "music_enabled"):
                    rect = controls.get(key)
                    if rect is not None and rect.collidepoint(event.pos) and unlocks.get(key, True):
                        settings[key] = not settings[key]
                        save_mission_settings(player, settings)
                        break
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_slider = False
            if event.type == pygame.MOUSEMOTION and dragging_slider and controls.get("spawn_rate_track"):
                set_spawn_rate_from_mouse(settings, controls["spawn_rate_track"], event.pos[0])
                save_mission_settings(player, settings)

        screen.blit(background, (0, 0))
        draw_mission_settings_modal(screen, settings, unlocks, controls, title_font, body_font, small_font)
        pygame.display.flip()
        clock.tick(60)


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
    max_instruction_scroll, scrollbar_track_rect, scrollbar_thumb_rect = draw_scrollable_text(
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
    return button_rect, max_instruction_scroll, scrollbar_track_rect, scrollbar_thumb_rect


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
            if event.type == pygame.MOUSEMOTION:
                # Only the cursor *moving* changes the selection; a stationary
                # cursor must not override keyboard navigation each frame.
                for index, rect in enumerate(buttons):
                    if rect.collidepoint(event.pos):
                        selected = index
                        break
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
        self.shot_trail_color = player_splash_rgb(self.shot_charge_color)
        self.mission_settings = player_mission_settings(player)
        self.raw_mega_shot_available = player_mega_shot_available(player, self.lesson_number)
        self.raw_shields_available = player_shield_available(player, self.lesson_number)
        if cheats.is_enabled("4"):
            self.raw_mega_shot_available = True
        if cheats.is_enabled("5"):
            self.raw_shields_available = True
        self.player_mega_shot_available = False
        self.player_advanced_mega_shot_available = player_advanced_mega_shot_available(player, self.lesson_number)
        self.player_shields_available = False
        self.max_shield_charges = player_shield_max_charges(player)
        self.target_keys = tuple(valid_keys)
        self.focus_keys = lesson_focus_keys(self.lesson_number, self.target_keys)
        self.drone_target = lesson_drone_target(self.lesson_number)
        self.mini_boss_numbers = mini_boss_numbers_for_lesson(self.lesson_number, self.drone_target)
        self.final_boss_count = final_boss_count(self.lesson_number)
        self.final_bosses_defeated = 0
        self.instructions_audio_path = self.lesson_dir / f"lesson_{self.lesson_number}_instructions.wav"
        self.instructions_audio_duration_ms = audio_duration_ms(self.instructions_audio_path)
        self.instructions_text = read_text(self.lesson_dir / f"lesson_{self.lesson_number}_instructions.txt")
        self.hint_images = load_mission_hint_images(self.lesson_dir, self.lesson_number)
        self.hint_texts = load_json_object(self.lesson_dir / f"mission_hints_l{self.lesson_number}.json")
        self.laser_sound = load_sound(self.sfx_dir / "laser.ogg", 0.55)
        self.explosion_sound = load_sound(self.sfx_dir / "explosion.ogg", 0.75)
        if cheats.is_enabled("13"):
            self.explosion_sound = None  # cheat: silence enemy explosion sounds
        self.health_sound = load_sound(self.sfx_dir / "health.ogg", 0.85)
        self.shield_up_sound = load_sound(self.sfx_dir / "shield_up.wav", 0.85)
        self.time_stop_sound = load_sound(self.sfx_dir / "time_stop.wav", 0.85)
        self.time_stop_ending_sound = load_sound(self.sfx_dir / "time_stop_ending.wav", 0.85)
        self.split_sound = load_sound(self.sfx_dir / "split.ogg", 0.75)
        self.boss_sound = load_sound(self.sfx_dir / "boss.ogg", 0.85)
        self.victory_sound = load_sound(self.sfx_dir / "victory.wav", 0.9)
        self.warning_sound = load_sound(self.sfx_dir / "warning.wav", 0.8)
        self.limited_sound = load_first_sound(
            (self.sfx_dir / "limited.wav", self.sfx_dir / "limited.wave", self.sfx_dir / "beep.wav"),
            0.8,
        )
        self.bg_music = load_sound(bg_music_path(self.sfx_dir, self.lesson_number), BG_MUSIC_VOLUME)
        self.bg_music_channel = None
        self.boss_music = load_sound(self.sfx_dir / "boss_music.wav", BOSS_MUSIC_VOLUME)
        self.boss_music_channel = None
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
        self.defense_drones = []
        self.defense_shots = []
        self.pending_shots = []
        self.shot_trails = []
        self.power_up = None
        self.life_power_ups_spawned = 0
        self.final_bosses = []
        self.particles = []
        self.stars = create_star_field()
        self.destroyed = 0
        self.spawned_count = 0
        self.score = 0
        self.hits_taken = 0
        self.accurate_inputs = 0
        self.inaccurate_inputs = 0
        self.inaccurate_keys = []
        self.bonus_points = 0
        self.mission_start_ticks = None
        self.level_time_ms = 0
        self.high_score_goal = high_score_goal(
            self.drone_target,
            MAX_LIFE_POWER_UPS_PER_MISSION,
            FINAL_BOSS_SCORE if self.final_boss_count > 0 else 0,
            len(self.mini_boss_numbers),
        )
        self.quick_defender_goal_ms = quick_defender_goal_ms(self.lesson_number)
        self.player_time_stop_available = player_time_stop_available(player, self.lesson_number)
        if cheats.is_enabled("6"):
            self.player_time_stop_available = True
        self.time_stop_power_up_enabled = time_stop_power_up_enabled(self.lesson_number)
        self.time_stop_max_charges = TIME_STOP_MAX_CHARGES
        self.time_stop_charges = self._player_int("time_stop_charges", 0, 0, self.time_stop_max_charges)
        if cheats.is_enabled("6"):
            self.time_stop_charges = min(self.time_stop_max_charges, cheats.CHEAT_TIME_STOP_CHARGES)
        self.time_stop = None
        self.current_time_scale = 1.0
        self._ring_radius = 0.0
        self._ring_overlay = None
        self._time_stop_ending_played = False
        self.space_tap_times = []
        # Cheat 14 auto-fire: on by default while the cheat is active; toggled
        # by tapping Left Ctrl AUTO_FIRE_TOGGLE_TAPS times quickly.
        self.auto_fire_enabled = True
        self.ctrl_tap_times = []
        self.credits_awarded = False
        self.lives = max(
            STARTING_LIVES,
            self._player_int("lives", STARTING_LIVES, 1, player_limits.MAX_PLAYER_LIVES),
        )
        if cheats.is_enabled("1"):
            self.lives = min(player_limits.MAX_PLAYER_LIVES, cheats.CHEAT_LIVES)
        self.shield_charges = self._player_int("shield_charges", 0, 0, self.max_shield_charges)
        if self.player_shields_available and self.max_shield_charges > 0 and self.shield_charges <= 0:
            self.shield_charges = 1
        self.starting_shield_charges = self.shield_charges
        self.active_shield_hits = 0
        self.active_shield_expires_at = 0
        self._save_player_resources()
        self.turret_angle = -math.pi / 2
        self.pod_rotation = 0
        self.player_center = screen_center(self.screen)
        self.space_held = False
        self.mega_charge_blocks = MEGA_CHARGE_MAX_BLOCKS
        self.next_mega_recharge_time = 0
        self.current_spawn_interval_ms = self._spawn_interval()
        self.next_spawn_rate_change_time = pygame.time.get_ticks() + SPAWN_RATE_CHANGE_MS
        self.next_spawn_time = pygame.time.get_ticks()
        self.next_power_up_spawn_time = next_power_up_time(self.next_spawn_time)
        self._apply_mission_settings(rebuild_defense_drones=True)

    @property
    def final_boss(self):
        return self.final_bosses[0] if self.final_bosses else None

    def _settings_unlocks(self):
        return {
            "disable_defense_drones": player_defense_drone_count(self.player) > 0,
            "disable_mega_shot": self.raw_mega_shot_available,
            "disable_shields": self.raw_shields_available,
            "music_enabled": True,
        }

    def _spawn_interval(self):
        multiplier = max(1.0, float(self.mission_settings.get("spawn_rate_multiplier", 1.0)))
        if cheats.is_enabled("15"):
            multiplier = max(multiplier, 10.0)  # cheat: 10x spawn rate
        return max(80, int(random_spawn_interval(self.lesson_number) / multiplier))

    def _create_defense_drones(self):
        if self.mission_settings.get("disable_defense_drones") and self._settings_unlocks()["disable_defense_drones"]:
            return []
        defense_drone_count = player_defense_drone_count(self.player)
        if defense_drone_count <= 0:
            return []
        fire_stagger_ms = DEFENSE_DRONE_FIRE_INTERVAL_MS / defense_drone_count
        start_time = pygame.time.get_ticks()
        return [
            DefenseDrone(
                angle=index * math.tau / defense_drone_count,
                next_fire_time=int(start_time + fire_stagger_ms * (index + 1)),
            )
            for index in range(defense_drone_count)
        ]

    def _apply_mission_settings(self, rebuild_defense_drones=False):
        self.mission_settings = player_mission_settings(self.player)
        unlocks = self._settings_unlocks()
        mega_disabled = self.mission_settings.get("disable_mega_shot") and unlocks["disable_mega_shot"]
        shields_disabled = self.mission_settings.get("disable_shields") and unlocks["disable_shields"]
        defense_disabled = self.mission_settings.get("disable_defense_drones") and unlocks["disable_defense_drones"]

        self.player_mega_shot_available = self.raw_mega_shot_available and not mega_disabled
        self.player_shields_available = self.raw_shields_available and not shields_disabled
        self.max_shield_charges = player_shield_max_charges(self.player) if self.player_shields_available else 0
        if self.player_shields_available and self.max_shield_charges > 0 and self.shield_charges <= 0:
            self.shield_charges = 1
        self.target_keys = mission_target_keys(self.valid_keys, self.lesson_number, self.player_mega_shot_available)
        if mega_disabled and "space" not in self.target_keys:
            self.target_keys = tuple(self.target_keys) + ("space",)
        self.focus_keys = lesson_focus_keys(self.lesson_number, self.target_keys)

        if mega_disabled:
            self.space_held = False
            self.mega_shots.clear()
            self.mega_charge_blocks = 0
            self.next_mega_recharge_time = 0
        elif self.mega_charge_blocks <= 0:
            self.mega_charge_blocks = MEGA_CHARGE_MAX_BLOCKS

        if shields_disabled:
            self._clear_active_shield()
            if self.power_up is not None and self.power_up.kind == "shield":
                self.power_up = None
                self.next_power_up_spawn_time = next_power_up_time(pygame.time.get_ticks())
        elif self.shield_charges > self.max_shield_charges:
            self.shield_charges = self.max_shield_charges

        if defense_disabled:
            self.defense_drones.clear()
            for shot in self.defense_shots:
                if shot.target is not None:
                    shot.target.incoming_defense_damage = max(0, shot.target.incoming_defense_damage - 1)
            self.defense_shots.clear()
        elif rebuild_defense_drones or not self.defense_drones:
            self.defense_drones = self._create_defense_drones()

        if not self.mission_settings.get("music_enabled", True):
            self._stop_all_music(BG_MUSIC_FADE_OUT_MS)
        elif self.bg_music_channel is None and self.boss_music_channel is None:
            if self.final_bosses:
                self._start_boss_music()
            else:
                self.bg_music_channel = play_looping_sound(self.bg_music, BG_MUSIC_FADE_IN_MS)

    def _run_mission_briefing(self):
        play_audio(self.instructions_audio_path)
        previous_mouse_visible = pygame.mouse.get_visible()
        pygame.mouse.set_visible(True)
        briefing_started_at = pygame.time.get_ticks()
        start_button = pygame.Rect(0, 0, 0, 0)
        instruction_scroll = 0
        max_instruction_scroll = 0
        scrollbar_track_rect = None
        scrollbar_thumb_rect = None
        dragging_scrollbar = False
        scrollbar_drag_offset = 0
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
                        if scrollbar_thumb_rect is not None and scrollbar_thumb_rect.collidepoint(event.pos):
                            dragging_scrollbar = True
                            scrollbar_drag_offset = event.pos[1] - scrollbar_thumb_rect.y
                            continue
                        if start_button.collidepoint(event.pos):
                            stop_audio()
                            self._shift_gameplay_timers(pygame.time.get_ticks() - briefing_started_at)
                            return "start"
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        dragging_scrollbar = False
                    if (
                        event.type == pygame.MOUSEMOTION
                        and dragging_scrollbar
                        and scrollbar_track_rect is not None
                        and scrollbar_thumb_rect is not None
                        and max_instruction_scroll > 0
                    ):
                        travel = max(1, scrollbar_track_rect.height - scrollbar_thumb_rect.height)
                        thumb_y = max(
                            scrollbar_track_rect.y,
                            min(event.pos[1] - scrollbar_drag_offset, scrollbar_track_rect.y + travel),
                        )
                        instruction_scroll = max_instruction_scroll * (thumb_y - scrollbar_track_rect.y) / travel

                if not dragging_scrollbar:
                    instruction_scroll = min(max_instruction_scroll, instruction_scroll + scroll_speed * dt)
                self._draw_frame(now, present=False)
                (
                    start_button,
                    max_instruction_scroll,
                    scrollbar_track_rect,
                    scrollbar_thumb_rect,
                ) = draw_mission_briefing_modal(
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
        self.player["lives"] = max(1, min(player_limits.MAX_PLAYER_LIVES, self.lives))
        if self.player_shields_available:
            self.player["shield_charges"] = max(0, min(self.max_shield_charges, self.shield_charges))
        self.player["time_stop_charges"] = max(0, min(self.time_stop_max_charges, self.time_stop_charges))

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
        self._stop_all_music()
        self._save_player_resources()
        return result

    def _stop_all_music(self, fade_ms=0):
        stop_looping_sound(self.bg_music_channel, fade_ms)
        stop_looping_sound(self.boss_music_channel, fade_ms)
        self.bg_music_channel = None
        self.boss_music_channel = None

    def _start_boss_music(self):
        if not self.mission_settings.get("music_enabled", True):
            return
        stop_looping_sound(self.bg_music_channel, BG_MUSIC_FADE_OUT_MS)
        self.bg_music_channel = None
        if self.boss_music_channel is None or not self.boss_music_channel.get_busy():
            self.boss_music_channel = play_looping_sound(self.boss_music, BOSS_MUSIC_FADE_IN_MS)

    def _accuracy_percent(self):
        total_inputs = self.accurate_inputs + self.inaccurate_inputs
        if total_inputs <= 0:
            return 100
        return self.accurate_inputs * 100 / total_inputs

    def _record_accurate_input(self, now=None):
        self.accurate_inputs += 1

    def _record_inaccurate_input(self):
        self.inaccurate_inputs += 1

    def _record_inaccurate_key(self, key, now=None):
        self._record_inaccurate_input()
        if not cheats.is_enabled("12"):
            play_sound(self.limited_sound)
        if len(self.inaccurate_keys) < 4:
            self.inaccurate_keys.append(key)

    def _defense_drone_accuracy_grace_active(self, pressed_key, now):
        if pressed_key is None:
            return False
        return any(
            defense_drone.last_shot_key == pressed_key and now <= defense_drone.last_shot_grace_until
            for defense_drone in self.defense_drones
        )

    def _retarget_split_shots(self, parent, children):
        if not children:
            return
        for pending_shot in self.pending_shots:
            if pending_shot.target is parent:
                child = reserve_split_child_target(children, pending_shot.damage)
                pending_shot.target = child
        for bullet in self.bullets:
            if bullet.target is parent:
                child = reserve_split_child_target(children, 1)
                bullet.target = child
        for mega_shot in self.mega_shots:
            if mega_shot.target is parent:
                child = reserve_split_child_target(children, mega_damage(mega_shot.charge_level))
                mega_shot.target = child
        for defense_shot in self.defense_shots:
            if defense_shot.target is parent:
                child = reserve_split_child_defense_target(children, 1)
                defense_shot.target = child

    def _show_end_screen(self, won):
        self._save_player_resources()
        credits_earned = self._calculate_credits_earned(won)
        self._award_credits(credits_earned)
        if won:
            self._add_lifetime_score()
        if self.player is not None:
            total_accuracy_inputs = self.accurate_inputs + self.inaccurate_inputs
            accuracy_percent = (
                100
                if total_accuracy_inputs <= 0
                else round(self.accurate_inputs * 100 / total_accuracy_inputs)
            )
            self.player["last_mission_stats"] = {
                "lesson_number": self.lesson_number,
                "won": bool(won),
                "hits_taken": max(0, self.hits_taken),
                "accurate_inputs": max(0, self.accurate_inputs),
                "inaccurate_inputs": max(0, self.inaccurate_inputs),
                "accuracy_percent": accuracy_percent,
                "starting_shield_charges": max(0, self.starting_shield_charges),
                "ending_shield_charges": max(0, self.shield_charges),
                "score": max(0, self.score),
                "bonus_points": max(0, self.bonus_points),
                "level_time_ms": max(0, self.level_time_ms),
                "high_score_goal": max(0, self.high_score_goal),
                "quick_time_goal_ms": max(0, self.quick_defender_goal_ms),
            }
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
            self.bonus_points,
            self.level_time_ms,
        )

    def _boss_player_target_center(self):
        width, height = self.screen.get_size()
        return pygame.Vector2(width * FINAL_BOSS_PLAYER_X_RATIO, height / 2)

    def _update_player_center(self, dt):
        target = self._boss_player_target_center() if self.final_bosses else screen_center(self.screen)
        travel = target - self.player_center
        distance = travel.length()
        max_step = FINAL_BOSS_PLAYER_PAN_SPEED * dt
        if distance <= max_step or distance == 0:
            self.player_center = target
        else:
            self.player_center += travel.normalize() * max_step

    def _boss_perspective_ready(self):
        if not self.final_bosses:
            return False
        return self.player_center.distance_to(self._boss_player_target_center()) <= 2

    def _firing_locked_for_boss_intro(self):
        # While final bosses are still approaching/repositioning the player cannot
        # engage them yet, so key presses must not be counted as inaccurate.
        return bool(self.final_bosses) and not self._boss_perspective_ready()

    def _shift_gameplay_timers(self, elapsed_ms):
        if elapsed_ms <= 0:
            return
        self.next_mega_recharge_time = self._shift_timer(self.next_mega_recharge_time, elapsed_ms)
        self.next_spawn_rate_change_time = self._shift_timer(self.next_spawn_rate_change_time, elapsed_ms)
        self.next_spawn_time = self._shift_timer(self.next_spawn_time, elapsed_ms)
        self.next_power_up_spawn_time = self._shift_timer(self.next_power_up_spawn_time, elapsed_ms)
        if self.mission_start_ticks is not None:
            self.mission_start_ticks = self._shift_timer(self.mission_start_ticks, elapsed_ms)
        self.active_shield_expires_at = self._shift_timer(self.active_shield_expires_at, elapsed_ms)
        if self.power_up is not None:
            self.power_up.expires_at += elapsed_ms
        for final_boss in self.final_bosses:
            final_boss.next_shot_time = self._shift_timer(final_boss.next_shot_time, elapsed_ms)
            final_boss.next_orbit_switch_time = self._shift_timer(final_boss.next_orbit_switch_time, elapsed_ms)
            final_boss.next_semi_boss_spawn_time = self._shift_timer(final_boss.next_semi_boss_spawn_time, elapsed_ms)
            if final_boss.shield_down_since is not None:
                final_boss.shield_down_since += elapsed_ms
            if final_boss.next_shield_recharge_time is not None:
                final_boss.next_shield_recharge_time += elapsed_ms
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

    def _ring_max_radius(self, center):
        # Distance from the ring center to the farthest screen corner (+margin),
        # so the ring fully clears the screen at peak.
        width, height = self.screen.get_size()
        corners = ((0, 0), (width, 0), (0, height), (width, height))
        farthest = max(math.hypot(center.x - cx, center.y - cy) for cx, cy in corners)
        return farthest + 40

    def _update_time_stop(self, dt):
        if self.time_stop is not None:
            self.time_stop.update(dt * 1000)
            if self.time_stop.is_contracting() and not self._time_stop_ending_played:
                play_sound(self.time_stop_ending_sound)
                self._time_stop_ending_played = True
            if not self.time_stop.active:
                self.time_stop = None
        # Cache the ring radius once per frame; while active, the ship/pod and the
        # level timer (both at/near the center) are frozen the whole time.
        if self.time_stop is not None:
            self._ring_radius = self.time_stop.radius()
            self.current_time_scale = self.time_stop.min_speed_scale
        else:
            self._ring_radius = 0.0
            self.current_time_scale = 1.0

    def _object_time_scale(self, pos):
        ring = self.time_stop
        if ring is None:
            return 1.0
        distance = math.hypot(pos.x - ring.center.x, pos.y - ring.center.y)
        return ring.object_time_scale(distance, self._ring_radius)

    def _activate_time_stop(self, now):
        if not self.player_time_stop_available or self.time_stop is not None:
            return False
        if self.time_stop_charges <= 0:
            return False
        if self._firing_locked_for_boss_intro():
            return False  # can't activate during the final boss pan/approach
        self.time_stop_charges -= 1
        self._save_player_resources()
        center = pygame.Vector2(self.player_center)
        self.time_stop = TimeStopRing(
            TIME_STOP_DURATION_MS,
            TIME_STOP_EXPAND_MS,
            TIME_STOP_CONTRACT_MS,
            TIME_STOP_MIN_SPEED_SCALE,
            center,
            self._ring_max_radius(center),
        )
        self._ring_radius = 0.0
        self._time_stop_ending_played = False
        self.space_tap_times = []
        play_sound(self.time_stop_sound)
        return True

    def _register_space_tap(self, now):
        self.space_tap_times = [t for t in self.space_tap_times if now - t <= TIME_STOP_DOUBLE_TAP_MS]
        self.space_tap_times.append(now)
        if len(self.space_tap_times) >= 2:
            return self._activate_time_stop(now)
        return False

    def _register_ctrl_tap(self, now):
        # Returns True once Left Ctrl has been tapped enough times in the window.
        self.ctrl_tap_times = [t for t in self.ctrl_tap_times if now - t <= AUTO_FIRE_TOGGLE_WINDOW_MS]
        self.ctrl_tap_times.append(now)
        if len(self.ctrl_tap_times) >= AUTO_FIRE_TOGGLE_TAPS:
            self.ctrl_tap_times = []
            return True
        return False

    def _auto_fire_turret(self, now):
        # Cheat 14: queue a shot at the nearest in-range drone. One at a time so
        # the turret works the queue exactly as it does for typed shots.
        if self.pending_shots:
            return
        max_range = AUTO_FIRE_RANGE_RATIO * self.screen.get_size()[1] / 2
        target = nearest_targetable_drone_in_range(self.drones, self.player_center, max_range)
        if target is not None:
            target.incoming_damage += 1
            self.pending_shots.append(PendingShot(target=target, damage=1, created_at=now))

    def _begin_frame(self):
        dt = self.clock.tick(60) / 1000
        now = pygame.time.get_ticks()
        self._update_time_stop(dt)
        self._update_player_center(dt)
        # During a time stop the pod keeps rotating, but at 1/3 speed.
        pod_scale = TIME_STOP_POD_ROTATION_SCALE if self.time_stop is not None else 1.0
        self.pod_rotation = (
            self.pod_rotation + math.tau * dt * pod_scale / POD_ROTATION_SECONDS
        ) % math.tau
        if now >= self.next_spawn_rate_change_time:
            self.current_spawn_interval_ms = self._spawn_interval()
            self.next_spawn_rate_change_time = now + SPAWN_RATE_CHANGE_MS
        # The background star field stops drifting during a time stop.
        if self.time_stop is None:
            update_star_field(self.stars, dt)
        # The level timer is fully frozen while a time stop is active.
        if self.mission_start_ticks is not None and self.time_stop is None:
            self.level_time_ms = min(
                MAX_LEVEL_TIME_MS, self.level_time_ms + dt * 1000
            )
        if self.player_mega_shot_available and self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS:
            if self.next_mega_recharge_time and now >= self.next_mega_recharge_time:
                self.mega_charge_blocks += 1
                self.next_mega_recharge_time = (
                    now + MEGA_RECHARGE_INTERVAL_MS
                    if self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS
                    else 0
                )
        # Cheats: keep charges topped up so they never effectively drain.
        if cheats.is_enabled("4"):
            self.mega_charge_blocks = MEGA_CHARGE_MAX_BLOCKS
        if cheats.is_enabled("5") and self.player_shields_available:
            self.shield_charges = min(self.max_shield_charges, cheats.CHEAT_SHIELD_CHARGES)
        if cheats.is_enabled("6"):
            self.time_stop_charges = min(self.time_stop_max_charges, cheats.CHEAT_TIME_STOP_CHARGES)
        return dt, now

    def _start_final_boss_encounter(self, now):
        for drone in self.drones:
            explode(self.particles, drone.pos, 12)
        self.drones.clear()
        while self.pending_shots:
            release_pending_shot(self.pending_shots.pop(0))
        self.bullets.clear()
        self.mega_shots.clear()
        boss_count = max(1, self.final_boss_count)
        self.final_bosses = [
            spawn_final_boss(
                self.screen,
                now,
                self.target_keys,
                self._boss_player_target_center(),
                self.focus_keys,
                index,
                boss_count,
            )
            for index in range(boss_count)
        ]
        self._start_boss_music()
        play_sound(self.boss_sound)

    def _complete_final_boss(self, target, now):
        explode(self.particles, target.pos, 42)
        play_sound(self.explosion_sound)
        if target in self.final_bosses:
            self.final_bosses.remove(target)
        self.score += FINAL_BOSS_SCORE
        self.final_bosses_defeated += 1
        if not self.final_bosses:
            self._stop_all_music(BOSS_MUSIC_FADE_OUT_MS)
            stop_audio()
            play_sound(self.victory_sound)
            return self._show_end_screen(True)
        return None

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
        if self.time_stop is not None:
            # No new spawns (drones, mini-bosses, or power-ups) while time is
            # stopped. Hold the spawn timers ahead of `now` so nothing bursts out
            # the instant the stop ends.
            self.next_spawn_time = now + self.current_spawn_interval_ms
            if self.next_power_up_spawn_time <= now:
                self.next_power_up_spawn_time = now + 1
            return
        has_no_standard_play_drones = (
            not self.final_bosses
            and not self.drones
            and self.destroyed < self.drone_target
        )
        if (
            not self.final_bosses
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
                self.player_shields_available,
                self.shield_charges,
                self.max_shield_charges,
                self.life_power_ups_spawned < MAX_LIFE_POWER_UPS_PER_MISSION,
                self.player_center,
                blocked_rects=self._power_up_blocked_rects(),
                time_stop_enabled=self.time_stop_power_up_enabled and self.player_time_stop_available,
                time_stop_charges=self.time_stop_charges,
                max_time_stop_charges=self.time_stop_max_charges,
            )
            if self.power_up is None:
                self.next_power_up_spawn_time = next_power_up_time(now)
            elif self.power_up.kind == "life":
                self.life_power_ups_spawned += 1

        if (
            final_boss_enabled(self.lesson_number)
            and not self.final_bosses
            and self.final_bosses_defeated == 0
            and self.destroyed >= self.drone_target
            and active_mini_boss_count(self.drones) == 0
            and self.time_stop is None  # wait for an active time stop to finish first
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

        draw_shot_trails(self.screen, self.shot_trails, self.shot_trail_color)

        for bullet in self.bullets:
            draw_bullet(self.screen, bullet, self.shot_image)

        for mega_shot in self.mega_shots:
            draw_mega_shot(self.screen, mega_shot, self.shot_image)

        for defense_shot in self.defense_shots:
            draw_defense_shot(self.screen, defense_shot, self.shot_trail_color)

        draw_power_up(self.screen, self.power_up, now)
        for final_boss in self.final_bosses:
            draw_final_boss(self.screen, final_boss, self.final_boss_image)

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
        # The time-stop ring sits on top of the world layer but UNDER the HUD.
        self._draw_time_stop_ring()
        mega_text = ""
        mega_active = False
        if self.player_mega_shot_available:
            mega_text = "Adv. Mega Shot" if self.player_advanced_mega_shot_available else "Mega Shot"
            mega_active = self.mega_charge_blocks > 0
        width, _ = self.screen.get_size()
        # Charge bars share one row, left-to-right: Mega, Shield, Time Stop.
        bars = []
        if self.player_mega_shot_available:
            bars.append("mega")
        if self.player_shields_available:
            bars.append("shield")
        if self.player_time_stop_available:
            bars.append("time_stop")
        spacing = 200
        start_x = width / 2 - (len(bars) - 1) * spacing / 2
        for index, bar in enumerate(bars):
            center_x = start_x + index * spacing
            if bar == "mega":
                draw_mega_bar(self.screen, self.font, mega_text, self.mega_charge_blocks, mega_active, center_x)
            elif bar == "shield":
                draw_player_shield_bar(
                    self.screen, self.font, self.shield_charges, True, 0, self.max_shield_charges, center_x
                )
            else:
                draw_time_stop_bar(
                    self.screen, self.font, self.time_stop_charges, True, 0, self.time_stop_max_charges, center_x
                )
        draw_hud(
            self.screen,
            self.font,
            min(self.destroyed, self.drone_target),
            self.drone_target,
            self.score,
            self.lives,
            self.level_time_ms,
        )
        footer_font = pygame.font.SysFont("arial", 18)
        footer_text = "Esc: Pause  |  F11: Max size"
        footer_surface = footer_font.render(footer_text, True, MUTED_TEXT)
        self.screen.blit(footer_surface, footer_surface.get_rect(center=(width / 2, height - 28)))

        if present:
            pygame.display.flip()

    def _draw_time_stop_ring(self):
        # Translucent light-yellow ring (shield-style) sweeping out from the
        # ship and contracting back in, marking the time-stop boundary.
        ring = self.time_stop
        if ring is None:
            return
        radius = int(self._ring_radius)
        if radius <= 1:
            return
        size = self.screen.get_size()
        if self._ring_overlay is None or self._ring_overlay.get_size() != size:
            self._ring_overlay = pygame.Surface(size, pygame.SRCALPHA)
        overlay = self._ring_overlay
        overlay.fill((0, 0, 0, 0))
        center = (int(ring.center.x), int(ring.center.y))
        alpha = max(0, min(255, TIME_RING_ALPHA))
        # Three concentric rings: grey outer, lighter inner ring, grey inner-outer.
        # Both grey rings share TIME_RING_COLOR.
        pygame.draw.circle(overlay, (*TIME_RING_COLOR, alpha), center, radius, 10)
        if radius > 22:
            pygame.draw.circle(overlay, (*TIME_RING_INNER_COLOR, max(0, alpha - 35)), center, radius - 16, 4)
        if radius > 40:
            pygame.draw.circle(overlay, (*TIME_RING_COLOR, alpha), center, radius - 28, 10)
        self.screen.blit(overlay, (0, 0))

    def _process_pending_shots(self, now, dt):
        while self.pending_shots and not target_is_available(self.pending_shots[0].target, self.drones, self.final_bosses):
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
        if not self.final_bosses:
            return
        for final_boss in self.final_bosses:
            object_scale = self._object_time_scale(final_boss.pos)
            object_dt = dt * object_scale
            update_final_boss_movement(final_boss, self.screen, object_dt, now)
            final_boss.rotation = (final_boss.rotation + math.tau * object_dt / FINAL_BOSS_ROTATION_SECONDS) % math.tau
            update_final_boss_shield(final_boss, now)
            if object_scale < 1.0:
                # Frozen: no firing or semi-boss spawning; pause the timers.
                if final_boss.next_shot_time:
                    final_boss.next_shot_time += dt * 1000
                if final_boss.next_semi_boss_spawn_time:
                    final_boss.next_semi_boss_spawn_time += dt * 1000
                continue
            if final_boss.is_orbiting and self._boss_perspective_ready() and final_boss.next_shot_time == 0:
                final_boss.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS
            if (
                final_boss.is_orbiting
                and self._boss_perspective_ready()
                and final_boss.next_shot_time
                and now >= final_boss.next_shot_time
            ):
                fire_final_boss_drones(
                    self.drones,
                    final_boss,
                    self.player_center,
                    self.target_keys,
                    final_boss_projectile_count(self.lesson_number),
                    self.focus_keys,
                )
                final_boss.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS
            if final_boss.next_semi_boss_spawn_time and now >= final_boss.next_semi_boss_spawn_time:
                spawn_final_boss_semi_boss(
                    self.drones,
                    final_boss,
                    self.player_center,
                    self.target_keys,
                    self.focus_keys,
                )
                play_sound(self.boss_sound)
                final_boss.next_semi_boss_spawn_time = now + FINAL_BOSS_SEMI_BOSS_SPAWN_INTERVAL_MS

    def _update_drones(self, now, dt):
        for drone in self.drones[:]:
            center = self.player_center
            object_scale = self._object_time_scale(drone.pos)
            object_dt = dt * object_scale
            update_drone_position(drone, center, object_dt)
            drone.rotation = (drone.rotation + drone_rotation_radians_per_second(drone) * object_dt) % math.tau
            if object_scale < 1.0:
                # Frozen by the time-stop ring: no shooting; pause the cooldown so
                # it doesn't fire the instant it un-freezes (purple drones can't
                # spawn more drones while frozen).
                drone.next_shot_time += dt * 1000
            elif drone.is_mega and now >= drone.next_shot_time:
                blocked_key = random.choice(self.final_bosses).letter if self.final_bosses else None
                focus_keys = self.focus_keys if self.final_bosses else ()
                fire_mega_drone(self.drones, drone, center, self.target_keys, blocked_key, focus_keys)
                drone.next_shot_time = now + MEGA_ATTACK_INTERVAL_MS
            if object_scale >= 1.0 and drone.pos.distance_to(center) <= drone.radius + PLAYER_COLLISION_RADIUS:
                self.drones.remove(drone)
                explode(self.particles, drone.pos, 12)
                play_sound(self.explosion_sound)
                if cheats.is_enabled("3"):
                    # Hit is fully ignored: not counted, no shield used, no life lost.
                    continue
                self.hits_taken += 1
                if self._absorb_player_hit_with_shield(now):
                    continue
                if cheats.is_enabled("2"):
                    continue  # invincible: hit counted but no life lost
                self.lives -= 1
                self._save_player_resources()
                if self.lives <= 0:
                    self._stop_all_music(BG_MUSIC_FADE_OUT_MS)
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

    def _remove_crashed_drone(self, drone):
        # Drone destroyed by crashing (into a defense drone or the pod): no
        # points and no level credit (see issue #15).
        pos = drone.pos.copy()
        if drone in self.drones:
            self.drones.remove(drone)
        explode(self.particles, pos)
        play_sound(self.explosion_sound)

    def _damage_drone_from_defense_shot(self, drone):
        if drone not in self.drones:
            return
        drone.incoming_defense_damage = max(0, drone.incoming_defense_damage - 1)
        drone.hp -= 1
        if not drone.is_mega:
            self.score += DRONE_HIT_SCORE
        if drone.hp > 0 and not drone.is_mega:
            self.drones.remove(drone)
            children = split_regular_drone(self.drones, drone)
            self._retarget_split_shots(drone, children)
            play_sound(self.split_sound)
        elif drone.hp <= 0:
            pos = drone.pos.copy()
            if drone.is_mega:
                self.score += MINI_BOSS_SCORE
            if drone_counts_for_level(drone):
                self.destroyed += drone.level_value
            if drone in self.drones:
                self.drones.remove(drone)
            explode(self.particles, pos)
            play_sound(self.explosion_sound)

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
        width, height = self.screen.get_size()
        engage_radius = min(width, height) * DEFENSE_DRONE_ENGAGE_RANGE_RATIO
        candidates = [
            drone
            for drone in self.drones
            if drone.pos.distance_to(self.player_center) <= engage_radius
            and self._defense_drone_has_line_of_sight(defense_pos, drone.pos)
            and defense_drone_remaining_shot_capacity(drone) > 0
        ]
        return random.choice(candidates) if candidates else None

    def _update_defense_drones(self, now, dt):
        for defense_drone in self.defense_drones:
            if not defense_drone.active:
                continue
            defense_pos = defense_drone_position(self.player_center, defense_drone)
            # During a time stop defense drones keep orbiting (at 1/10 speed) but
            # do not fire; otherwise they run at normal speed.
            time_stopped = self.time_stop is not None
            orbit_scale = TIME_STOP_POD_ROTATION_SCALE if time_stopped else 1.0
            defense_drone.angle = (defense_drone.angle + math.tau * dt * orbit_scale / DEFENSE_DRONE_ORBIT_SECONDS) % math.tau
            defense_pos = defense_drone_position(self.player_center, defense_drone)

            for drone in self.drones[:]:
                if drone.pos.distance_to(defense_pos) <= drone.radius + DEFENSE_DRONE_COLLISION_RADIUS:
                    defense_drone.active = False
                    self._remove_crashed_drone(drone)
                    explode(self.particles, defense_pos, 10)
                    break

            if not defense_drone.active:
                continue
            if time_stopped:
                defense_drone.next_fire_time += dt * 1000  # hold fire during a time stop, pause cooldown
            elif now >= defense_drone.next_fire_time:
                target = self._defense_drone_target(defense_pos)
                if target is not None:
                    defense_drone.last_shot_key = target.letter
                    defense_drone.last_shot_grace_until = now + DEFENSE_DRONE_ACCURACY_GRACE_MS
                    direction = target.pos - defense_pos
                    if direction.length_squared() == 0:
                        direction = pygame.Vector2(0, -1)
                    else:
                        direction = direction.normalize()
                    target.incoming_defense_damage += 1
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
            object_dt = dt * self._object_time_scale(shot.pos)
            if shot.target not in self.drones:
                if shot.target is not None:
                    shot.target.incoming_defense_damage = max(0, shot.target.incoming_defense_damage - 1)
                shot.target = None
                add_shot_trail(self.shot_trails, shot, pygame.time.get_ticks())
                shot.pos += shot.vel * object_dt
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
            shot.pos += shot.vel * object_dt
            if bullet_is_offscreen(shot, self.screen):
                shot.target.incoming_defense_damage = max(0, shot.target.incoming_defense_damage - 1)
                self.defense_shots.remove(shot)

    def run(self):
        briefing_result = self._run_mission_briefing()
        if briefing_result == "quit":
            return self._finish("quit")
        pygame.mouse.set_visible(False)
        pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        self.mission_start_ticks = pygame.time.get_ticks()

        while True:
            dt, now = self._begin_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
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
                        if self.boss_music_channel is not None:
                            self.boss_music_channel.pause()
                        if pygame.mixer.get_init():
                            pygame.mixer.music.pause()
                        pause_started_at = pygame.time.get_ticks()
                        pause_result = pause_menu(self.screen, self.clock)
                        if pause_result == "resume":
                            self._shift_gameplay_timers(pygame.time.get_ticks() - pause_started_at)
                            pygame.mouse.set_visible(False)
                            if self.bg_music_channel is not None:
                                self.bg_music_channel.unpause()
                            if self.boss_music_channel is not None:
                                self.boss_music_channel.unpause()
                            if pygame.mixer.get_init():
                                pygame.mixer.music.unpause()
                            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN))
                            continue
                        self._stop_all_music(BG_MUSIC_FADE_OUT_MS)
                        stop_audio()
                        if pause_result == "quit":
                            return self._finish("quit")
                        if pause_result == "restart":
                            return self._finish("restart")
                        return self._finish("menu")
                    pressed_key = event_to_lesson_key(event, self.lesson_number)
                    if cheats.is_enabled("14") and event.key == pygame.K_LCTRL:
                        # Tap Left Ctrl 5x quickly to toggle auto-fire on/off.
                        if self._register_ctrl_tap(now):
                            self.auto_fire_enabled = not self.auto_fire_enabled
                        continue
                    if event.key == pygame.K_SPACE:
                        if self.player_mega_shot_available:
                            self.space_held = True
                            started_space_charge = True
                        if self.player_time_stop_available and self._register_space_tap(now):
                            continue
                    collected_power_up, consumed_by_power_up = handle_power_up_key(self.power_up, pressed_key)
                    if collected_power_up:
                        if collected_power_up == "shield":
                            self.shield_charges = min(self.max_shield_charges, self.shield_charges + 1)
                        elif collected_power_up == "time_stop":
                            self.time_stop_charges = min(
                                self.time_stop_max_charges, self.time_stop_charges + 1
                            )
                        else:
                            self.lives = min(player_limits.MAX_PLAYER_LIVES, self.lives + 1)
                        self.score += POWER_UP_SCORE
                        self._save_player_resources()
                        play_sound(self.health_sound)
                        self.power_up = None
                        self.next_power_up_spawn_time = next_power_up_time(now)
                    if consumed_by_power_up:
                        self._record_accurate_input(now)
                        continue
                    shot_queued = False
                    if pressed_key in self.target_keys:
                        if (
                            self.player_mega_shot_available
                            and self.space_held
                            and not started_space_charge
                            and self.mega_charge_blocks > 0
                        ):
                            final_boss_target = self.final_bosses if self._boss_perspective_ready() else []
                            queued_mega = queue_mega_shot(
                                self.drones,
                                final_boss_target,
                                self.pending_shots,
                                pressed_key,
                                self.player_center,
                                self.mega_charge_blocks,
                                now,
                                self.player_advanced_mega_shot_available,
                            )
                            if queued_mega:
                                self._record_accurate_input(now)
                                self.mega_charge_blocks = max(0, self.mega_charge_blocks - queued_mega)
                                self.next_mega_recharge_time = now + MEGA_RECHARGE_DELAY_MS
                                continue
                        shot_queued = queue_shot_at(self.drones, self.pending_shots, pressed_key, self.player_center, now)
                        if shot_queued:
                            self._record_accurate_input(now)
                    if (
                        pressed_key is not None
                        and not shot_queued
                        and not started_space_charge
                        and not self._defense_drone_accuracy_grace_active(pressed_key, now)
                        and not self._firing_locked_for_boss_intro()
                    ):
                        self._record_inaccurate_key(pressed_key, now)
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        self.space_held = False

            if cheats.is_enabled("14") and self.auto_fire_enabled:
                self._auto_fire_turret(now)
            self._process_pending_shots(now, dt)

            self._spawn_entities(now)

            if (
                not final_boss_enabled(self.lesson_number)
                and (self.lesson_number <= 2 or self.spawned_count >= self.drone_target)
                and self.destroyed >= self.drone_target
                and active_mini_boss_count(self.drones) == 0
            ):
                self._stop_all_music(BG_MUSIC_FADE_OUT_MS)
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
                    if not bullet.target.is_mega:
                        self.score += DRONE_HIT_SCORE
                    if bullet.target.hp > 0 and not bullet.target.is_mega and bullet.target in self.drones:
                        hit_drone = bullet.target
                        self.drones.remove(hit_drone)
                        children = split_regular_drone(self.drones, hit_drone)
                        self._retarget_split_shots(hit_drone, children)
                        play_sound(self.split_sound)
                        continue
                    if bullet.target.hp <= 0 and bullet.target in self.drones:
                        pos = bullet.target.pos.copy()
                        counts_for_level = drone_counts_for_level(bullet.target)
                        self.drones.remove(bullet.target)
                        if counts_for_level:
                            self.destroyed += bullet.target.level_value
                        if bullet.target.is_mega:
                            self.score += MINI_BOSS_SCORE
                        explode(self.particles, pos)
                        play_sound(self.explosion_sound)
                    continue

                if target_vector.length_squared() > 0:
                    bullet.vel = target_vector.normalize() * 650
                add_shot_trail(self.shot_trails, bullet, now)
                bullet.pos += bullet.vel * dt

            for mega_shot in self.mega_shots[:]:
                mega_shot.rotation = (mega_shot.rotation + math.tau * SHOT_ROTATIONS_PER_SECOND * dt) % math.tau
                if mega_shot.target is not None and not target_is_available(
                    mega_shot.target, self.drones, self.final_bosses
                ):
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
                            result = self._complete_final_boss(target, now)
                            if result is not None:
                                return result
                        else:
                            target.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS
                        continue

                    if isinstance(target, Drone) and target in self.drones:
                        damage = mega_damage_for_target(target, mega_shot.charge_level)
                        hp_before = target.hp
                        target.incoming_damage = max(0, target.incoming_damage - damage)
                        target.hp -= damage
                        if target.hp > 0 and not target.is_mega:
                            self.score += DRONE_HIT_SCORE * max(1, damage)
                            self.drones.remove(target)
                            children = split_regular_drone(self.drones, target)
                            self._retarget_split_shots(target, children)
                            play_sound(self.split_sound)
                        elif target.hp <= 0:
                            pos = target.pos.copy()
                            counts_for_level = drone_counts_for_level(target)
                            self.drones.remove(target)
                            if counts_for_level:
                                self.destroyed += target.level_value
                            if target.is_mega:
                                bonus = MINI_BOSS_MEGA_BONUS
                                self.score += MINI_BOSS_SCORE + bonus
                            else:
                                bonus = mega_kill_bonus(target.max_hp)
                                self.score += regular_drone_clear_score(hp_before) + bonus
                            self.bonus_points += bonus
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
