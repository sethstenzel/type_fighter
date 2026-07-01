"""Secret level 1 -- Reposition Mission 1.

A hidden bonus stage reached by selecting training mission one with Shift held
(after arming it with ``--secret_level 1`` on the command line; see
``secret_levels.py``).

Unlike a normal mission -- where the pod sits at screen centre and you clear a
quota of drones -- here you *pilot* the pod from the right side of the field to
a goal zone far off screen to the left, then hold station inside it:

* Shift+S  thrust forward (fly left)   Shift+F  thrust back (slow / reverse)
* Shift+E  thrust up                   Shift+D  thrust down

Thrust is a consumable resource (the orange gauge): each second of thrust burns
a charge, top speed is about ten charges' worth, and the bank only refills after
the engines rest for a few seconds. Combined with preserved momentum, that means
you can overshoot the target and have to drift back.

Reach the green target zone and keep the pod inside it for 10 continuous seconds
to win, within a 3-minute limit. The level is played through a
:class:`MissionEngine` subclass, so the player's normal loadout still works:
orbiting defense drones, shields, mega shot, and time stop (whatever they have
unlocked). Intro/instruction/summary screens mirror the regular missions, driven
by text under ``reposition_missions/reposition_mission_N/``.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

import cheats
import fonts
import player_limits
import lessons.mission_engine as me
from lessons.audio import (
    audio_duration_ms,
    load_sound,
    play_audio,
    play_looping_sound,
    play_sound,
    stop_audio,
    stop_looping_sound,
)
from lessons.key_render import render_inline_center, render_inline_text, render_key_label
from lessons.mission_engine import (
    ACCENT,
    BG_COLOR,
    BG_MUSIC_FADE_OUT_MS,
    MEGA_CHARGE_MAX_BLOCKS,
    MEGA_RECHARGE_DELAY_MS,
    MEGA_RECHARGE_INTERVAL_MS,
    MUTED_TEXT,
    EXPLOSION_COLOR,
    PLAYER_COLLISION_RADIUS,
    POD_IMAGE_SIZE,
    POD_ROTATION_SECONDS,
    POWER_UP_SCORE,
    SHIP_COLOR,
    TEXT_COLOR,
    THREE_SHOT_DRONE_COLOR,
    TIME_STOP_POD_ROTATION_SCALE,
    Drone,
    MissionEngine,
    draw_active_player_shield,
    draw_bullet,
    draw_button,
    draw_defense_drone,
    draw_defense_shot,
    draw_mega_bar,
    draw_mega_shot,
    draw_player_shield_bar,
    draw_power_up,
    draw_scrollable_text,
    draw_shot_trails,
    draw_ship,
    draw_star_field,
    draw_time_stop_bar,
    drone_color,
    drone_radius_for_hp,
    drone_rotation_radians_per_second,
    enforce_min_window_size,
    event_to_lesson_key,
    explode,
    format_mission_time,
    handle_power_up_key,
    load_image,
    next_power_up_time,
    pause_menu,
    queue_mega_shot,
    queue_shot_at,
    read_text,
    rotated_drone_image,
    spawn_power_up,
    toggle_fullscreen,
    update_drone_position,
)


# The goal zone is blue (matching the ship blue) and drawn quite translucent.
GOAL_COLOR = SHIP_COLOR
GOAL_GLOW_COLOR = (150, 195, 255)
# Thrust gauge (orange, styled exactly like the shield gauge).
THRUST_COLOR = (240, 158, 74)
THRUST_FRAME = (180, 120, 60)
THRUST_EMPTY = (40, 28, 18)

# Letters the chasing drones (and power-ups) use. A spread of home-row and
# upper-row keys -- shooting is a bare key press, so it never clashes with the
# Shift+key movement controls.
DRONE_KEYS = ("f", "j", "d", "k", "a", "g", "h", "l", "r", "u", "e", "i")

# Thrust as a resource: five charges, depleted/recharged in whole-square steps.
# Top speed is about MAX_THRUST charges' worth -- holding thrust accelerates at
# ACCEL, and draining the whole bank (MAX_THRUST seconds) reaches the cap.
MAX_THRUST = 5
THRUST_CONSUME_PER_SEC = 1.0
THRUST_REGEN_PER_SEC = 1.0
THRUST_REGEN_DELAY_MS = 1000
ACCEL_X = 80.0
ACCEL_Y = 80.0
VX_MAX = 400.0          # == ACCEL_X * MAX_THRUST ("five thrust worth")
VY_MAX = 400.0

# World distance to the goal. The goal sits at an EXACT world position and is
# scrolled onto the screen by the camera (see _goal_pos); it does not float
# relative to the pod. Large distance keeps it off screen until the final leg.
GOAL_DISTANCE = 18000.0
GOAL_SCALE = 0.30       # world-units -> pixels for the camera
GOAL_RADIUS = 160       # 2x the original target diameter, then a touch larger
DWELL_REQUIRED_MS = 10000  # hold inside the target this long to win

# 3-minute time limit.
TIME_LIMIT_MS = 180000

# Pod screen x as a fraction of width: starts right, slides to the left as it
# nears the goal.
POD_LEFT_X_RATIO = 0.16
POD_RIGHT_X_RATIO = 0.82
ORBIT_RADIUS = POD_IMAGE_SIZE // 2 + 85

STAR_PARALLAX = 0.6

SPAWN_INTERVAL_START_MS = 2400
SPAWN_INTERVAL_MIN_MS = 1300
MAX_ACTIVE_DRONES = 7
# Drones swept this far past a screen edge are gone for good -- drop them so the
# active-drone cap can't clog with unreachable strays (which would stop spawns).
DRONE_CULL_MARGIN = 600

THRUSTER_OFFSET = POD_IMAGE_SIZE // 2 - 6
THRUSTER_FLICKER_MS = 55

NO_EXHAUST = {"s": False, "f": False, "e": False, "d": False}


def secret_drone_hp():
    roll = random.random()
    if roll < 0.12:
        return 3
    if roll < 0.40:
        return 2
    return 1


def lerp(a, b, t):
    return a + (b - a) * t


def draw_thrust_bar(screen, font, charges, max_charges, y_offset=0, center_x=None):
    """Orange thrust gauge -- same square-block shape as the shield bar.

    Charges fill in whole-square increments (a square is lit only once its full
    charge is present).
    """
    width, _ = screen.get_size()
    if center_x is None:
        center_x = width / 2
    block = 22
    gap = 5
    max_charges = max(1, int(max_charges))
    bar_width = max_charges * block + (max_charges - 1) * gap
    bar_rect = pygame.Rect(0, 0, bar_width, block)
    bar_rect.center = (center_x, 51 + y_offset)
    for index in range(max_charges):
        rect = pygame.Rect(bar_rect.x + index * (block + gap), bar_rect.y, block, block)
        pygame.draw.rect(screen, THRUST_EMPTY, rect, border_radius=4)
        pygame.draw.rect(screen, THRUST_FRAME, rect, 2, border_radius=4)
        if charges >= index + 1:  # whole-square increments only
            pygame.draw.rect(screen, THRUST_COLOR, rect.inflate(-8, -8), border_radius=3)
    text = font.render("Thrust", True, THRUST_COLOR if charges > 0 else (110, 90, 68))
    if charges <= 0:
        text.set_alpha(160)
    screen.blit(text, text.get_rect(center=(center_x, 28 + y_offset)))


def draw_reposition_briefing_modal(screen, title_text, instructions_text, instruction_scroll):
    width, height = screen.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((2, 5, 13, 210))
    screen.blit(overlay, (0, 0))

    title_font = fonts.get_font(42, bold=True)
    body_font = fonts.get_font(21)
    button_font = fonts.get_font(26, bold=True)

    modal_width = min(width - 64, 980)
    modal_height = min(height - 32, 720)
    modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
    modal_rect.center = (width / 2, height / 2)
    pygame.draw.rect(screen, (10, 18, 36), modal_rect, border_radius=8)
    pygame.draw.rect(screen, ACCENT, modal_rect, 2, border_radius=8)

    title = title_font.render(title_text, True, TEXT_COLOR)
    screen.blit(title, title.get_rect(center=(width / 2, modal_rect.y + 52)))

    content_margin = 44
    button_rect = pygame.Rect(0, modal_rect.bottom - 78, 190, 48)
    button_rect.centerx = modal_rect.centerx
    text_rect = pygame.Rect(
        modal_rect.x + content_margin,
        modal_rect.y + 96,
        modal_rect.width - content_margin * 2,
        max(70, button_rect.y - 18 - (modal_rect.y + 96)),
    )
    max_scroll, track_rect, thumb_rect = draw_scrollable_text(
        screen, instructions_text, body_font, MUTED_TEXT, text_rect, instruction_scroll
    )
    draw_button(screen, button_rect, "Start", button_font, True)
    return button_rect, max_scroll, track_rect, thumb_rect


def run_reposition_intro(screen, clock, base_dir, level_number):
    """Scrolling intro screen mirroring the regular mission intros."""
    mission_dir = Path(base_dir) / "reposition_missions" / f"reposition_mission_{level_number}"
    intro_audio = mission_dir / f"reposition_mission_{level_number}_intro.wav"
    intro_text = read_text(mission_dir / f"reposition_mission_{level_number}_intro.txt")
    play_audio(intro_audio)

    title_font = fonts.get_font(34, bold=True)
    body_font = fonts.get_font(22)
    small_font = fonts.get_font(18, bold=True)
    prompt_font = fonts.get_font(24, bold=True)

    audio_ms = audio_duration_ms(intro_audio)
    duration = max(1, (audio_ms / 1000 if audio_ms > 0 else 55) - 6)
    stars = me.create_star_field()
    lines = []
    last_width = None
    max_scroll = 0
    scroll_speed = 0
    scroll_y = 0.0
    try:
        while True:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.VIDEORESIZE:
                    screen = enforce_min_window_size(screen)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        screen = toggle_fullscreen()
                    elif event.key == pygame.K_ESCAPE:
                        return "menu"
                    elif event.key == pygame.K_SPACE:
                        return "start"
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        scroll_y = min(max_scroll, scroll_y + 42)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        scroll_y = max(0, scroll_y - 42)
                if event.type == pygame.MOUSEWHEEL:
                    scroll_y = max(0, min(max_scroll, scroll_y - event.y * 36))
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    return "start"

            screen = pygame.display.get_surface()
            width, height = screen.get_size()
            me.update_star_field(stars, dt)
            screen.fill(BG_COLOR)
            draw_star_field(screen, stars)

            panel = pygame.Rect(0, 0, min(880, width - 100), 120)
            panel.center = (width / 2, 108)
            pygame.draw.rect(screen, (12, 20, 38), panel, border_radius=10)
            pygame.draw.rect(screen, (48, 67, 105), panel, 2, border_radius=10)
            render_inline_center(screen, f"REPOSITION MISSION {level_number}", title_font, ACCENT, panel.center)

            text_rect = pygame.Rect(panel.x, panel.bottom + 24, panel.width, height - panel.bottom - 130)
            if text_rect.width != last_width:
                lines = _wrap(intro_text, body_font, text_rect.width - 44)
                line_h = body_font.get_height() + 8
                max_scroll = max(0, len(lines) * line_h - text_rect.height + 44)
                scroll_speed = max_scroll / duration if max_scroll else 0
                scroll_y = min(scroll_y, max_scroll)
                last_width = text_rect.width
            scroll_y = min(max_scroll, scroll_y + scroll_speed * dt)

            pygame.draw.rect(screen, (14, 24, 45), text_rect, border_radius=8)
            pygame.draw.rect(screen, (48, 67, 105), text_rect, 2, border_radius=8)
            clip = screen.get_clip()
            screen.set_clip(text_rect.inflate(-20, -20))
            y = text_rect.y + 16 - scroll_y
            line_h = body_font.get_height() + 8
            for line in lines:
                if text_rect.y - line_h <= y <= text_rect.bottom:
                    render_inline_text(screen, line, body_font, TEXT_COLOR, (text_rect.x + 18, y))
                y += line_h
            screen.set_clip(clip)

            render_inline_center(
                screen, "Press ␣ to continue", prompt_font, ACCENT, (width / 2, height - 74)
            )
            screen.blit(
                small_font.render("F11: Max size  |  Esc: Menu  |  Wheel/Up/Down: Scroll", True, MUTED_TEXT),
                (text_rect.x, height - 40),
            )
            pygame.display.flip()
    finally:
        stop_audio()


def _wrap(text, font, max_width):
    from lessons.key_render import inline_text_width

    lines = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            test = f"{current} {word}".strip()
            if inline_text_width(test, font) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


class SecretLevel(MissionEngine):
    def __init__(self, screen, clock, base_dir, level_number, player=None):
        self.secret_level_number = level_number
        # Drive it as "lesson 1"; ability availability then falls out of the
        # player's completed lessons / upgrades exactly like a normal mission.
        super().__init__(screen, clock, base_dir, "lesson_1", DRONE_KEYS, player)

        # Point the briefing at this reposition mission's own text (not lesson 1).
        self.mission_dir = Path(base_dir) / "reposition_missions" / f"reposition_mission_{level_number}"
        self.instructions_text = read_text(
            self.mission_dir / f"reposition_mission_{level_number}_instructions.txt"
        )
        self.instructions_audio_path = self.mission_dir / f"reposition_mission_{level_number}_instructions.wav"
        self.instructions_audio_duration_ms = audio_duration_ms(self.instructions_audio_path)
        self.hint_images = []
        self.hint_texts = {}

        # Let time-stop power-ups drop for anyone who has time stop unlocked.
        self.time_stop_power_up_enabled = self.player_time_stop_available

        self.thrusters_image = self._load_thrusters_image()
        self.thruster_sound = load_sound(self.sfx_dir / "thrusters.wav", 0.6)
        self.thruster_channel = None

        # Flight state (momentum-based, thrust-limited).
        self.vx = 0.0
        self.vy = 0.0
        self.distance = 0.0
        width, height = self.screen.get_size()
        self.pod_y = height / 2
        self.player_center = pygame.Vector2(self._pod_screen_x(width), self.pod_y)
        self.goal_y_ratio = random.uniform(0.30, 0.70)

        self.thrust_charges = MAX_THRUST
        self.last_thrust_ms = pygame.time.get_ticks()

        self.time_left_ms = TIME_LIMIT_MS
        self.dwell_ms = 0.0

        now = pygame.time.get_ticks()
        self.next_spawn_time = now + 1200
        self.next_power_up_spawn_time = now + random.randint(9000, 15000)
        self.thruster_lit = True
        self.next_flicker_time = now + THRUSTER_FLICKER_MS

    # -- asset helpers ----------------------------------------------------
    def _load_thrusters_image(self):
        image = load_image(self.pod_gfx_dir / "thrusters.png")
        if image is None:
            return None
        # ~50% smaller on screen than the previous size.
        target_h = POD_IMAGE_SIZE // 4
        rect = image.get_rect()
        scale = target_h / rect.height if rect.height else 1.0
        return pygame.transform.smoothscale(
            image, (max(1, int(rect.width * scale)), max(1, int(rect.height * scale)))
        )

    # -- geometry ---------------------------------------------------------
    def _progress(self):
        return max(0.0, min(1.0, self.distance / GOAL_DISTANCE))

    def _pod_screen_x(self, width):
        return lerp(width * POD_RIGHT_X_RATIO, width * POD_LEFT_X_RATIO, self._progress())

    def _goal_pos(self, width, height):
        # The goal is at a FIXED world position (distance == GOAL_DISTANCE). Its
        # screen x is that position run through the camera -- anchored to a fixed
        # left reference, NOT offset from the pod's current screen x. So it holds
        # an exact spot the pod flies to (and can overshoot).
        anchor_x = width * POD_LEFT_X_RATIO
        goal_x = anchor_x - (GOAL_DISTANCE - self.distance) * GOAL_SCALE
        goal_y = height * self.goal_y_ratio
        return pygame.Vector2(goal_x, goal_y)

    # -- audio ------------------------------------------------------------
    def _set_thruster_sound(self, active):
        if active and self.thruster_channel is None:
            self.thruster_channel = play_looping_sound(self.thruster_sound)
        elif not active and self.thruster_channel is not None:
            stop_looping_sound(self.thruster_channel)
            self.thruster_channel = None

    # -- per-frame update -------------------------------------------------
    def _begin_secret_frame(self, dt, now):
        self._update_time_stop(dt)
        pod_scale = TIME_STOP_POD_ROTATION_SCALE if self.time_stop is not None else 1.0
        self.pod_rotation = (
            self.pod_rotation + math.tau * dt * pod_scale / POD_ROTATION_SECONDS
        ) % math.tau
        if self.player_mega_shot_available and self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS:
            if self.next_mega_recharge_time and now >= self.next_mega_recharge_time:
                self.mega_charge_blocks += 1
                self.next_mega_recharge_time = (
                    now + MEGA_RECHARGE_INTERVAL_MS
                    if self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS
                    else 0
                )
        if cheats.is_enabled("4"):
            self.mega_charge_blocks = MEGA_CHARGE_MAX_BLOCKS
        if cheats.is_enabled("5") and self.player_shields_available:
            self.shield_charges = min(self.max_shield_charges, cheats.CHEAT_SHIELD_CHARGES)
        if cheats.is_enabled("6"):
            self.time_stop_charges = min(self.time_stop_max_charges, cheats.CHEAT_TIME_STOP_CHARGES)

    def _apply_thrust(self, dt, now):
        keys = pygame.key.get_pressed()
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        # Each key fires the thruster on its side; the pod is pushed the opposite
        # way (real thruster physics). +vx is "forward" = leftward = toward goal.
        s_key = bool(shift and keys[pygame.K_s])  # left thruster  -> pod right
        f_key = bool(shift and keys[pygame.K_f])  # right thruster -> pod left (forward)
        e_key = bool(shift and keys[pygame.K_e])  # top thruster   -> pod down
        d_key = bool(shift and keys[pygame.K_d])  # bottom thruster-> pod up
        # Only a direction key (with Shift) counts as "using the thrusters".
        # Holding Shift by itself never counts. There is no separate empty
        # cooldown: recharge simply resumes 1s after the last direction press.
        any_held = s_key or f_key or e_key or d_key
        active = False
        if any_held:
            self.last_thrust_ms = now
            if self.thrust_charges > 0:
                self.thrust_charges = max(0.0, self.thrust_charges - THRUST_CONSUME_PER_SEC * dt)
                if f_key:
                    self.vx = min(VX_MAX, self.vx + ACCEL_X * dt)
                if s_key:
                    self.vx = max(-VX_MAX, self.vx - ACCEL_X * dt)
                if d_key:
                    self.vy = max(-VY_MAX, self.vy - ACCEL_Y * dt)
                if e_key:
                    self.vy = min(VY_MAX, self.vy + ACCEL_Y * dt)
                active = True
        elif now - self.last_thrust_ms >= THRUST_REGEN_DELAY_MS:
            self.thrust_charges = min(MAX_THRUST, self.thrust_charges + THRUST_REGEN_PER_SEC * dt)
        return {"s": s_key and active, "f": f_key and active, "e": e_key and active, "d": d_key and active}

    def _advance_flight(self, dt):
        width, height = self.screen.get_size()
        self.distance = max(0.0, self.distance + self.vx * dt)
        self.pod_y += self.vy * dt
        top = 80
        bottom = height - 70
        if self.pod_y < top:
            self.pod_y = top
            self.vy = max(0.0, self.vy)
        elif self.pod_y > bottom:
            self.pod_y = bottom
            self.vy = min(0.0, self.vy)
        self.player_center = pygame.Vector2(self._pod_screen_x(width), self.pod_y)

    def _update_stars(self, dt):
        width, height = self.screen.get_size()
        # Pod flies left, so the world sweeps right.
        dx = self.vx * STAR_PARALLAX * dt
        dy = -self.vy * STAR_PARALLAX * dt
        for star in self.stars:
            star.x_ratio = (star.x_ratio + dx * star.speed_scale / width) % 1
            star.y_ratio = (star.y_ratio + dy * star.speed_scale / height) % 1

    def _spawn_position(self):
        width, height = self.screen.get_size()
        margin = 70
        # Spawn side follows where the pod actually is: drones come from ahead
        # when it hugs the right, chase from behind (the right) once it reaches
        # the left near the goal, and from all sides in the middle.
        pod_fraction = self.player_center.x / max(1, width)
        if pod_fraction > 0.6:
            side = "left"  # pod on the right -> drones ahead of it (left)
        elif pod_fraction < 0.4:
            side = "right"  # pod on the left -> drones chase from behind (right)
        else:
            side = random.choice(("top", "right", "bottom", "left"))
        if side == "right":
            return pygame.Vector2(width + margin, random.randint(0, height))
        if side == "left":
            return pygame.Vector2(-margin, random.randint(0, height))
        if side == "top":
            return pygame.Vector2(random.randint(0, width), -margin)
        return pygame.Vector2(random.randint(0, width), height + margin)

    def _secret_spawn_interval(self):
        return int(lerp(SPAWN_INTERVAL_START_MS, SPAWN_INTERVAL_MIN_MS, self._progress()))

    def _spawn_secret_drone(self):
        hp = secret_drone_hp()
        letters = [key for key in self.target_keys if len(key) == 1 and key.isalpha()] or list(DRONE_KEYS)
        drone = Drone(
            pos=self._spawn_position(),
            letter=random.choice(letters),
            hp=hp,
            max_hp=hp,
            radius=drone_radius_for_hp(hp),
            # Speed scales with closeness to the goal: 2x far away, up to 3x at it.
            speed=random.uniform(66, 96) * (2.0 + self._progress()),
        )
        self.drones.append(drone)

    def _spawn_secret_entities(self, now):
        if self.time_stop is not None:
            self.next_spawn_time = now + self._secret_spawn_interval()
            if self.next_power_up_spawn_time <= now:
                self.next_power_up_spawn_time = now + 1
            return
        if now >= self.next_spawn_time and len(self.drones) < MAX_ACTIVE_DRONES:
            self._spawn_secret_drone()
            self.next_spawn_time = now + self._secret_spawn_interval()
        if self.power_up is not None and now >= self.power_up.expires_at:
            self.power_up = None
            self.next_power_up_spawn_time = next_power_up_time(now)
        if self.power_up is None and now >= self.next_power_up_spawn_time:
            self.power_up = spawn_power_up(
                self.screen,
                self.target_keys,
                now,
                shield_enabled=self.player_shields_available,
                shield_charges=self.shield_charges,
                max_shield_charges=self.max_shield_charges,
                life_enabled=self.life_power_ups_spawned < me.MAX_LIFE_POWER_UPS_PER_MISSION,
                blocked_center=self.player_center,
                blocked_rects=self._power_up_blocked_rects(),
                time_stop_enabled=self.time_stop_power_up_enabled and self.player_time_stop_available,
                time_stop_charges=self.time_stop_charges,
                max_time_stop_charges=self.time_stop_max_charges,
            )
            if self.power_up is None:
                self.next_power_up_spawn_time = next_power_up_time(now)
            elif self.power_up.kind == "life":
                self.life_power_ups_spawned += 1

    def _update_secret_drones(self, now, dt):
        center = self.player_center
        width, height = self.screen.get_size()
        for drone in self.drones[:]:
            object_scale = self._object_time_scale(drone.pos)
            object_dt = dt * object_scale
            update_drone_position(drone, center, object_dt)
            # World objects: the pod's forward speed sweeps them across the screen.
            drone.pos.x += self.vx * object_dt
            drone.rotation = (drone.rotation + drone_rotation_radians_per_second(drone) * object_dt) % math.tau
            # Drop strays swept far off screen so they don't clog the spawn cap.
            if (
                drone.pos.x < -DRONE_CULL_MARGIN
                or drone.pos.x > width + DRONE_CULL_MARGIN
                or drone.pos.y < -DRONE_CULL_MARGIN
                or drone.pos.y > height + DRONE_CULL_MARGIN
            ):
                self.drones.remove(drone)
                continue
            if object_scale >= 1.0 and drone.pos.distance_to(center) <= drone.radius + PLAYER_COLLISION_RADIUS:
                self.drones.remove(drone)
                explode(self.particles, drone.pos, 12)
                play_sound(self.explosion_sound)
                if cheats.is_enabled("3"):
                    continue
                self.hits_taken += 1
                if self._absorb_player_hit_with_shield(now):
                    continue
                if cheats.is_enabled("2"):
                    continue
                self.lives -= 1
                self._save_player_resources()
                if self.lives <= 0:
                    explode(self.particles, center, 36)
                    return "lost"
        return None

    # -- drawing ----------------------------------------------------------
    def _draw_thrusters(self, exhaust, now):
        if self.thrusters_image is None:
            return
        if now >= self.next_flicker_time:
            self.thruster_lit = random.random() < 0.82
            self.next_flicker_time = now + THRUSTER_FLICKER_MS
        if not self.thruster_lit:
            return
        # Each key fires the thruster on its own side; the pod is pushed away
        # from those flames (real thruster physics).
        directions = {
            "s": pygame.Vector2(-1, 0),  # left thruster   -> pod pushed right
            "f": pygame.Vector2(1, 0),   # right thruster  -> pod pushed left
            "e": pygame.Vector2(0, -1),  # top thruster    -> pod pushed down
            "d": pygame.Vector2(0, 1),   # bottom thruster -> pod pushed up
        }
        for name, exhaust_dir in directions.items():
            if not exhaust[name]:
                continue
            theta = math.atan2(exhaust_dir.y, exhaust_dir.x)
            rotation_deg = -math.degrees(theta) + 90
            rotated = pygame.transform.rotozoom(self.thrusters_image, rotation_deg, 1.0)
            pos = self.player_center + exhaust_dir * THRUSTER_OFFSET
            self.screen.blit(rotated, rotated.get_rect(center=pos))

    def _draw_goal(self, goal_pos, width):
        if goal_pos.x + GOAL_RADIUS < -40 or goal_pos.x - GOAL_RADIUS > width + 40:
            return
        pulse = (math.sin(pygame.time.get_ticks() / 240) + 1) / 2
        size = GOAL_RADIUS * 2 + 24
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        c = glow.get_rect().center
        pygame.draw.circle(glow, (*GOAL_COLOR, 26), c, GOAL_RADIUS + 8)
        pygame.draw.circle(glow, (*GOAL_GLOW_COLOR, 70 + int(55 * pulse)), c, GOAL_RADIUS, 4)
        pygame.draw.circle(glow, (*GOAL_COLOR, 16), c, int(GOAL_RADIUS * 0.6))
        self.screen.blit(glow, glow.get_rect(center=goal_pos))
        # Dwell progress: a ring that fills as you hold station.
        if self.dwell_ms > 0:
            frac = min(1.0, self.dwell_ms / DWELL_REQUIRED_MS)
            ring = pygame.Rect(0, 0, GOAL_RADIUS * 2, GOAL_RADIUS * 2)
            ring.center = (int(goal_pos.x), int(goal_pos.y))
            start = math.pi / 2
            pygame.draw.arc(self.screen, GOAL_GLOW_COLOR, ring, start, start + math.tau * frac, 7)

    def _draw_goal_indicator(self, goal_pos):
        direction = goal_pos - self.player_center
        if direction.length_squared() == 0:
            return
        direction = direction.normalize()
        tip = self.player_center + direction * ORBIT_RADIUS
        side = pygame.Vector2(-direction.y, direction.x)
        points = [tip + direction * 12, tip - direction * 8 + side * 9, tip - direction * 8 - side * 9]
        pygame.draw.polygon(self.screen, SHIP_COLOR, points)

    def _draw_ability_bars(self, width):
        bars = []
        if self.player_mega_shot_available:
            bars.append("mega")
        if self.player_shields_available:
            bars.append("shield")
        if self.player_time_stop_available:
            bars.append("time_stop")
        spacing = 200
        start_x = width / 2 - (len(bars) - 1) * spacing / 2
        shield_center_x = None
        for index, bar in enumerate(bars):
            center_x = start_x + index * spacing
            if bar == "mega":
                mega_text = "Adv. Mega Shot" if self.player_advanced_mega_shot_available else "Mega Shot"
                draw_mega_bar(self.screen, self.font, mega_text, self.mega_charge_blocks, self.mega_charge_blocks > 0, center_x)
            elif bar == "shield":
                draw_player_shield_bar(self.screen, self.font, self.shield_charges, True, 0, self.max_shield_charges, center_x)
                shield_center_x = center_x
            else:
                draw_time_stop_bar(self.screen, self.font, self.time_stop_charges, True, 0, self.time_stop_max_charges, center_x)
        # Thrust gauge: same shape/side as the shield bar, directly below it.
        thrust_x = shield_center_x if shield_center_x is not None else width / 2
        draw_thrust_bar(self.screen, self.font, self.thrust_charges, MAX_THRUST, 52, thrust_x)

    def _draw_hud(self, width, height):
        progress = self._progress()
        self.screen.blit(self.font.render("REPOSITION", True, TEXT_COLOR), (22, 16))
        bar_x, bar_y, bar_w = 24, 50, 240
        pygame.draw.rect(self.screen, (28, 40, 66), (bar_x, bar_y, bar_w, 12), border_radius=6)
        pygame.draw.rect(self.screen, SHIP_COLOR, (bar_x, bar_y, int(bar_w * progress), 12), border_radius=6)
        pygame.draw.rect(self.screen, (70, 90, 130), (bar_x, bar_y, bar_w, 12), 1, border_radius=6)
        small = fonts.get_font(18)
        self.screen.blit(small.render(f"{int(progress * 100)}%", True, MUTED_TEXT), (bar_x + bar_w + 10, bar_y - 3))

        seconds_left = max(0, int(self.time_left_ms // 1000))
        timer_color = THREE_SHOT_DRONE_COLOR if seconds_left <= 30 else TEXT_COLOR
        timer_font = fonts.get_font(30, bold=True)
        timer_surface = timer_font.render(f"{seconds_left // 60}:{seconds_left % 60:02d}", True, timer_color)
        self.screen.blit(timer_surface, (width - timer_surface.get_width() - 22, 14))
        score_surface = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_surface, (width - score_surface.get_width() - 22, 50))
        life_surface = self.font.render(f"Lives: {self.lives}", True, MUTED_TEXT)
        self.screen.blit(life_surface, (width - life_surface.get_width() - 22, 78))

        # Hold countdown while inside the target.
        if self.dwell_ms > 0:
            remaining = max(0.0, (DWELL_REQUIRED_MS - self.dwell_ms) / 1000)
            hold_font = fonts.get_font(26, bold=True)
            hold = hold_font.render(f"HOLD  {remaining:0.1f}s", True, GOAL_COLOR)
            self.screen.blit(hold, hold.get_rect(center=(width / 2, height - 58)))

        footer_font = fonts.get_font(18)
        footer = "Shift+S/F/E/D: Fire thrusters (pod pushes opposite)   Type letters to fire   Esc: Pause"
        footer_surface = footer_font.render(footer, True, MUTED_TEXT)
        self.screen.blit(footer_surface, footer_surface.get_rect(center=(width / 2, height - 26)))

    def _draw_frame(self, exhaust, now, present=True):
        self.screen = pygame.display.get_surface()
        width, height = self.screen.get_size()
        if self.active_shield_hits > 0 and now >= self.active_shield_expires_at:
            self._clear_active_shield()
        self.screen.fill(BG_COLOR)
        draw_star_field(self.screen, self.stars)

        goal_pos = self._goal_pos(width, height)
        self._draw_goal(goal_pos, width)

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

        for drone in self.drones:
            image = rotated_drone_image(drone, self.drone_images, self.drone_image_cache)
            if image is None:
                color = drone_color(drone)
                pygame.draw.circle(self.screen, color, drone.pos, drone.radius)
                pygame.draw.circle(self.screen, (255, 231, 214), drone.pos, drone.radius, 2)
            else:
                self.screen.blit(image, image.get_rect(center=drone.pos))
            label_font = fonts.get_font(28, bold=True)
            render_key_label(self.screen, drone.letter, label_font, (8, 10, 18), drone.pos, drone.radius * 1.45)

        self._draw_thrusters(exhaust, now)
        draw_ship(self.screen, self.turret_angle, self.pod_rotation, self.turret_image, self.pod_image, self.player_center)
        for defense_drone in self.defense_drones:
            draw_defense_drone(self.screen, defense_drone, self.player_center, self.defense_drone_image)
        draw_active_player_shield(self.screen, self.player_center, self.active_shield_expires_at, self.active_shield_hits, now)
        self._draw_time_stop_ring()

        self._draw_ability_bars(width)
        self._draw_hud(width, height)
        self._draw_goal_indicator(goal_pos)
        if present:
            pygame.display.flip()

    # -- main loop --------------------------------------------------------
    def run(self):
        briefing = self._run_reposition_briefing()
        if briefing != "start":
            self._stop_all_music(BG_MUSIC_FADE_OUT_MS)
            return briefing
        pygame.mouse.set_visible(False)
        pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        # Rebase timers so the (variable-length) briefing doesn't burst spawns or
        # stall thrust regen the instant gameplay starts.
        start_now = pygame.time.get_ticks()
        self.next_spawn_time = start_now + 1200
        self.next_power_up_spawn_time = start_now + random.randint(9000, 15000)
        self.last_thrust_ms = start_now
        self.next_flicker_time = start_now + THRUSTER_FLICKER_MS

        while True:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            now = pygame.time.get_ticks()
            self._begin_secret_frame(dt, now)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return self._end("quit")
                if event.type == pygame.VIDEORESIZE:
                    self.screen = enforce_min_window_size(self.screen)
                if event.type == pygame.KEYDOWN:
                    started_space_charge = False
                    if event.key == pygame.K_F11:
                        self.screen = toggle_fullscreen()
                        continue
                    if event.key == pygame.K_ESCAPE:
                        paused = self._handle_pause()
                        if paused == "resume":
                            continue
                        return paused
                    if cheats.is_enabled("14") and event.key == pygame.K_LCTRL:
                        if self._register_ctrl_tap(now):
                            self.auto_fire_enabled = not self.auto_fire_enabled
                        continue
                    if event.key == pygame.K_SPACE:
                        if self.player_mega_shot_available:
                            self.space_held = True
                            started_space_charge = True
                        if self.player_time_stop_available and self._register_space_tap(now):
                            continue
                    if event.mod & pygame.KMOD_SHIFT:
                        continue  # Shift+key steers the pod, never fires
                    pressed_key = event_to_lesson_key(event, self.lesson_number)
                    if not pressed_key:
                        continue
                    collected, consumed = handle_power_up_key(self.power_up, pressed_key)
                    if collected:
                        if collected == "shield":
                            self.shield_charges = min(self.max_shield_charges, self.shield_charges + 1)
                        elif collected == "time_stop":
                            self.time_stop_charges = min(self.time_stop_max_charges, self.time_stop_charges + 1)
                        else:
                            self.lives = min(player_limits.MAX_PLAYER_LIVES, self.lives + 1)
                        self.score += POWER_UP_SCORE
                        self._save_player_resources()
                        play_sound(self.health_sound)
                        self.power_up = None
                        self.next_power_up_spawn_time = next_power_up_time(now)
                    if consumed:
                        self._record_accurate_input(now)
                        continue
                    if pressed_key in self.target_keys:
                        if (
                            self.player_mega_shot_available
                            and self.space_held
                            and not started_space_charge
                            and self.mega_charge_blocks > 0
                        ):
                            queued_mega = queue_mega_shot(
                                self.drones,
                                [],
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
                        if queue_shot_at(self.drones, self.pending_shots, pressed_key, self.player_center, now):
                            self._record_accurate_input(now)
                        else:
                            self._record_inaccurate_key(pressed_key, now)
                    elif not started_space_charge:
                        self._record_inaccurate_key(pressed_key, now)
                if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                    self.space_held = False

            width, height = self.screen.get_size()
            if self.time_stop is None:
                exhaust = self._apply_thrust(dt, now)
                self._advance_flight(dt)
                self._update_stars(dt)
                self.time_left_ms = max(0, self.time_left_ms - dt * 1000)
                goal_pos = self._goal_pos(width, height)
                if self.player_center.distance_to(goal_pos) <= GOAL_RADIUS:
                    self.dwell_ms = min(DWELL_REQUIRED_MS, self.dwell_ms + dt * 1000)
                else:
                    self.dwell_ms = 0.0
            else:
                exhaust = NO_EXHAUST
            self._set_thruster_sound(self.time_stop is None and any(exhaust.values()))

            if cheats.is_enabled("14") and self.auto_fire_enabled:
                self._auto_fire_turret(now)
            self._process_pending_shots(now, dt)
            self._spawn_secret_entities(now)
            self._update_defense_drones(now, dt)
            self._update_defense_shots(dt)
            result = self._update_secret_drones(now, dt)
            if result is not None:
                return self._end("lost")
            self._update_bullets(now, dt)
            self._update_mega_shots(now, dt)
            self._update_particles(dt)
            self._update_shot_trails(dt)

            if self.dwell_ms >= DWELL_REQUIRED_MS:
                return self._end("won")
            if self.time_left_ms <= 0:
                return self._end("timeup")

            self._draw_frame(exhaust, now)

    def _handle_pause(self):
        self._set_thruster_sound(False)
        pygame.mouse.set_visible(True)
        if self.bg_music_channel is not None:
            self.bg_music_channel.pause()
        result = pause_menu(self.screen, self.clock, self.button_press_sound)
        if result == "resume":
            pygame.mouse.set_visible(False)
            if self.bg_music_channel is not None:
                self.bg_music_channel.unpause()
            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN))
            return "resume"
        self._stop_all_music(BG_MUSIC_FADE_OUT_MS)
        stop_audio()
        if result == "quit":
            return "quit"
        if result == "restart":
            return "restart"
        return "menu"

    def _end(self, kind):
        self._set_thruster_sound(False)
        self._stop_all_music(BG_MUSIC_FADE_OUT_MS)
        stop_audio()
        self._save_player_resources()
        if kind == "quit":
            return "quit"
        won = kind == "won"
        if won:
            play_sound(self.victory_sound)
        return self._show_summary(won, kind)

    # -- briefing / summary screens --------------------------------------
    def _run_reposition_briefing(self):
        play_audio(self.instructions_audio_path)
        previous_mouse_visible = pygame.mouse.get_visible()
        pygame.mouse.set_visible(True)
        instruction_scroll = 0
        max_scroll = 0
        scroll_speed = 0
        start_button = pygame.Rect(0, 0, 0, 0)
        track_rect = None
        thumb_rect = None
        dragging = False
        drag_offset = 0
        audio_seconds = (
            self.instructions_audio_duration_ms / 1000 if self.instructions_audio_duration_ms > 0 else 40
        )
        scroll_duration = max(1, audio_seconds - 4)
        title = f"Reposition Mission {self.secret_level_number}"
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
                        elif event.key == pygame.K_ESCAPE:
                            stop_audio()
                            return "menu"
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            instruction_scroll = min(max_scroll, instruction_scroll + 42)
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            instruction_scroll = max(0, instruction_scroll - 42)
                        elif event.key == pygame.K_SPACE:
                            stop_audio()
                            return "start"
                    if event.type == pygame.MOUSEWHEEL:
                        instruction_scroll = max(0, min(max_scroll, instruction_scroll - event.y * 36))
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if thumb_rect is not None and thumb_rect.collidepoint(event.pos):
                            dragging = True
                            drag_offset = event.pos[1] - thumb_rect.y
                            continue
                        if start_button.collidepoint(event.pos):
                            stop_audio()
                            return "start"
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        dragging = False
                    if event.type == pygame.MOUSEMOTION and dragging and track_rect is not None and thumb_rect is not None and max_scroll > 0:
                        travel = max(1, track_rect.height - thumb_rect.height)
                        thumb_y = max(track_rect.y, min(event.pos[1] - drag_offset, track_rect.y + travel))
                        instruction_scroll = max_scroll * (thumb_y - track_rect.y) / travel

                if not dragging:
                    instruction_scroll = min(max_scroll, instruction_scroll + scroll_speed * dt)
                self._draw_frame(NO_EXHAUST, now, present=False)
                start_button, max_scroll, track_rect, thumb_rect = draw_reposition_briefing_modal(
                    self.screen, title, self.instructions_text, instruction_scroll
                )
                scroll_speed = max_scroll / scroll_duration if max_scroll else 0
                instruction_scroll = max(0, min(instruction_scroll, max_scroll))
                pygame.display.flip()
        finally:
            pygame.mouse.set_visible(previous_mouse_visible)

    def _show_summary(self, won, kind):
        title_font = fonts.get_font(56, bold=True)
        body_font = fonts.get_font(24)
        if won:
            title, accent = "REPOSITION COMPLETE", GOAL_COLOR
        elif kind == "timeup":
            title, accent = "OUT OF TIME", (231, 194, 111)
        else:
            title, accent = "POD DESTROYED", THREE_SHOT_DRONE_COLOR
        level_time_ms = TIME_LIMIT_MS - self.time_left_ms
        accuracy_inputs = self.accurate_inputs + self.inaccurate_inputs
        accuracy = 100 if accuracy_inputs == 0 else round(self.accurate_inputs * 100 / accuracy_inputs)
        rows = [
            ("Time", format_mission_time(int(level_time_ms))),
            ("Score", str(self.score)),
            ("Drones destroyed", str(int(self.destroyed))),
            ("Hits taken", str(self.hits_taken)),
            ("Accuracy", f"{accuracy}%"),
            ("Accurate keys", str(self.accurate_inputs)),
            ("Inaccurate keys", str(self.inaccurate_inputs)),
        ]
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.VIDEORESIZE:
                    self.screen = enforce_min_window_size(self.screen)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.screen = toggle_fullscreen()
                    elif event.key == pygame.K_r:
                        return "restart"
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                        return "won" if won else "menu"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    return "won" if won else "menu"

            self.screen = pygame.display.get_surface()
            width, height = self.screen.get_size()
            self.screen.fill(BG_COLOR)
            draw_star_field(self.screen, self.stars)
            modal_rect = pygame.Rect(0, 0, min(560, width - 80), min(520, height - 24))
            modal_rect.center = (width / 2, height / 2)
            pygame.draw.rect(self.screen, (10, 18, 34), modal_rect, border_radius=8)
            pygame.draw.rect(self.screen, accent, modal_rect, 2, border_radius=8)
            title_surface = title_font.render(title, True, accent)
            self.screen.blit(title_surface, title_surface.get_rect(center=(width / 2, modal_rect.y + 56)))
            for index, (label, value) in enumerate(rows):
                y = modal_rect.y + 116 + index * 38
                self.screen.blit(body_font.render(label, True, MUTED_TEXT), (modal_rect.x + 54, y))
                value_surface = body_font.render(value, True, TEXT_COLOR)
                self.screen.blit(value_surface, (modal_rect.right - value_surface.get_width() - 54, y))
            render_inline_center(
                self.screen, "Enter: Menu    R: Retry", body_font, MUTED_TEXT, (width / 2, modal_rect.bottom - 40)
            )
            pygame.display.flip()
            self.clock.tick(60)


def run_secret_level(screen, clock, base_dir, level_number, player=None):
    previous_mouse_visible = pygame.mouse.get_visible()
    pygame.mouse.set_visible(False)
    try:
        intro = run_reposition_intro(screen, clock, base_dir, level_number)
        if intro == "quit":
            return "quit"
        if intro == "menu":
            return "menu"
        while True:
            result = SecretLevel(screen, clock, base_dir, level_number, player).run()
            if result != "restart":
                return result
    finally:
        pygame.mouse.set_visible(previous_mouse_visible)
