"""Central game font loader.

Loads the bundled OTF (gfx/game_font_1.otf) and caches Font objects by
(size, bold). Falls back to the system Arial if the font can't be loaded, so the
game still renders if the asset is missing.

Bold is intentionally disabled: the game font is always rendered at its regular
weight. The `bold` argument is kept for call-site compatibility but no longer
applies synthetic bolding.

The font lives in gfx/, which the build bundles via --include-data-dir, so it is
packaged alongside the executable. The path is resolved the same frozen/dev way
as the rest of the assets.
"""

import sys
from pathlib import Path

import pygame


def _running_frozen():
    return getattr(sys, "frozen", False) or "__compiled__" in globals()


def _base_dir():
    if _running_frozen():
        return Path(sys.executable).resolve().parent
    # fonts.py lives in src/, alongside gfx/ during development.
    return Path(__file__).resolve().parent


GAME_FONT_PATH = _base_dir() / "gfx" / "game_font_1.otf"

_font_cache = {}


def get_font(size, bold=False):
    size = max(1, int(size))
    key = (size, bool(bold))
    cached = _font_cache.get(key)
    if cached is not None:
        return cached
    font = None
    try:
        if GAME_FONT_PATH.exists():
            font = pygame.font.Font(str(GAME_FONT_PATH), size)
            # Bold is intentionally never applied -- always regular weight.
            font.set_bold(False)
    except (OSError, pygame.error):
        font = None
    if font is None:
        font = pygame.font.SysFont("arial", size, bold=False)
    _font_cache[key] = font
    return font
