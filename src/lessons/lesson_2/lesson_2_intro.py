from pathlib import Path
import wave

import pygame

from lessons.key_render import inline_text_width, render_inline_center, render_inline_text, render_key_label


BG_COLOR = (8, 12, 24)
PANEL = (14, 24, 45)
PANEL_EDGE = (48, 67, 105)
TEXT_COLOR = (230, 238, 255)
MUTED_TEXT = (142, 154, 184)
ACCENT = (72, 209, 204)
LEFT_KEY = (70, 120, 190)
RIGHT_KEY = (88, 166, 132)
NEW_KEY = (245, 203, 92)
BASE_SCREEN_SIZE = (1024, 768)
INTRO_SCROLL_END_BUFFER_SECONDS = 8
FALLBACK_SCROLL_SECONDS = 150


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return "Lesson text could not be loaded."


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


def get_wav_duration(path):
    try:
        with wave.open(str(path), "rb") as audio:
            return audio.getnframes() / audio.getframerate()
    except (OSError, wave.Error, ZeroDivisionError):
        return FALLBACK_SCROLL_SECONDS


def wrap_lines(text, font, max_width):
    lines = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue

        words = paragraph.split()
        current = ""
        for word in words:
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


def draw_keyboard_image(surface, rect, title_font, small_font):
    pygame.draw.rect(surface, (12, 20, 38), rect, border_radius=10)
    pygame.draw.rect(surface, PANEL_EDGE, rect, 2, border_radius=10)
    render_inline_text(surface, "Add D, K, and ␣: Middle Fingers and Thumbs", title_font, TEXT_COLOR, (rect.x + 28, rect.y + 22))

    keys = ["A", "S", "D", "F", "J", "K", "L", ";"]
    start_x = rect.x + 154
    key_y = rect.y + 128
    key_w = 62
    gap = 10
    for index, key in enumerate(keys):
        x = start_x + index * (key_w + gap)
        color = LEFT_KEY if key in ("A", "S", "D", "F") else RIGHT_KEY
        if key in ("D", "K"):
            color = NEW_KEY
        elif key in ("F", "J"):
            color = ACCENT
        pygame.draw.rect(surface, color, (x, key_y, key_w, 54), border_radius=7)
        pygame.draw.rect(surface, (220, 244, 255), (x, key_y, key_w, 54), 2, border_radius=7)
        label = small_font.render(key, True, (4, 10, 20))
        surface.blit(label, label.get_rect(center=(x + key_w / 2, key_y + 27)))

    space_rect = pygame.Rect(rect.x + 298, key_y + 74, 300, 44)
    pygame.draw.rect(surface, NEW_KEY, space_rect, border_radius=7)
    pygame.draw.rect(surface, (220, 244, 255), space_rect, 2, border_radius=7)
    render_key_label(surface, "space", small_font, (4, 10, 20), space_rect.center, space_rect.width - 24)

    left_note = "Left middle -> D"
    right_note = "Right middle -> K"
    thumb_note = "Either thumb -> ␣"
    surface.blit(small_font.render(left_note, True, TEXT_COLOR), (rect.x + 242, rect.y + 212))
    surface.blit(small_font.render(right_note, True, TEXT_COLOR), (rect.x + 508, rect.y + 212))
    render_inline_text(surface, thumb_note, small_font, TEXT_COLOR, (rect.x + 386, rect.y + 244))
    render_inline_text(
        surface,
        "Keep F and J as your beacons. Add D, K, and ␣ without looking down.",
        small_font,
        MUTED_TEXT,
        (rect.x + 154, rect.y + 274),
    )


def draw_scroll_text(surface, rect, lines, font, scroll_y):
    pygame.draw.rect(surface, PANEL, rect, border_radius=8)
    pygame.draw.rect(surface, PANEL_EDGE, rect, 2, border_radius=8)

    clip = surface.get_clip()
    surface.set_clip(rect.inflate(-20, -20))
    y = rect.y + 16 - scroll_y
    line_height = font.get_height() + 8
    for line in lines:
        if rect.y - line_height <= y <= rect.bottom:
            render_inline_text(surface, line, font, TEXT_COLOR, (rect.x + 18, y))
        y += line_height
    surface.set_clip(clip)


def run(screen, clock, base_dir):
    lesson_dir = Path(base_dir) / "lessons" / "lesson_2"
    intro_audio_path = lesson_dir / "lesson_2_intro.wav"
    intro_text = read_text(lesson_dir / "lesson_2_intro.txt")
    play_audio(intro_audio_path)

    title_font = pygame.font.SysFont("arial", 30, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 18, bold=True)
    prompt_font = pygame.font.SysFont("arial", 24, bold=True)

    intro_duration = max(1, get_wav_duration(intro_audio_path) - INTRO_SCROLL_END_BUFFER_SECONDS)
    lines = []
    max_scroll = 0
    scroll_speed = 0
    scroll_y = 0.0
    last_text_width = None

    while True:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_audio()
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                if event.key == pygame.K_ESCAPE:
                    stop_audio()
                    return "menu"
                if event.key == pygame.K_SPACE:
                    stop_audio()
                    return "start"
                if event.key == pygame.K_DOWN:
                    scroll_y = min(max_scroll, scroll_y + 42)
                if event.key == pygame.K_UP:
                    scroll_y = max(0, scroll_y - 42)
            if event.type == pygame.MOUSEWHEEL:
                scroll_y = max(0, min(max_scroll, scroll_y - event.y * 36))

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        panel_width = min(844, max(620, width - 120))
        panel_left = (width - panel_width) / 2
        image_rect = pygame.Rect(panel_left, 38, panel_width, 300)
        prompt_y = height - 82
        footer_y = height - 42
        text_height = max(120, min(292, int(prompt_y - 34 - 370)))
        text_rect = pygame.Rect(panel_left, 370, panel_width, text_height)
        if text_rect.width != last_text_width:
            lines = wrap_lines(intro_text, body_font, text_rect.width - 44)
            max_scroll = max(0, len(lines) * (body_font.get_height() + 8) - text_rect.height + 44)
            scroll_speed = max_scroll / intro_duration if max_scroll else 0
            scroll_y = min(scroll_y, max_scroll)
            last_text_width = text_rect.width

        scroll_y = min(max_scroll, scroll_y + scroll_speed * dt)

        screen.fill(BG_COLOR)
        draw_keyboard_image(screen, image_rect, title_font, small_font)
        draw_scroll_text(screen, text_rect, lines, body_font, scroll_y)

        prompt = "Press ␣ to launch Lesson 2"
        render_inline_center(screen, prompt, prompt_font, ACCENT, (width / 2, prompt_y))
        screen.blit(
            small_font.render("F11: Max size  |  Esc: Menu  |  Mouse wheel or Up/Down: Scroll", True, MUTED_TEXT),
            (panel_left, footer_y),
        )

        pygame.display.flip()
