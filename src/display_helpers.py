import pygame


ASPECT_WIDTH = 16
ASPECT_HEIGHT = 9
ASPECT_RATIO = ASPECT_WIDTH / ASPECT_HEIGHT
SCREEN_SIZE = (1280, 720)
MIN_SCREEN_SIZE = (1024, 576)
WINDOW_FLAGS = pygame.RESIZABLE

_original_display_get_surface = pygame.display.get_surface
_original_display_flip = pygame.display.flip
_original_mouse_get_pos = pygame.mouse.get_pos
_original_event_get = pygame.event.get
_patches_installed = False
_letterboxed_fullscreen = False
_physical_surface = None
_render_surface = None
_render_rect = pygame.Rect(0, 0, 0, 0)


def aspect_locked_size(width, height, minimum=MIN_SCREEN_SIZE):
    width = max(1, int(width))
    height = max(1, int(height))

    locked_width = width
    locked_height = round(locked_width / ASPECT_RATIO)
    if locked_height > height:
        locked_height = height
        locked_width = round(locked_height * ASPECT_RATIO)

    min_width, min_height = minimum
    if locked_width < min_width:
        locked_width = min_width
        locked_height = round(locked_width / ASPECT_RATIO)
    if locked_height < min_height:
        locked_height = min_height
        locked_width = round(locked_height * ASPECT_RATIO)

    return locked_width, locked_height


def desktop_aspect_size():
    info = pygame.display.Info()
    width = getattr(info, "current_w", 0) or SCREEN_SIZE[0]
    height = getattr(info, "current_h", 0) or SCREEN_SIZE[1]
    return aspect_locked_size(width, height, minimum=(1, 1))


def desktop_size():
    sizes = []
    if hasattr(pygame.display, "get_desktop_sizes"):
        try:
            sizes = pygame.display.get_desktop_sizes()
        except pygame.error:
            sizes = []
    if sizes:
        display_index = max(0, min(active_display_index(), len(sizes) - 1))
        return sizes[display_index]

    info = pygame.display.Info()
    width = getattr(info, "current_w", 0) or SCREEN_SIZE[0]
    height = getattr(info, "current_h", 0) or SCREEN_SIZE[1]
    return width, height


def active_display_index():
    if not hasattr(pygame.display, "get_window_display_index"):
        return 0
    try:
        return max(0, pygame.display.get_window_display_index())
    except pygame.error:
        return 0


def is_letterboxed_fullscreen():
    return _letterboxed_fullscreen


def _center_rect(size, bounds):
    rect = pygame.Rect(0, 0, *size)
    rect.center = (bounds[0] // 2, bounds[1] // 2)
    return rect


def _display_get_surface():
    if _letterboxed_fullscreen and _render_surface is not None:
        return _render_surface
    return _original_display_get_surface()


def _translate_physical_pos(pos):
    if not _letterboxed_fullscreen:
        return pos
    x, y = pos
    if not _render_rect.collidepoint(x, y):
        return -1, -1
    return x - _render_rect.x, y - _render_rect.y


def _mouse_get_pos():
    return _translate_physical_pos(_original_mouse_get_pos())


def _event_get(*args, **kwargs):
    events = _original_event_get(*args, **kwargs)
    if not _letterboxed_fullscreen:
        return events
    for index, event in enumerate(events):
        if hasattr(event, "pos"):
            translated_pos = _translate_physical_pos(event.pos)
            try:
                event.pos = translated_pos
            except (AttributeError, TypeError):
                event_data = dict(getattr(event, "dict", {}))
                event_data["pos"] = translated_pos
                events[index] = pygame.event.Event(event.type, event_data)
    return events


def _display_flip():
    if _letterboxed_fullscreen and _physical_surface is not None and _render_surface is not None:
        _physical_surface.fill((0, 0, 0))
        _physical_surface.blit(_render_surface, _render_rect)
    return _original_display_flip()


def _install_display_patches():
    global _patches_installed
    if _patches_installed:
        return
    pygame.display.get_surface = _display_get_surface
    pygame.display.flip = _display_flip
    pygame.mouse.get_pos = _mouse_get_pos
    pygame.event.get = _event_get
    _patches_installed = True


def set_fullscreen_16_9():
    global _letterboxed_fullscreen, _physical_surface, _render_surface, _render_rect
    _install_display_patches()
    display_index = active_display_index()
    physical_size = desktop_size()
    logical_size = aspect_locked_size(*physical_size, minimum=(1, 1))
    try:
        _physical_surface = pygame.display.set_mode(physical_size, pygame.FULLSCREEN, display=display_index)
    except TypeError:
        _physical_surface = pygame.display.set_mode(physical_size, pygame.FULLSCREEN)
    _render_surface = pygame.Surface(logical_size).convert()
    _render_rect = _center_rect(logical_size, physical_size)
    _letterboxed_fullscreen = True
    return _render_surface


def set_windowed_16_9(size=SCREEN_SIZE):
    global _letterboxed_fullscreen, _physical_surface, _render_surface, _render_rect
    _letterboxed_fullscreen = False
    _render_surface = None
    _render_rect = pygame.Rect(0, 0, 0, 0)
    _physical_surface = pygame.display.set_mode(aspect_locked_size(*size), WINDOW_FLAGS)
    return _physical_surface


def enforce_16_9_window(screen):
    global _physical_surface
    if _letterboxed_fullscreen or screen.get_flags() & pygame.FULLSCREEN:
        return screen

    current_size = screen.get_size()
    locked_size = aspect_locked_size(*current_size)
    if current_size == locked_size:
        return screen
    _physical_surface = pygame.display.set_mode(locked_size, WINDOW_FLAGS)
    return _physical_surface
