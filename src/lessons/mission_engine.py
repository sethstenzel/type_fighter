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
SHOT_TRAIL_COLOR = (92, 190, 255)
SHIP_COLOR = (112, 170, 255)
EXPLOSION_COLOR = (255, 218, 125)
POD_ROTATION_SECONDS = 15
POD_IMAGE_SIZE = 163
PLAYER_COLLISION_RADIUS = 29
TURRET_IMAGE_SIZE = 86
DRONE_PIXELS_PER_ROTATION = 60
TURRET_TURN_SPEED = 13
TURRET_FIRE_ANGLE_THRESHOLD = 0.08
TURRET_FIRE_DELAY_MS = 90
SHOT_IMAGE_SIZE = 22
SHOT_TRAIL_INTERVAL_MS = 18

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
FINAL_BOSS_ATTACK_INTERVAL_MS = 8000
FINAL_BOSS_APPROACH_SPEED = 90
FINAL_BOSS_ORBIT_SECONDS = 10
FINAL_BOSS_ORBIT_DISTANCE_SCALE = 1.44
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
POWER_UP_WARNING_MS = 3000
POWER_UP_MIN_INTERVAL_MS = 18000
POWER_UP_MAX_INTERVAL_MS = 32000
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


def final_boss_enabled(lesson_number):
    return lesson_number >= 5


def mission_target_keys(valid_keys, lesson_number):
    return tuple(
        key
        for key in valid_keys
        if not (mega_shot_enabled(lesson_number) and key == "space")
    )


def player_shield_enabled(lesson_number):
    return lesson_number >= 7


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


def drone_rotation_radians_per_second(drone):
    pixels_per_rotation = MEGA_PIXELS_PER_ROTATION if drone.is_mega else DRONE_PIXELS_PER_ROTATION
    return math.tau * max(0, drone.speed) / pixels_per_rotation


def drone_counts_for_level(drone):
    return drone.level_value > 0


def active_level_value(drones):
    return sum(drone.level_value for drone in drones if drone_counts_for_level(drone))


def should_spawn_mission_drone(lesson_number, spawned_count, destroyed, drones, drone_target):
    if final_boss_enabled(lesson_number):
        return spawned_count < drone_target
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
        radius=MEGA_DRONE_RADIUS if is_mega else drone_radius_for_hp(hp),
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
            level_value=drone.level_value / 2,
        )
        drones.append(child)


def next_power_up_time(now):
    return now + random.randint(POWER_UP_MIN_INTERVAL_MS, POWER_UP_MAX_INTERVAL_MS)


def spawn_power_up(screen, valid_keys, now, shield_enabled=False, shield_charges=0):
    width, height = screen.get_size()
    margin = 90
    power_up_keys = [key for key in valid_keys if len(key) == 1 and key.isalpha()] or list(valid_keys)
    keys = random.choices(power_up_keys, k=2)
    can_spawn_shield = shield_enabled and shield_charges < PLAYER_SHIELD_MAX_CHARGES
    kind = "shield" if can_spawn_shield and random.random() < 0.5 else "life"
    return PowerUp(
        pos=pygame.Vector2(
            random.randint(margin, max(margin, width - margin)),
            random.randint(margin, max(margin, height - margin)),
        ),
        letters=(keys[0], keys[1]),
        expires_at=now + POWER_UP_DURATION_MS,
        kind=kind,
    )


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
            pos=boss.pos + direction * (boss.radius + BOSS_SHOT_IMAGE_RADIUS + 4),
            letter=random.choice(valid_keys),
            hp=1,
            max_hp=1,
            radius=BOSS_SHOT_IMAGE_RADIUS,
            speed=BOSS_SHOT_SPEED,
            is_boss_shot=True,
            level_value=0,
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
                pos=final_boss.pos + shot_direction * (final_boss.radius + BOSS_SHOT_IMAGE_RADIUS + 6),
                letter=random.choice(valid_keys),
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


def add_shot_trail(shot_trails, bullet, now):
    if now < bullet.next_trail_time or bullet.vel.length_squared() == 0:
        return

    direction = bullet.vel.normalize()
    origin = bullet.pos - direction * 7
    side = pygame.Vector2(-direction.y, direction.x)
    for _ in range(2):
        drift = -direction * random.uniform(10, 24) + side * random.uniform(-12, 12)
        ttl = random.uniform(0.18, 0.32)
        shot_trails.append(
            ShotTrailParticle(
                pos=origin + side * random.uniform(-3, 3),
                vel=drift,
                ttl=ttl,
                max_ttl=ttl,
                radius=random.uniform(1.0, 2.0),
            )
        )
    bullet.next_trail_time = now + SHOT_TRAIL_INTERVAL_MS


def draw_shot_trails(screen, shot_trails):
    for particle in shot_trails:
        alpha_scale = max(0, min(1, particle.ttl / particle.max_ttl))
        radius = max(1, int(particle.radius * alpha_scale))
        size = radius * 2 + 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        alpha = int(58 * alpha_scale)
        pygame.draw.circle(surface, (*SHOT_TRAIL_COLOR, alpha), (size // 2, size // 2), radius)
        screen.blit(surface, surface.get_rect(center=particle.pos))


def draw_bullet(screen, bullet, shot_image=None):
    if shot_image is not None:
        image = shot_image
        if bullet.vel.length_squared() > 0:
            angle = math.degrees(math.atan2(-bullet.vel.y, bullet.vel.x))
            image = pygame.transform.rotozoom(shot_image, angle, 1.0)
        screen.blit(image, image.get_rect(center=bullet.pos))
    else:
        pygame.draw.circle(screen, BULLET_COLOR, bullet.pos, 5)


def draw_ship(screen, turret_angle, pod_rotation, turret_image=None, pod_image=None):
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
    note_font = pygame.font.SysFont("arial", 15, bold=True)
    note_surface = note_font.render("Hold Space Bar When Firing", True, text_color)
    if not active:
        note_surface.set_alpha(150)
    screen.blit(note_surface, note_surface.get_rect(center=(width / 2, 76)))


def draw_player_shield_bar(screen, font, charges, enabled, y_offset=0):
    if not enabled:
        return
    width, _ = screen.get_size()
    block_size = 22
    gap = 5
    bar_width = PLAYER_SHIELD_MAX_CHARGES * block_size + (PLAYER_SHIELD_MAX_CHARGES - 1) * gap
    bar_rect = pygame.Rect(0, 0, bar_width, block_size)
    bar_rect.center = (width / 2, 91 + y_offset)

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
    screen.blit(text_surface, text_surface.get_rect(center=(width / 2, 70 + y_offset)))


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


def draw_end_screen(screen, clock, won, destroyed, drone_target, score):
    title_font = pygame.font.SysFont("arial", 56, bold=True)
    body_font = pygame.font.SysFont("arial", 26)
    title = "MISSION COMPLETE" if won else "MISSION FAILED"
    message = f"Drones destroyed: {int(min(destroyed, drone_target))}/{drone_target}    Score: {score}"
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
        self.lesson_number = int(lesson_dir_name.split("_")[-1])
        self.target_keys = mission_target_keys(valid_keys, self.lesson_number)
        self.drone_target = lesson_drone_target(self.lesson_number)
        self.mini_boss_numbers = mini_boss_numbers_for_lesson(self.lesson_number, self.drone_target)
        play_audio(self.lesson_dir / f"lesson_{self.lesson_number}_instructions.wav")
        self.laser_sound = load_sound(self.sfx_dir / "laser.ogg", 0.55)
        self.explosion_sound = load_sound(self.sfx_dir / "explosion.ogg", 0.75)
        self.health_sound = load_sound(self.sfx_dir / "health.ogg", 0.85)
        self.split_sound = load_sound(self.sfx_dir / "split.ogg", 0.75)
        self.boss_sound = load_sound(self.sfx_dir / "boss.ogg", 0.85)
        self.victory_sound = load_sound(self.sfx_dir / "victory.wav", 0.9)
        self.bg_music = load_sound(self.sfx_dir / "bg_music.wav", BG_MUSIC_VOLUME)
        self.bg_music_channel = play_looping_sound(self.bg_music, BG_MUSIC_FADE_IN_MS)
        self.turret_image = load_image(self.gfx_dir / "turret.png")
        if self.turret_image is not None:
            self.turret_image = pygame.transform.smoothscale(self.turret_image, (TURRET_IMAGE_SIZE, TURRET_IMAGE_SIZE))
        self.pod_image = load_image(self.gfx_dir / "pod.png")
        if self.pod_image is not None:
            self.pod_image = pygame.transform.smoothscale(self.pod_image, (POD_IMAGE_SIZE, POD_IMAGE_SIZE))
        self.shot_image = load_image(self.gfx_dir / "shot.png")
        if self.shot_image is not None:
            self.shot_image = pygame.transform.smoothscale(self.shot_image, (SHOT_IMAGE_SIZE, SHOT_IMAGE_SIZE))
        self.final_boss_image = load_image(self.gfx_dir / "final-boss.png")
        if self.final_boss_image is not None:
            self.final_boss_image = pygame.transform.smoothscale(
                self.final_boss_image,
                (FINAL_BOSS_IMAGE_SIZE, FINAL_BOSS_IMAGE_SIZE),
            )
        self.drone_images = {
            "yellow": load_image(self.gfx_dir / "yellow_drone.png"),
            "orange": load_image(self.gfx_dir / "orange_drone.png"),
            "red": load_image(self.gfx_dir / "red_drone.png"),
            "semi_boss": load_image(self.gfx_dir / "semi-boss.png"),
        }
        self.drone_image_cache = {}

        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.drones = []
        self.bullets = []
        self.mega_shots = []
        self.pending_shots = []
        self.shot_trails = []
        self.power_up = None
        self.final_boss = None
        self.particles = []
        self.stars = create_star_field()
        self.destroyed = 0
        self.spawned_count = 0
        self.score = 0
        self.lives = max(STARTING_LIVES, self._player_int("lives", STARTING_LIVES, 1))
        self.shield_charges = self._player_int("shield_charges", 0, 0, PLAYER_SHIELD_MAX_CHARGES)
        self._save_player_resources()
        self.turret_angle = -math.pi / 2
        self.pod_rotation = 0
        self.space_held = False
        self.mega_charge_blocks = MEGA_CHARGE_MAX_BLOCKS
        self.next_mega_recharge_time = 0
        self.current_spawn_interval_ms = random_spawn_interval(self.lesson_number)
        self.next_spawn_rate_change_time = pygame.time.get_ticks() + SPAWN_RATE_CHANGE_MS
        self.next_spawn_time = pygame.time.get_ticks()
        self.next_power_up_spawn_time = next_power_up_time(self.next_spawn_time)

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
        self.player["lives"] = max(1, self.lives)
        self.player["shield_charges"] = max(0, min(PLAYER_SHIELD_MAX_CHARGES, self.shield_charges))

    def _finish(self, result):
        self._save_player_resources()
        return result

    def _show_end_screen(self, won):
        self._save_player_resources()
        return draw_end_screen(self.screen, self.clock, won, self.destroyed, self.drone_target, self.score)

    def _begin_frame(self):
        dt = self.clock.tick(60) / 1000
        now = pygame.time.get_ticks()
        self.pod_rotation = (self.pod_rotation + math.tau * dt / POD_ROTATION_SECONDS) % math.tau
        if now >= self.next_spawn_rate_change_time:
            self.current_spawn_interval_ms = random_spawn_interval(self.lesson_number)
            self.next_spawn_rate_change_time = now + SPAWN_RATE_CHANGE_MS
        update_star_field(self.stars, dt)
        if mega_shot_enabled(self.lesson_number) and self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS:
            if self.next_mega_recharge_time and now >= self.next_mega_recharge_time:
                self.mega_charge_blocks += 1
                self.next_mega_recharge_time = (
                    now + MEGA_RECHARGE_INTERVAL_MS
                    if self.mega_charge_blocks < MEGA_CHARGE_MAX_BLOCKS
                    else 0
                )
        return dt, now

    def _spawn_entities(self, now):
        if (
            self.final_boss is None
            and should_spawn_mission_drone(
                self.lesson_number,
                self.spawned_count,
                self.destroyed,
                self.drones,
                self.drone_target,
            )
            and now >= self.next_spawn_time
        ):
            drone, self.spawned_count = spawn_next_drone(
                self.drones,
                self.screen,
                self.destroyed,
                self.target_keys,
                self.spawned_count,
                self.mini_boss_numbers,
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
            )

        if (
            final_boss_enabled(self.lesson_number)
            and self.final_boss is None
            and self.spawned_count >= self.drone_target
            and active_mini_boss_count(self.drones) == 0
        ):
            self.final_boss = spawn_final_boss(self.screen, now, self.target_keys)
            play_sound(self.boss_sound)

    def _draw_frame(self, now):
        self.screen = pygame.display.get_surface()
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
            pygame.draw.circle(self.screen, MEGA_SHOT_COLOR, mega_shot.pos, mega_shot.radius)
            pygame.draw.circle(self.screen, (255, 255, 255), mega_shot.pos, mega_shot.radius, 2)

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

        draw_ship(self.screen, self.turret_angle, self.pod_rotation, self.turret_image, self.pod_image)
        mega_text = ""
        mega_active = False
        if mega_shot_enabled(self.lesson_number):
            mega_text = "Mega shot"
            mega_active = self.mega_charge_blocks > 0
        draw_mega_bar(self.screen, self.font, mega_text, self.mega_charge_blocks, mega_active)
        shield_offset = 32 if mega_shot_enabled(self.lesson_number) else 0
        draw_player_shield_bar(
            self.screen,
            self.font,
            self.shield_charges,
            player_shield_enabled(self.lesson_number),
            shield_offset,
        )
        draw_hud(self.screen, self.font, min(self.destroyed, self.drone_target), self.drone_target, self.score, self.lives)

        key_hint = ", ".join(display_key(key) for key in self.target_keys)
        hint = f"Press {key_hint} to fire. F11 toggles max size. Esc returns to menu."
        render_inline_text(self.screen, hint, pygame.font.SysFont("arial", 18), MUTED_TEXT, (22, height - 34))

        pygame.display.flip()

    def _process_pending_shots(self, now, dt):
        while self.pending_shots and not target_is_available(self.pending_shots[0].target, self.drones, self.final_boss):
            release_pending_shot(self.pending_shots.pop(0))
        if self.pending_shots:
            center = screen_center(self.screen)
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
        if self.final_boss.is_orbiting and now >= self.final_boss.next_shot_time:
            fire_final_boss_drones(
                self.drones,
                self.final_boss,
                screen_center(self.screen),
                self.target_keys,
                final_boss_projectile_count(self.lesson_number),
            )
            self.final_boss.next_shot_time = now + FINAL_BOSS_ATTACK_INTERVAL_MS

    def _update_drones(self, now, dt):
        for drone in self.drones[:]:
            center = screen_center(self.screen)
            update_drone_position(drone, center, dt)
            drone.rotation = (drone.rotation + drone_rotation_radians_per_second(drone) * dt) % math.tau
            if drone.is_mega and now >= drone.next_shot_time:
                fire_mega_drone(self.drones, drone, center, self.target_keys)
                drone.next_shot_time = now + MEGA_ATTACK_INTERVAL_MS
            if drone.pos.distance_to(center) <= drone.radius + PLAYER_COLLISION_RADIUS:
                self.drones.remove(drone)
                explode(self.particles, drone.pos, 12)
                play_sound(self.explosion_sound)
                if player_shield_enabled(self.lesson_number) and self.shield_charges > 0:
                    self.shield_charges -= 1
                    self._save_player_resources()
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

    def run(self):
        while True:
            dt, now = self._begin_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stop_looping_sound(self.bg_music_channel)
                    stop_audio()
                    return self._finish("quit")
                if event.type == pygame.KEYDOWN:
                    started_space_charge = False
                    if event.key == pygame.K_F11:
                        self.screen = toggle_fullscreen()
                    if event.key == pygame.K_ESCAPE:
                        if self.bg_music_channel is not None:
                            self.bg_music_channel.pause()
                        if pygame.mixer.get_init():
                            pygame.mixer.music.pause()
                        pause_result = pause_menu(self.screen, self.clock)
                        if pause_result == "resume":
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
                    if mega_shot_enabled(self.lesson_number) and event.key == pygame.K_SPACE:
                        self.space_held = True
                        started_space_charge = True
                    collected_power_up, consumed_by_power_up = handle_power_up_key(self.power_up, pressed_key)
                    if collected_power_up:
                        if collected_power_up == "shield":
                            self.shield_charges = min(PLAYER_SHIELD_MAX_CHARGES, self.shield_charges + 1)
                        else:
                            self.lives += 1
                        self._save_player_resources()
                        play_sound(self.health_sound)
                        self.power_up = None
                        self.next_power_up_spawn_time = next_power_up_time(now)
                    if consumed_by_power_up:
                        continue
                    if pressed_key in self.target_keys:
                        if (
                            mega_shot_enabled(self.lesson_number)
                            and self.space_held
                            and not started_space_charge
                            and self.mega_charge_blocks > 0
                        ):
                            queued_mega = queue_mega_shot(
                                self.drones,
                                self.final_boss,
                                self.pending_shots,
                                pressed_key,
                                screen_center(self.screen),
                                self.mega_charge_blocks,
                                now,
                            )
                            if queued_mega:
                                self.mega_charge_blocks = 0
                                self.next_mega_recharge_time = now + MEGA_RECHARGE_DELAY_MS
                                continue
                        queue_shot_at(self.drones, self.pending_shots, pressed_key, screen_center(self.screen), now)
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
            result = self._update_drones(now, dt)
            if result is not None:
                return result

            for bullet in self.bullets[:]:
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
                if isinstance(mega_shot.target, Drone) and mega_shot.target not in self.drones:
                    mega_shot.target = None

                if mega_shot.target is None:
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
                    mega_shot.vel = target_vector.normalize() * 820
                mega_shot.pos += mega_shot.vel * dt

            self._update_particles(dt)
            self._update_shot_trails(dt)

            self._draw_frame(now)


def run_mission(screen, clock, base_dir, lesson_dir_name, valid_keys, player=None):
    return MissionEngine(screen, clock, base_dir, lesson_dir_name, valid_keys, player).run()
