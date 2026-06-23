from pathlib import Path

import pygame


SPACE_KEY = "space"
SPACE_SYMBOL = "␣"
_SPACEBAR_PATH = Path(__file__).resolve().parents[1] / "gfx" / "spacebar.svg"
_RAW_SPACEBAR = None
_SPACEBAR_CACHE = {}


def display_key(key):
    if key == SPACE_KEY:
        return SPACE_SYMBOL
    return key.upper() if len(key) == 1 and key.isalpha() else key.upper()


def _load_raw_spacebar():
    global _RAW_SPACEBAR
    if _RAW_SPACEBAR is not None:
        return _RAW_SPACEBAR
    try:
        _RAW_SPACEBAR = pygame.image.load(str(_SPACEBAR_PATH)).convert_alpha()
    except (OSError, pygame.error):
        _RAW_SPACEBAR = False
    return _RAW_SPACEBAR


def _spacebar_surface(height, color, max_width=None):
    raw = _load_raw_spacebar()
    if raw is False:
        return None
    height = max(8, int(height))
    width = max(8, int(raw.get_width() * height / raw.get_height()))
    if max_width and width > max_width:
        width = max(8, int(max_width))
        height = max(8, int(raw.get_height() * width / raw.get_width()))

    tint = color if len(color) == 4 else color[:3] + (255,)
    cache_key = (width, height, tint)
    if cache_key in _SPACEBAR_CACHE:
        return _SPACEBAR_CACHE[cache_key]

    scaled = pygame.transform.smoothscale(raw, (width, height))
    mask = pygame.mask.from_surface(scaled)
    tinted = mask.to_surface(setcolor=tint, unsetcolor=(0, 0, 0, 0)).convert_alpha()
    _SPACEBAR_CACHE[cache_key] = tinted
    return tinted


def inline_text_width(text, font, spacebar_height=None):
    if SPACE_SYMBOL not in text:
        return font.size(text)[0]
    height = spacebar_height or int(font.get_height() * 0.9)
    width = 0
    parts = text.split(SPACE_SYMBOL)
    for index, part in enumerate(parts):
        width += font.size(part)[0]
        if index < len(parts) - 1:
            icon = _spacebar_surface(height, (255, 255, 255))
            width += icon.get_width() if icon is not None else font.size(SPACE_SYMBOL)[0]
    return width


def render_inline_text(surface, text, font, color, pos, spacebar_height=None):
    x, y = pos
    if SPACE_SYMBOL not in text:
        rendered = font.render(text, True, color)
        surface.blit(rendered, (x, y))
        return rendered.get_rect(topleft=(x, y))

    height = spacebar_height or int(font.get_height() * 0.9)
    cursor_x = x
    rects = []
    parts = text.split(SPACE_SYMBOL)
    for index, part in enumerate(parts):
        if part:
            rendered = font.render(part, True, color)
            rect = rendered.get_rect(topleft=(cursor_x, y))
            surface.blit(rendered, rect)
            rects.append(rect)
            cursor_x = rect.right
        if index < len(parts) - 1:
            icon = _spacebar_surface(height, color)
            if icon is None:
                rendered = font.render(SPACE_SYMBOL, True, color)
                rect = rendered.get_rect(topleft=(cursor_x, y))
                surface.blit(rendered, rect)
            else:
                rect = icon.get_rect()
                rect.midleft = (cursor_x, y + font.get_height() / 2)
                surface.blit(icon, rect)
            rects.append(rect)
            cursor_x = rect.right

    if not rects:
        return pygame.Rect(x, y, 0, font.get_height())
    return rects[0].unionall(rects[1:])


def render_inline_center(surface, text, font, color, center, spacebar_height=None):
    width = inline_text_width(text, font, spacebar_height)
    x = center[0] - width / 2
    y = center[1] - font.get_height() / 2
    return render_inline_text(surface, text, font, color, (x, y), spacebar_height)


def render_key_label(surface, key, font, color, center, max_width=None):
    if key != SPACE_KEY:
        label = font.render(display_key(key), True, color)
        surface.blit(label, label.get_rect(center=center))
        return

    icon = _spacebar_surface(int(font.get_height() * 0.95), color, max_width)
    if icon is None:
        label = font.render(SPACE_SYMBOL, True, color)
        surface.blit(label, label.get_rect(center=center))
        return
    surface.blit(icon, icon.get_rect(center=center))
