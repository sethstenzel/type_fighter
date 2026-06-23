from dataclasses import dataclass
import math
import random
from pathlib import Path

import pygame

from lessons.key_render import display_key, render_inline_center, render_inline_text, render_key_label


BASE_SCREEN_SIZE = (1024, 768)
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
SHIP_COLOR = (112, 170, 255)
EXPLOSION_COLOR = (255, 218, 125)
POD_ROTATION_SECONDS = 15
TURRET_TURN_SPEED = 13
TURRET_FIRE_ANGLE_THRESHOLD = 0.08
TURRET_FIRE_DELAY_MS = 90

START_SPAWN_INTERVAL_MS = 6000
MIN_SPAWN_INTERVAL_MS = 2000
MIN_DRONE_SPAWN_RATE = 0.1
MAX_DRONE_SPAWN_RATE = 0.5
SPAWN_RATE_CHANGE_MS = 15000
KILLS_PER_DIFFICULTY_TIER = 5
STARTING_LIVES = 3
DRONE_SPEED_BONUS_PER_TIER = 6
MINI_BOSS_INTERVAL = 10
MEGA_DRONE_HP = 5
MEGA_ATTACK_INTERVAL_MS = 3000
MEGA_ROTATION_SECONDS = 3
BOSS_SHOT_RADIUS = 11
MINI_BOSS_SHOT_RADIUS = 20
BOSS_SHOT_SPEED = 190
FINAL_BOSS_SHOT_SPEED = 142
FINAL_BOSS_HP = 1
FINAL_BOSS_RADIUS = 87
FINAL_BOSS_SHIELD_MAX = 3
FINAL_BOSS_SHIELD_DOWN_MS = 15000
FINAL_BOSS_SHIELD_RECHARGE_MS = 5000
FINAL_BOSS_ATTACK_INTERVAL_MS = 8000
FINAL_BOSS_APPROACH_SPEED = 90
FINAL_BOSS_ORBIT_SECONDS = 10
FINAL_BOSS_ORBIT_DISTANCE_SCALE = 1.2
FINAL_BOSS_ORBIT_SWITCH_MIN_MS = 10000
FINAL_BOSS_ORBIT_SWITCH_MAX_MS = 30000
MINI_BOSS_STRAFE_RANGE = 95
MINI_BOSS_STRAFE_SPEED_SCALE = 0.45
MINI_BOSS_CENTER_DISTANCE_SCALE = 0.25
PLAYER_SHIELD_MAX_CHARGES = 3
PLAYER_SHIELD_RECHARGE_MS = 20000
MEGA_CHARGE_MAX_BLOCKS = 5
MEGA_RECHARGE_INTERVAL_MS = 1000
MEGA_RECHARGE_DELAY_MS = 1000
MEGA_SHIELD_MIN_LEVEL = 3
MEGA_FINAL_KILL_LEVEL = 5
POWER_UP_DURATION_MS = 10000
POWER_UP_MIN_INTERVAL_MS = 18000
POWER_UP_MAX_INTERVAL_MS = 32000
POWER_UP_COLOR = (88, 214, 141)
BG_MUSIC_VOLUME = 0.35
BG_MUSIC_FADE_IN_MS = 1800
BG_MUSIC_FADE_OUT_MS = 700
STAR_COUNT = 150
STAR_DRIFT_SPEED = 10
LESSON_DIR_NAME = "lesson_1"
VALID_KEYS = ("f", "j")
SPECIAL_KEY_LABELS = {
    pygame.K_SPACE: "space",
    pygame.K_RETURN: "enter",
    pygame.K_BACKSPACE: "backspace",
    pygame.K_TAB: "tab",
    pygame.K_CAPSLOCK: "caps lock",
    pygame.K_LSHIFT: "shift",
    pygame.K_RSHIFT: "shift",
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


@dataclass
class MegaShot:
    pos: pygame.Vector2
    vel: pygame.Vector2
    charge_level: int
    target: object | None
    radius: int = 10


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


@dataclass
class PowerUp:
    pos: pygame.Vector2
    letters: tuple[str, str]
    expires_at: int
    progress: int = 0


@dataclass
class Particle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    ttl: float


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
    if screen.get_flags() & pygame.FULLSCREEN:
        return pygame.display.set_mode(BASE_SCREEN_SIZE, pygame.RESIZABLE)
    return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)


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
    return destroyed // KILLS_PER_DIFFICULTY_TIER


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


def final_boss_enabled(lesson_number):
    return lesson_number >= 5


def mission_target_keys(valid_keys, lesson_number):
    return tuple(
        key
        for key in valid_keys
        if not (mega_shot_enabled(lesson_number) and key == "space")
    )


def player_shield_enabled(lesson_number):
    return lesson_number >= 10


def final_boss_projectile_count(lesson_number):
    if lesson_number > 20:
        return 3
    if lesson_number > 10:
        return 2
    return 1


def mini_boss_numbers_for_lesson(lesson_number, drone_target):
    if not mini_bosses_enabled(lesson_number):
        return set()
    return set(range(MINI_BOSS_INTERVAL, drone_target + 1, MINI_BOSS_INTERVAL))


def active_mini_boss_count(drones):
    return sum(1 for drone in drones if drone.is_mega)


def random_spawn_interval():
    drones_per_second = random.uniform(MIN_DRONE_SPAWN_RATE, MAX_DRONE_SPAWN_RATE)
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


def spawn_drone(drones, screen, destroyed, valid_keys, is_mega=False):
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
        letter=random.choice(valid_keys),
        hp=hp,
        max_hp=hp,
        radius=42 if is_mega else drone_radius_for_hp(hp),
        speed=(random.uniform(38, 52) if is_mega else random.uniform(50, 75)) + speed_bonus,
        is_mega=is_mega,
        target_pos=target_pos,
        strafe_axis=strafe_axis,
        strafe_direction=random.choice((-1, 1)),
    )
    drones.append(drone)
    return drone


def spawn_next_drone(drones, screen, destroyed, valid_keys, spawned_count, mini_boss_numbers):
    spawned_count += 1
    drone = spawn_drone(
        drones,
        screen,
        destroyed,
        valid_keys,
        is_mega=spawned_count in mini_boss_numbers,
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
        )
        drones.append(child)


def next_power_up_time(now):
    return now + random.randint(POWER_UP_MIN_INTERVAL_MS, POWER_UP_MAX_INTERVAL_MS)


def spawn_power_up(screen, valid_keys, now):
    width, height = screen.get_size()
    margin = 90
    power_up_keys = [key for key in valid_keys if len(key) == 1 and key.isalpha()] or list(valid_keys)
    keys = random.choices(power_up_keys, k=2)
    return PowerUp(
        pos=pygame.Vector2(
            random.randint(margin, max(margin, width - margin)),
            random.randint(margin, max(margin, height - margin)),
        ),
        letters=(keys[0], keys[1]),
        expires_at=now + POWER_UP_DURATION_MS,
    )


def handle_power_up_key(power_up, pressed_key):
    if power_up is None:
        return False, False
    if pressed_key == power_up.letters[power_up.progress]:
        power_up.progress += 1
        return power_up.progress >= len(power_up.letters), True
    power_up.progress = 0
    return False, False


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
                vel=direction * 820,
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


def spawn_final_boss(screen, now, valid_keys):
    center = screen_center(screen)
    spawn_pos = pygame.Vector2(center.x, 128)
    target_pos = spawn_pos.lerp(center, 0.5)
    return FinalBoss(
        pos=spawn_pos,
        target_pos=target_pos,
        letter=random.choice(valid_keys),
        orbit_angle=math.atan2(target_pos.y - center.y, target_pos.x - center.x),
        orbit_radius=target_pos.distance_to(center) * FINAL_BOSS_ORBIT_DISTANCE_SCALE,
        orbit_direction=random.choice((-1, 1)),
        next_shot_time=now + FINAL_BOSS_ATTACK_INTERVAL_MS,
        next_orbit_switch_time=now + random.randint(FINAL_BOSS_ORBIT_SWITCH_MIN_MS, FINAL_BOSS_ORBIT_SWITCH_MAX_MS),
    )


def update_final_boss_movement(final_boss, screen, dt, now):
    center = screen_center(screen)
    if not final_boss.is_orbiting:
        travel = final_boss.target_pos - final_boss.pos
        distance = travel.length()
        if distance <= FINAL_BOSS_APPROACH_SPEED * dt:
            final_boss.pos = final_boss.target_pos.copy()
            final_boss.is_orbiting = True
            final_boss.orbit_angle = math.atan2(final_boss.pos.y - center.y, final_boss.pos.x - center.x)
            final_boss.orbit_radius = max(90, final_boss.pos.distance_to(center) * FINAL_BOSS_ORBIT_DISTANCE_SCALE)
            final_boss.pos = center + pygame.Vector2(
                math.cos(final_boss.orbit_angle),
                math.sin(final_boss.orbit_angle),
            ) * final_boss.orbit_radius
        elif distance > 0:
            final_boss.pos += travel.normalize() * FINAL_BOSS_APPROACH_SPEED * dt
        return

    if now >= final_boss.next_orbit_switch_time:
        final_boss.orbit_direction *= -1
        final_boss.next_orbit_switch_time = now + random.randint(
            FINAL_BOSS_ORBIT_SWITCH_MIN_MS,
            FINAL_BOSS_ORBIT_SWITCH_MAX_MS,
        )

    final_boss.orbit_angle += final_boss.orbit_direction * math.tau * dt / FINAL_BOSS_ORBIT_SECONDS
    final_boss.pos = center + pygame.Vector2(
        math.cos(final_boss.orbit_angle),
        math.sin(final_boss.orbit_angle),
    ) * final_boss.orbit_radius


def update_final_boss_shield(final_boss, now):
    return


def fire_mega_drone(drones, boss, center, valid_keys):
    direction = center - boss.pos
    if direction.length_squared() == 0:
        direction = pygame.Vector2(0, 1)
    direction = direction.normalize()
    drones.append(
        Drone(
            pos=boss.pos + direction * (boss.radius + BOSS_SHOT_RADIUS + 4),
            letter=random.choice(valid_keys),
            hp=1,
            max_hp=1,
            radius=MINI_BOSS_SHOT_RADIUS,
            speed=BOSS_SHOT_SPEED,
            is_boss_shot=True,
        )
    )


def fire_final_boss_drones(drones, final_boss, center, valid_keys, count=1):
    direction = center - final_boss.pos
    if direction.length_squared() == 0:
        direction = pygame.Vector2(0, 1)
    direction = direction.normalize()
    spread_step = math.radians(14)
    start_angle = -spread_step * (count - 1) / 2
    for index in range(count):
        shot_direction = direction.rotate_rad(start_angle + spread_step * index)
        drones.append(
            Drone(
                pos=final_boss.pos + shot_direction * (final_boss.radius + BOSS_SHOT_RADIUS + 6),
                letter=random.choice(valid_keys),
                hp=1,
                max_hp=1,
                radius=BOSS_SHOT_RADIUS,
                speed=FINAL_BOSS_SHOT_SPEED,
                is_boss_shot=True,
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


def draw_ship(screen, turret_angle, pod_rotation, turret_image=None, pod_image=None):
    center = screen_center(screen)
    if pod_image is not None:
        rotated_pod = pygame.transform.rotate(pod_image, -math.degrees(pod_rotation))
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
        rotated = pygame.transform.rotate(turret_image, -math.degrees(turret_angle) - 90)
        screen.blit(rotated, rotated.get_rect(center=center))
    else:
        barrel_direction = pygame.Vector2(math.cos(turret_angle), math.sin(turret_angle))
        turret_base = center + barrel_direction * 2
        turret_tip = center + barrel_direction * 36
        pygame.draw.line(screen, ACCENT, turret_base, turret_tip, 8)
        pygame.draw.circle(screen, (225, 243, 255), turret_base, 11)
        pygame.draw.circle(screen, ACCENT, turret_base, 7)


def draw_power_up(screen, power_up):
    if power_up is None:
        return
    rect = pygame.Rect(0, 0, 66, 52)
    rect.center = power_up.pos
    pygame.draw.rect(screen, POWER_UP_COLOR, rect, border_radius=8)
    pygame.draw.rect(screen, (226, 255, 235), rect, 3, border_radius=8)

    label_text = " ".join(display_key(key) for key in power_up.letters)
    label_font = pygame.font.SysFont("arial", 24, bold=True)
    render_inline_center(screen, label_text, label_font, (5, 24, 12), rect.center)

    if power_up.progress:
        pip_rect = pygame.Rect(rect.x + 8, rect.bottom - 9, 24, 4)
        pygame.draw.rect(screen, (5, 24, 12), pip_rect)


def draw_final_boss(screen, final_boss):
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

    points = polygon_points(final_boss.pos, final_boss.radius, 6, final_boss.rotation - math.pi / 2)
    pygame.draw.polygon(screen, FINAL_BOSS_COLOR, points)
    pygame.draw.polygon(screen, (229, 214, 255), points, 3)
    label_font = pygame.font.SysFont("arial", 46, bold=True)
    render_key_label(screen, final_boss.letter, label_font, (8, 10, 18), final_boss.pos, final_boss.radius * 1.25)


def draw_mega_bar(screen, font, mega_text, charge_blocks=0, active=False):
    if not mega_text:
        return
    width, _ = screen.get_size()
    block_size = 22
    gap = 4
    bar_width = MEGA_CHARGE_MAX_BLOCKS * block_size + (MEGA_CHARGE_MAX_BLOCKS - 1) * gap
    bar_height = block_size
    bar_rect = pygame.Rect(0, 0, bar_width, bar_height)
    bar_rect.center = (width / 2, 51)

    bg_color = (35, 39, 48)
    fill_color = MEGA_SHOT_COLOR if active else (92, 98, 110)
    frame_color = (105, 116, 135) if active else (55, 60, 70)

    pygame.draw.rect(screen, frame_color, bar_rect, 2)
    for index in range(MEGA_CHARGE_MAX_BLOCKS):
        block_rect = pygame.Rect(
            bar_rect.x + index * (block_size + gap),
            bar_rect.y,
            block_size,
            block_size,
        )
        pygame.draw.rect(screen, bg_color, block_rect)
        if index < charge_blocks:
            pygame.draw.rect(screen, fill_color, block_rect.inflate(-4, -4))
        pygame.draw.rect(screen, frame_color, block_rect, 1)

    text_color = MEGA_SHOT_COLOR if active else (92, 98, 110)
    text_surface = font.render(mega_text, True, text_color)
    if not active:
        text_surface.set_alpha(150)
    screen.blit(text_surface, text_surface.get_rect(center=(width / 2, 28)))


def draw_player_shield_bar(screen, font, charges, enabled):
    if not enabled:
        return
    width, _ = screen.get_size()
    block_size = 22
    gap = 5
    bar_width = PLAYER_SHIELD_MAX_CHARGES * block_size + (PLAYER_SHIELD_MAX_CHARGES - 1) * gap
    bar_rect = pygame.Rect(0, 0, bar_width, block_size)
    bar_rect.center = (width / 2, 91)

    frame_color = (70, 154, 190)
    empty_color = (22, 34, 48)
    for index in range(PLAYER_SHIELD_MAX_CHARGES):
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
    screen.blit(text_surface, text_surface.get_rect(center=(width / 2, 70)))


def draw_hud(screen, font, destroyed, drone_target, score, lives):
    width, _ = screen.get_size()
    left = f"Drones destroyed: {destroyed}/{drone_target}"
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


def draw_end_screen(screen, clock, won, destroyed, drone_target, score):
    title_font = pygame.font.SysFont("arial", 56, bold=True)
    body_font = pygame.font.SysFont("arial", 26)
    title = "MISSION COMPLETE" if won else "MISSION FAILED"
    message = f"Drones destroyed: {min(destroyed, drone_target)}/{drone_target}    Score: {score}"
    prompt = "Press ␣ to return to the menu"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
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
        title_surface = title_font.render(title, True, ACCENT if won else THREE_SHOT_DRONE_COLOR)
        screen.blit(title_surface, title_surface.get_rect(center=(width / 2, height / 2 - 84)))
        message_surface = body_font.render(message, True, TEXT_COLOR)
        screen.blit(message_surface, message_surface.get_rect(center=(width / 2, height / 2 - 12)))
        render_inline_center(screen, prompt, body_font, MUTED_TEXT, (width / 2, height / 2 + 61))
        pygame.display.flip()
        clock.tick(60)


def draw_button(surface, rect, text, font, selected=False):
    fill = (27, 42, 74) if selected else (14, 24, 45)
    border = ACCENT if selected else (65, 82, 120)
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, 2, border_radius=8)
    label = font.render(text, True, TEXT_COLOR)
    surface.blit(label, label.get_rect(center=rect.center))


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


def run_mission(screen, clock, base_dir, lesson_dir_name, valid_keys):
    lesson_dir = Path(base_dir) / "lessons" / lesson_dir_name
    sfx_dir = Path(base_dir) / "sfx"
    gfx_dir = Path(base_dir) / "gfx"
    lesson_number = int(lesson_dir_name.split("_")[-1])
    target_keys = mission_target_keys(valid_keys, lesson_number)
    drone_target = lesson_drone_target(lesson_number)
    mini_boss_numbers = mini_boss_numbers_for_lesson(lesson_number, drone_target)
    play_audio(lesson_dir / f"lesson_{lesson_number}_instructions.wav")
    laser_sound = load_sound(sfx_dir / "laser.ogg", 0.55)
    explosion_sound = load_sound(sfx_dir / "explosion.ogg", 0.75)
    health_sound = load_sound(sfx_dir / "health.ogg", 0.85)
    split_sound = load_sound(sfx_dir / "split.ogg", 0.75)
    boss_sound = load_sound(sfx_dir / "boss.ogg", 0.85)
    victory_sound = load_sound(sfx_dir / "victory.wav", 0.9)
    bg_music = load_sound(sfx_dir / "bg_music.wav", BG_MUSIC_VOLUME)
    bg_music_channel = play_looping_sound(bg_music, BG_MUSIC_FADE_IN_MS)
    turret_image = load_image(gfx_dir / "turret.png")
    if turret_image is not None:
        turret_image = pygame.transform.smoothscale(turret_image, (72, 72))
    pod_image = load_image(gfx_dir / "pod.png")
    if pod_image is not None:
        pod_image = pygame.transform.smoothscale(pod_image, (108, 108))

    font = pygame.font.SysFont("arial", 24, bold=True)
    drones = []
    bullets = []
    mega_shots = []
    pending_shots = []
    power_up = None
    final_boss = None
    particles = []
    stars = create_star_field()
    destroyed = 0
    spawned_count = 0
    score = 0
    lives = STARTING_LIVES
    shield_charges = PLAYER_SHIELD_MAX_CHARGES if player_shield_enabled(lesson_number) else 0
    turret_angle = -math.pi / 2
    pod_rotation = 0
    space_held = False
    mega_charge_blocks = MEGA_CHARGE_MAX_BLOCKS
    next_mega_recharge_time = 0
    next_shield_recharge_time = 0
    current_spawn_interval_ms = random_spawn_interval()
    next_spawn_rate_change_time = pygame.time.get_ticks() + SPAWN_RATE_CHANGE_MS
    next_spawn_time = pygame.time.get_ticks()
    next_power_up_spawn_time = next_power_up_time(next_spawn_time)

    while True:
        dt = clock.tick(60) / 1000
        now = pygame.time.get_ticks()
        pod_rotation = (pod_rotation + math.tau * dt / POD_ROTATION_SECONDS) % math.tau
        if now >= next_spawn_rate_change_time:
            current_spawn_interval_ms = random_spawn_interval()
            next_spawn_rate_change_time = now + SPAWN_RATE_CHANGE_MS
        update_star_field(stars, dt)
        if mega_shot_enabled(lesson_number) and mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS:
            if next_mega_recharge_time and now >= next_mega_recharge_time:
                mega_charge_blocks += 1
                next_mega_recharge_time = (
                    now + MEGA_RECHARGE_INTERVAL_MS
                    if mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS
                    else 0
                )
        if (
            player_shield_enabled(lesson_number)
            and shield_charges < PLAYER_SHIELD_MAX_CHARGES
            and now >= next_shield_recharge_time
        ):
            shield_charges += 1
            next_shield_recharge_time = (
                now + PLAYER_SHIELD_RECHARGE_MS
                if shield_charges < PLAYER_SHIELD_MAX_CHARGES
                else 0
            )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_looping_sound(bg_music_channel)
                stop_audio()
                return "quit"
            if event.type == pygame.KEYDOWN:
                started_space_charge = False
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                if event.key == pygame.K_ESCAPE:
                    if bg_music_channel is not None:
                        bg_music_channel.pause()
                    if pygame.mixer.get_init():
                        pygame.mixer.music.pause()
                    pause_result = pause_menu(screen, clock)
                    if pause_result == "resume":
                        if bg_music_channel is not None:
                            bg_music_channel.unpause()
                        if pygame.mixer.get_init():
                            pygame.mixer.music.unpause()
                        pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN))
                        continue
                    stop_looping_sound(bg_music_channel, BG_MUSIC_FADE_OUT_MS)
                    stop_audio()
                    if pause_result == "quit":
                        return "quit"
                    if pause_result == "restart":
                        return "restart"
                    return "menu"
                pressed_key = event_to_lesson_key(event)
                if mega_shot_enabled(lesson_number) and event.key == pygame.K_SPACE:
                    space_held = True
                    started_space_charge = True
                collected_power_up, consumed_by_power_up = handle_power_up_key(power_up, pressed_key)
                if collected_power_up:
                    lives += 1
                    play_sound(health_sound)
                    power_up = None
                    next_power_up_spawn_time = next_power_up_time(now)
                if consumed_by_power_up:
                    continue
                if pressed_key in target_keys:
                    if (
                        mega_shot_enabled(lesson_number)
                        and space_held
                        and not started_space_charge
                        and mega_charge_blocks > 0
                    ):
                        queued_mega = queue_mega_shot(
                            drones,
                            final_boss,
                            pending_shots,
                            pressed_key,
                            screen_center(screen),
                            mega_charge_blocks,
                            now,
                        )
                        if queued_mega:
                            mega_charge_blocks = 0
                            next_mega_recharge_time = now + MEGA_RECHARGE_DELAY_MS
                            continue
                    queue_shot_at(drones, pending_shots, pressed_key, screen_center(screen), now)
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    space_held = False

        while pending_shots and not target_is_available(pending_shots[0].target, drones, final_boss):
            release_pending_shot(pending_shots.pop(0))
        if pending_shots:
            center = screen_center(screen)
            next_shot = pending_shots[0]
            aim_angle = target_angle(next_shot.target, center)
            turret_angle = rotate_toward_angle(turret_angle, aim_angle, TURRET_TURN_SPEED * dt)
            if (
                now - next_shot.created_at >= TURRET_FIRE_DELAY_MS
                and abs(angle_delta(turret_angle, aim_angle)) <= TURRET_FIRE_ANGLE_THRESHOLD
            ):
                turret_angle = fire_pending_shot(next_shot, bullets, mega_shots, center)
                pending_shots.pop(0)
                play_sound(laser_sound)

        if final_boss is None and spawned_count < drone_target and now >= next_spawn_time:
            drone, spawned_count = spawn_next_drone(
                drones,
                screen,
                destroyed,
                target_keys,
                spawned_count,
                mini_boss_numbers,
            )
            if drone.is_mega:
                play_sound(boss_sound)
            next_spawn_time = now + current_spawn_interval_ms

        if power_up is not None and now >= power_up.expires_at:
            power_up = None
            next_power_up_spawn_time = next_power_up_time(now)
        if power_up is None and now >= next_power_up_spawn_time:
            power_up = spawn_power_up(screen, target_keys, now)

        if (
            final_boss_enabled(lesson_number)
            and final_boss is None
            and spawned_count >= drone_target
            and active_mini_boss_count(drones) == 0
        ):
            final_boss = spawn_final_boss(screen, now, target_keys)
            play_sound(boss_sound)

        if (
            not final_boss_enabled(lesson_number)
            and (lesson_number <= 2 or spawned_count >= drone_target)
            and destroyed >= drone_target
            and active_mini_boss_count(drones) == 0
        ):
            stop_looping_sound(bg_music_channel, BG_MUSIC_FADE_OUT_MS)
            stop_audio()
            play_sound(victory_sound)
            return draw_end_screen(screen, clock, True, destroyed, drone_target, score)

        if final_boss is not None:
            update_final_boss_movement(final_boss, screen, dt, now)
            final_boss.rotation = (final_boss.rotation + math.tau * dt / MEGA_ROTATION_SECONDS) % math.tau
            update_final_boss_shield(final_boss, now)
            if final_boss.is_orbiting and now >= final_boss.next_shot_time:
                fire_final_boss_drones(
                    drones,
                    final_boss,
                    screen_center(screen),
                    target_keys,
                    final_boss_projectile_count(lesson_number),
                )
                final_boss.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS

        for drone in drones[:]:
            center = screen_center(screen)
            update_drone_position(drone, center, dt)
            if drone.is_mega:
                drone.rotation = (drone.rotation + math.tau * dt / MEGA_ROTATION_SECONDS) % math.tau
            if drone.is_mega and now >= drone.next_shot_time:
                fire_mega_drone(drones, drone, center, target_keys)
                drone.next_shot_time = now + MEGA_ATTACK_INTERVAL_MS
            if drone.pos.distance_to(center) <= drone.radius + 23:
                drones.remove(drone)
                explode(particles, drone.pos, 12)
                play_sound(explosion_sound)
                if shield_charges > 0:
                    shield_charges -= 1
                    if not next_shield_recharge_time:
                        next_shield_recharge_time = now + PLAYER_SHIELD_RECHARGE_MS
                    continue
                lives -= 1
                if lives <= 0:
                    stop_looping_sound(bg_music_channel, BG_MUSIC_FADE_OUT_MS)
                    stop_audio()
                    explode(particles, center, 36)
                    return draw_end_screen(screen, clock, False, destroyed, drone_target, score)

        for bullet in bullets[:]:
            if bullet.target not in drones:
                bullet.target = None
                bullet.pos += bullet.vel * dt
                if bullet_is_offscreen(bullet, screen):
                    bullets.remove(bullet)
                continue

            if bullet.target is None:
                bullet.pos += bullet.vel * dt
                if bullet_is_offscreen(bullet, screen):
                    bullets.remove(bullet)
                continue

            target_vector = bullet.target.pos - bullet.pos
            if target_vector.length_squared() <= (bullet.target.radius + 7) ** 2:
                bullet.target.incoming_damage = max(0, bullet.target.incoming_damage - 1)
                bullet.target.hp -= 1
                bullets.remove(bullet)
                if bullet.target.hp > 0 and not bullet.target.is_mega and bullet.target in drones:
                    hit_drone = bullet.target
                    drones.remove(hit_drone)
                    split_regular_drone(drones, hit_drone)
                    play_sound(split_sound)
                    continue
                if bullet.target.hp <= 0 and bullet.target in drones:
                    pos = bullet.target.pos.copy()
                    drones.remove(bullet.target)
                    destroyed += 1
                    score += 100
                    explode(particles, pos)
                    play_sound(explosion_sound)
                continue

            if target_vector.length_squared() > 0:
                bullet.vel = target_vector.normalize() * 650
            bullet.pos += bullet.vel * dt

        for mega_shot in mega_shots[:]:
            if isinstance(mega_shot.target, Drone) and mega_shot.target not in drones:
                mega_shot.target = None

            if mega_shot.target is None:
                mega_shot.pos += mega_shot.vel * dt
                if bullet_is_offscreen(mega_shot, screen):
                    mega_shots.remove(mega_shot)
                continue

            target_vector = mega_shot.target.pos - mega_shot.pos
            target_radius = getattr(mega_shot.target, "radius", 26)
            if target_vector.length_squared() <= (target_radius + mega_shot.radius) ** 2:
                target = mega_shot.target
                mega_shots.remove(mega_shot)
                if isinstance(target, FinalBoss):
                    if target.shield > 0:
                        if mega_shot.charge_level >= MEGA_SHIELD_MIN_LEVEL:
                            target.shield -= 1
                            target.shield_down_since = now if target.shield == 0 else None
                            target.next_shield_recharge_time = None
                            explode(particles, target.pos, 12)
                            play_sound(explosion_sound)
                    elif mega_shot.charge_level >= MEGA_FINAL_KILL_LEVEL:
                        explode(particles, target.pos, 42)
                        play_sound(explosion_sound)
                        stop_looping_sound(bg_music_channel, BG_MUSIC_FADE_OUT_MS)
                        stop_audio()
                        play_sound(victory_sound)
                        return draw_end_screen(screen, clock, True, destroyed, drone_target, score)
                    else:
                        target.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS
                    continue

                if isinstance(target, Drone) and target in drones:
                    damage = mega_damage(mega_shot.charge_level)
                    target.incoming_damage = max(0, target.incoming_damage - damage)
                    target.hp -= damage
                    if target.hp > 0 and not target.is_mega:
                        drones.remove(target)
                        split_regular_drone(drones, target)
                        play_sound(split_sound)
                    elif target.hp <= 0:
                        pos = target.pos.copy()
                        drones.remove(target)
                        destroyed += 1
                        score += 100
                        explode(particles, pos)
                        play_sound(explosion_sound)
                    continue

            if target_vector.length_squared() > 0:
                mega_shot.vel = target_vector.normalize() * 820
            mega_shot.pos += mega_shot.vel * dt

        for particle in particles[:]:
            particle.ttl -= dt
            if particle.ttl <= 0:
                particles.remove(particle)
                continue
            particle.pos += particle.vel * dt
            particle.vel *= 0.98

        screen = pygame.display.get_surface()
        screen.fill(BG_COLOR)
        width, height = screen.get_size()
        draw_star_field(screen, stars)

        for particle in particles:
            alpha_scale = max(0, min(1, particle.ttl))
            radius = max(2, int(5 * alpha_scale))
            pygame.draw.circle(screen, EXPLOSION_COLOR, particle.pos, radius)

        for bullet in bullets:
            pygame.draw.circle(screen, BULLET_COLOR, bullet.pos, 5)

        for mega_shot in mega_shots:
            pygame.draw.circle(screen, MEGA_SHOT_COLOR, mega_shot.pos, mega_shot.radius)
            pygame.draw.circle(screen, (255, 255, 255), mega_shot.pos, mega_shot.radius, 2)

        draw_power_up(screen, power_up)
        draw_final_boss(screen, final_boss)

        for drone in drones:
            color = drone_color(drone)
            if drone.is_mega:
                points = pentagon_points(drone.pos, drone.radius, drone.rotation - math.pi / 2)
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (245, 222, 255), points, 2)
            else:
                pygame.draw.circle(screen, color, drone.pos, drone.radius)
                pygame.draw.circle(screen, (255, 231, 214), drone.pos, drone.radius, 2)
            label_size = 24 if drone.is_boss_shot else 18 if len(drone.letter) > 2 else 28
            label_font = pygame.font.SysFont("arial", label_size, bold=True)
            render_key_label(screen, drone.letter, label_font, (8, 10, 18), drone.pos, drone.radius * 1.45)

        draw_ship(screen, turret_angle, pod_rotation, turret_image, pod_image)
        mega_text = ""
        mega_active = False
        if mega_shot_enabled(lesson_number):
            mega_text = "Mega shot"
            mega_active = mega_charge_blocks > 0
        draw_mega_bar(screen, font, mega_text, mega_charge_blocks, mega_active)
        draw_player_shield_bar(screen, font, shield_charges, player_shield_enabled(lesson_number))
        draw_hud(screen, font, min(destroyed, drone_target), drone_target, score, lives)

        key_hint = ", ".join(display_key(key) for key in target_keys)
        hint = f"Press {key_hint} to fire. F11 toggles max size. Esc returns to menu."
        render_inline_text(screen, hint, pygame.font.SysFont("arial", 18), MUTED_TEXT, (22, height - 34))

        pygame.display.flip()


def run(screen, clock, base_dir):
    return run_mission(screen, clock, base_dir, LESSON_DIR_NAME, VALID_KEYS)
