import importlib
import json
from pathlib import Path
import re

import pygame

from lessons.lesson_config import LESSON_PROGRESS
from lessons.key_render import render_inline_text
from lessons.mission_engine import create_star_field, draw_star_field, update_star_field


SCREEN_SIZE = (1024, 768)
WINDOW_FLAGS = pygame.RESIZABLE
BG_COLOR = (8, 12, 24)
TEXT_COLOR = (230, 238, 255)
MUTED_TEXT = (138, 150, 178)
ACCENT = (72, 209, 204)
LOCKED_SELECTED = (245, 203, 92)
STARTING_LIVES = 3
PLAYER_SHIELD_MAX_CHARGES = 3
DEFAULT_POD = {"color": "blue", "type": "standard", "upgrades": []}

BASE_DIR = Path(__file__).resolve().parent
PLAYERS_PATH = BASE_DIR.parent / "players.json"
is_fullscreen = True


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
                shield_charges=max(0, min(PLAYER_SHIELD_MAX_CHARGES, shield_charges)),
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
    pod_upgrades = pod.get("upgrades", [])
    if not isinstance(pod_color, str) or not pod_color.strip():
        pod_color = DEFAULT_POD["color"]
    if not isinstance(pod_type, str) or not pod_type.strip():
        pod_type = DEFAULT_POD["type"]
    if not isinstance(pod_upgrades, list):
        pod_upgrades = []

    return {
        "name": name,
        "completed_lessons": completed_lessons or [],
        "lives": max(1, lives),
        "shield_charges": max(0, min(PLAYER_SHIELD_MAX_CHARGES, shield_charges)),
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

    while True:
        update_star_field(stars, clock.get_time() / 1000)
        if selected >= len(players):
            selected = max(0, len(players) - 1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
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

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        content_width = min(820, max(620, width - 120))
        content_left = (width - content_width) / 2
        text_left = content_left + 20
        screen.fill(BG_COLOR)
        draw_star_field(screen, stars)

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
            for index, player in enumerate(players):
                if not first_visible <= index < first_visible + visible_rows:
                    continue
                x, y = text_left, list_top + (index - first_visible) * item_gap
                is_selected = index == selected
                card_color = (20, 32, 58) if is_selected else (13, 22, 42)
                border_color = ACCENT if is_selected else (43, 57, 89)
                unlocked = unlocked_lesson_count(player)
                rank = player_rank(player)
                pygame.draw.rect(screen, card_color, (content_left, y - 20, content_width, 82), border_radius=8)
                pygame.draw.rect(screen, border_color, (content_left, y - 20, content_width, 82), 2, border_radius=8)
                draw_text(screen, player["name"], item_font, TEXT_COLOR, (x, y - 4))
                summary = f"Unlocked missions: {unlocked}/{len(LESSONS)}    Rank: {rank}"
                draw_text(screen, summary, body_font, MUTED_TEXT, (x, y + 34))

        if delete_confirm and players:
            message = f"Delete {players[selected]['name']}? Press Y to confirm or N to cancel."
            draw_text(screen, message, small_font, (245, 203, 92), (text_left + 4, height - 88))
        draw_text(screen, "Enter/␣: Select  |  N: New  |  Delete: Delete  |  Q: Quit  |  F11: Max size", small_font, MUTED_TEXT, (text_left + 4, height - 58))
        pygame.display.flip()
        clock.tick(60)


def menu_loop(screen, clock, players, player):
    title_font = pygame.font.SysFont("arial", 54, bold=True)
    item_font = pygame.font.SysFont("arial", 30, bold=True)
    body_font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 18)

    selected = 0
    stars = create_star_field()

    while True:
        update_star_field(stars, clock.get_time() / 1000)
        unlocked_count = unlocked_lesson_count(player)

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
                        result = run_lesson(screen, clock, LESSONS[completed_index], player)
                        save_players(players)
                        if result == "quit":
                            return "quit"
                        if result == "won":
                            mark_lesson_complete(player, LESSONS[completed_index]["number"])
                            save_players(players)
                            selected = min(completed_index + 1, unlocked_lesson_count(player) - 1)
                        pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP))

        screen = pygame.display.get_surface()
        width, height = screen.get_size()
        content_width = min(820, max(620, width - 120))
        content_left = (width - content_width) / 2
        text_left = content_left + 20
        screen.fill(BG_COLOR)
        draw_star_field(screen, stars)
        draw_text(screen, "TYPE FIGHTER", title_font, TEXT_COLOR, (text_left, 90))
        draw_text(
            screen,
            f"{player['name']}    Rank: {player_rank(player)}    Unlocked: {unlocked_count}/{len(LESSONS)}",
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
        pygame.display.flip()
        clock.tick(60)


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass

    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Type Fighter")
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
