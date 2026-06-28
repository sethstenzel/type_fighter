from __future__ import annotations

import wave

import pygame


def play_audio(path):
    if path.exists() and pygame.mixer.get_init():
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except pygame.error:
            pass


def stop_audio():
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()


def load_sound(path, volume=1.0):
    if not path.exists() or not pygame.mixer.get_init():
        return None
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(volume)
        return sound
    except pygame.error:
        return None


def load_first_sound(paths, volume=1.0):
    for path in paths:
        sound = load_sound(path, volume)
        if sound is not None:
            return sound
    return None


def play_sound(sound):
    if sound is not None:
        try:
            sound.play()
        except pygame.error:
            pass


def play_looping_sound(sound, fade_ms=0):
    if sound is None:
        return None
    try:
        return sound.play(loops=-1, fade_ms=fade_ms)
    except pygame.error:
        return None


def stop_looping_sound(channel, fade_ms=0):
    if channel is None:
        return
    try:
        channel.fadeout(fade_ms) if fade_ms else channel.stop()
    except pygame.error:
        pass


def audio_duration_ms(path):
    if not path.exists():
        return 0
    try:
        with wave.open(str(path), "rb") as audio_file:
            frames = audio_file.getnframes()
            rate = audio_file.getframerate()
            return int(frames / rate * 1000) if rate else 0
    except (wave.Error, OSError, EOFError):
        return 0
