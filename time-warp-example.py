import math
import random

import numpy as np
import pygame


class TimeBubble:
    def __init__(self, duration=6.0, min_speed_scale=0.05, release_time=1.5):
        self.duration = duration
        self.min_speed_scale = min_speed_scale
        self.release_time = release_time
        self.timer = duration
        self.active = True

    def update(self, dt):
        if not self.active:
            return

        self.timer -= dt

        if self.timer <= 0:
            self.timer = 0
            self.active = False

    def get_time_scale(self):
        """
        Returns how fast gameplay objects should move.

        1.0  = normal speed
        0.05 = almost frozen
        """

        if not self.active:
            return 1.0

        # Most of the bubble duration is nearly frozen.
        if self.timer > self.release_time:
            return self.min_speed_scale

        # During the final release_time seconds, ease back to normal speed.
        release_progress = 1.0 - (self.timer / self.release_time)

        # Smooth easing.
        eased = release_progress * release_progress * (3 - 2 * release_progress)

        return self.min_speed_scale + (1.0 - self.min_speed_scale) * eased


class SpaceTimeRipple:
    def __init__(
        self,
        size,
        center,
        speed=90,
        strength=24,
        wavelength=95,
        thickness=210,
        start_radius=55,
    ):
        self.w, self.h = size
        self.cx, self.cy = center

        self.radius = start_radius
        self.speed = speed
        self.strength = strength
        self.wavelength = wavelength
        self.thickness = thickness

        self.max_radius = math.hypot(self.w, self.h)
        self.alive = True

        # Pygame surfarray uses [x, y].
        self.x = np.arange(self.w, dtype=np.float32)[:, None]
        self.y = np.arange(self.h, dtype=np.float32)[None, :]

    def update(self, dt):
        self.radius += self.speed * dt

        if self.radius > self.max_radius + self.thickness * 2:
            self.alive = False

    def apply(self, source_surface):
        src = pygame.surfarray.array3d(source_surface)

        dx = self.x - self.cx
        dy = self.y - self.cy

        dist = np.sqrt(dx * dx + dy * dy)
        safe_dist = np.maximum(dist, 1)

        ring_distance = dist - self.radius

        envelope = np.exp(
            -(ring_distance * ring_distance)
            / (2 * self.thickness * self.thickness)
        )

        # One broad, calm wave.
        wave = np.sin(ring_distance / self.wavelength * math.tau)

        # Slow fade so it remains visible.
        fade = max(0.4, 1.0 - (self.radius / self.max_radius) * 0.25)

        offset = wave * envelope * self.strength * fade

        # Prevent center droplet bulge.
        center_suppression = np.clip(dist / 90, 0, 1)
        offset *= center_suppression

        sample_x = self.x + (dx / safe_dist) * offset
        sample_y = self.y + (dy / safe_dist) * offset

        sample_x = np.clip(sample_x, 0, self.w - 1).astype(np.int32)
        sample_y = np.clip(sample_y, 0, self.h - 1).astype(np.int32)

        distorted_pixels = src[sample_x, sample_y]

        output = pygame.Surface((self.w, self.h)).convert()
        pygame.surfarray.blit_array(output, distorted_pixels)

        return output


class MovingObject:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.x = random.randrange(40, width - 40)
        self.y = random.randrange(80, height - 80)

        self.vx = random.choice([-1, 1]) * random.uniform(45, 110)
        self.vy = random.choice([-1, 1]) * random.uniform(25, 80)

        self.radius = random.randrange(8, 16)
        self.angle = random.uniform(0, math.tau)
        self.spin_speed = random.uniform(-2.5, 2.5)

    def update(self, dt, time_scale):
        # This is the important part:
        # gameplay motion uses dt * time_scale.
        scaled_dt = dt * time_scale

        self.x += self.vx * scaled_dt
        self.y += self.vy * scaled_dt
        self.angle += self.spin_speed * scaled_dt

        if self.x < 30:
            self.x = 30
            self.vx *= -1

        if self.x > self.width - 30:
            self.x = self.width - 30
            self.vx *= -1

        if self.y < 60:
            self.y = 60
            self.vy *= -1

        if self.y > self.height - 30:
            self.y = self.height - 30
            self.vy *= -1

    def draw(self, surface):
        cx = int(self.x)
        cy = int(self.y)

        # Small triangular drone/ship shape.
        points = []

        for i in range(3):
            a = self.angle + i * math.tau / 3
            px = cx + math.cos(a) * self.radius
            py = cy + math.sin(a) * self.radius
            points.append((px, py))

        pygame.draw.polygon(surface, (120, 170, 220), points)
        pygame.draw.polygon(surface, (220, 245, 255), points, 1)

        pygame.draw.circle(surface, (180, 220, 255), (cx, cy), 2)


def make_stars(width, height, count):
    stars = []

    for _ in range(count):
        stars.append(
            {
                "x": random.randrange(width),
                "y": random.randrange(height),
                "speed": random.uniform(12, 45),
                "size": random.choice([1, 1, 1, 2]),
                "brightness": random.randrange(90, 230),
            }
        )

    return stars


def update_and_draw_stars(surface, stars, dt):
    width, height = surface.get_size()

    for star in stars:
        # Stars are background only, so they are not affected by time bubble.
        star["y"] += star["speed"] * dt

        if star["y"] > height:
            star["x"] = random.randrange(width)
            star["y"] = 0
            star["speed"] = random.uniform(12, 45)
            star["brightness"] = random.randrange(90, 230)

        b = star["brightness"]

        pygame.draw.circle(
            surface,
            (b, b, b),
            (int(star["x"]), int(star["y"])),
            star["size"],
        )


def draw_background(surface):
    width, height = surface.get_size()

    surface.fill((4, 6, 18))

    # Subtle background grid so the ripple distortion is easier to see.
    for x in range(0, width, 90):
        pygame.draw.line(surface, (7, 10, 28), (x, 0), (x, height), 1)

    for y in range(0, height, 90):
        pygame.draw.line(surface, (7, 10, 28), (0, y), (width, y), 1)


def draw_time_bubble_overlay(surface, time_bubble, font):
    if not time_bubble or not time_bubble.active:
        return

    time_scale = time_bubble.get_time_scale()
    remaining = time_bubble.timer

    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    # Subtle dark overlay. No center circle, no droplet.
    overlay.fill((20, 35, 60, 24))

    surface.blit(overlay, (0, 0))

    text = font.render(
        f"TIME BUBBLE  {remaining:0.1f}s  speed {time_scale * 100:0.0f}%",
        True,
        (200, 230, 255),
    )

    surface.blit(text, (18, 18))


def main():
    pygame.init()

    width, height = 900, 600
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Space-Time Ripple With Time Bubble")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)

    game_surface = pygame.Surface((width, height)).convert()

    stars = make_stars(width, height, 240)
    moving_objects = [MovingObject(width, height) for _ in range(14)]

    ripple = None
    time_bubble = None

    running = True

    while running:
        dt = clock.tick(60) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    ripple = SpaceTimeRipple(
                        size=(width, height),
                        center=(width // 2, height // 2),
                        speed=90,
                        strength=24,
                        wavelength=95,
                        thickness=210,
                        start_radius=55,
                    )

                    time_bubble = TimeBubble(
                        duration=6.0,
                        min_speed_scale=0.05,
                        release_time=1.5,
                    )

        if time_bubble:
            time_bubble.update(dt)

        time_scale = 1.0

        if time_bubble:
            time_scale = time_bubble.get_time_scale()

        draw_background(game_surface)

        # Stars are drawn first and keep moving normally.
        update_and_draw_stars(game_surface, stars, dt)

        # These objects are "under the stars" and get slowed by the time bubble.
        for obj in moving_objects:
            obj.update(dt, time_scale)
            obj.draw(game_surface)

        draw_time_bubble_overlay(game_surface, time_bubble, font)

        if ripple and ripple.alive:
            ripple.update(dt)
            frame = ripple.apply(game_surface)
        else:
            frame = game_surface

        screen.blit(frame, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()