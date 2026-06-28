from pathlib import Path
import wave

import pygame
import session_state

from lessons.key_render import display_key, inline_text_width, render_inline_center, render_inline_text
from lessons.lesson_config import lesson_fingers, lesson_new_keys, lesson_title


BG_COLOR = (8, 12, 24)
PANEL = (14, 24, 45)
PANEL_EDGE = (48, 67, 105)
TEXT_COLOR = (230, 238, 255)
MUTED_TEXT = (142, 154, 184)
ACCENT = (72, 209, 204)
NEW_KEY = (245, 203, 92)
BASE_SCREEN_SIZE = (1024, 768)
INTRO_SCROLL_END_BUFFER_SECONDS = 8
FALLBACK_SCROLL_SECONDS = 120


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return "Lesson text could not be loaded."


def play_audio(path):
    if not pygame.mixer.get_init() or not Path(path).exists():
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


def draw_training_image(surface, rect, title_font, small_font, lesson_number):
    new_keys = lesson_new_keys(lesson_number)
    title = f"Lesson {lesson_number}: {lesson_title(lesson_number)}"
    key_text = "   ".join(display_key(key) for key in new_keys)

    pygame.draw.rect(surface, (12, 20, 38), rect, border_radius=10)
    pygame.draw.rect(surface, PANEL_EDGE, rect, 2, border_radius=10)
    surface.blit(title_font.render(title, True, TEXT_COLOR), (rect.x + 28, rect.y + 22))

    key_font = pygame.font.SysFont("arial", 46, bold=True)
    key_box = pygame.Rect(0, 0, max(260, inline_text_width(key_text, key_font) + 80), 90)
    key_box.center = (rect.centerx, rect.y + 145)
    pygame.draw.rect(surface, NEW_KEY, key_box, border_radius=10)
    pygame.draw.rect(surface, (245, 250, 255), key_box, 3, border_radius=10)
    render_inline_center(surface, key_text, key_font, (4, 10, 20), key_box.center)

    fingers = f"Main fingers: {lesson_fingers(lesson_number)}"
    surface.blit(small_font.render(fingers, True, TEXT_COLOR), (rect.x + 300, rect.y + 220))
    surface.blit(
        small_font.render("Keep your hands anchored. Press the new keys, then return to ready position.", True, MUTED_TEXT),
        (rect.x + 150, rect.y + 254),
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


def run_intro(screen, clock, base_dir, lesson_number):
    lesson_dir = Path(base_dir) / "lessons" / f"lesson_{lesson_number}"
    intro_audio_path = lesson_dir / f"lesson_{lesson_number}_intro.wav"
    intro_text = read_text(lesson_dir / f"lesson_{lesson_number}_intro.txt")
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
        if session_state.has_forced_disconnect():
            stop_audio()
            return "signin"
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
        draw_training_image(screen, image_rect, title_font, small_font, lesson_number)
        draw_scroll_text(screen, text_rect, lines, body_font, scroll_y)

        prompt = f"Press ␣ to launch Lesson {lesson_number}"
        render_inline_center(screen, prompt, prompt_font, ACCENT, (width / 2, prompt_y))
        screen.blit(
            small_font.render("F11: Max size  |  Esc: Menu  |  Mouse wheel or Up/Down: Scroll", True, MUTED_TEXT),
            (panel_left, footer_y),
        )
        pygame.display.flip()
