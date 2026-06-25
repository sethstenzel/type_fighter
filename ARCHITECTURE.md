# Type Fighter Architecture

Type Fighter is a Pygame typing trainer. The application is structured around a player/profile menu, a sequential lesson curriculum, per-lesson intro screens, and a shared arcade mission engine.

## Runtime Entry Point

- `src/game.py` is the application entry point.
- Running it initializes Pygame, starts fullscreen mode, opens the player selection screen, then enters the lesson menu for the selected player.
- The main loop flow is:
  1. `main()`
  2. `player_select_loop()`
  3. `menu_loop()`
  4. `run_lesson()`
  5. lesson intro module
  6. lesson mission module

`game.py` dynamically imports lesson modules from strings stored in `LESSONS`.

## Player And Progress Data

- Player data is stored in root-level `players.json`.
- `game.py` reads and writes this file through:
  - `load_players()`
  - `save_players()`
  - `mark_lesson_complete()`
- Each player record has:

```json
{
  "name": "Player Name",
  "completed_lessons": [1, 2, 3],
  "lives": 3,
  "shield_charges": 0
}
```

Progression is prefix-based. `unlocked_lesson_count()` unlocks only the first incomplete lesson after the longest completed prefix. Completing lesson 5 without completing lesson 4 would not unlock lesson 6.

`lives` and `shield_charges` are persistent player resources. `run_lesson()` passes the active player record into mission modules, and `MissionEngine` reads and writes those resource values during missions. If a player has fewer than 3 lives when a mission starts, the mission engine raises them back to 3 before play begins. `menu_loop()` saves the player list after mission return so resource changes survive between games and app sessions.

## Curriculum Definition

- `src/lessons/lesson_config.py` is the curriculum source of truth.
- `LESSON_PROGRESS` defines all 36 lessons.
- Each lesson tuple contains:
  - lesson number
  - newly introduced keys
  - finger guidance
  - title
  - menu summary

Important helpers:

- `learned_keys_through(lesson_number)` returns every key learned up to that lesson.
- `lesson_new_keys(lesson_number)` returns only the newly introduced keys for that lesson.
- `lesson_title(lesson_number)` and `lesson_fingers(lesson_number)` feed intro UI text.

## Lesson Module Pattern

Every lesson folder lives under `src/lessons/lesson_N/`.

Typical files:

- `lesson_N_intro.py`
- `lesson_N_intro.txt`
- `lesson_N_intro.wav`
- `lesson_N_mission.py`
- `lesson_N_instructions.txt`
- `lesson_N_instructions.wav`
- `__init__.py`

For most lessons, intro and mission modules are thin wrappers:

```python
from lessons.generic_intro import run_intro


def run(screen, clock, base_dir):
    return run_intro(screen, clock, base_dir, 3)
```

```python
from lessons.generic_mission import run_lesson_mission


def run(screen, clock, base_dir, player=None):
    return run_lesson_mission(screen, clock, base_dir, 3, player)
```

Lessons 1 and 2 have more custom wrappers and UI, but gameplay runs through the shared mission engine.

## Intro System

- Generic intro code lives in `src/lessons/generic_intro.py`.
- It reads `lesson_N_intro.txt`, plays `lesson_N_intro.wav`, displays a training panel, and scrolls text based on audio duration.
- Inputs:
  - `Space`: start mission
  - `Esc`: return to menu
  - `F11`: toggle fullscreen
  - mouse wheel or up/down: manual scroll

Lesson 1 and lesson 2 have specialized intro modules with custom visuals, but they follow the same `run(screen, clock, base_dir)` contract.

## Mission System

- The mission engine lives in `src/lessons/mission_engine.py`.
- `src/lessons/generic_mission.py` calls `run_mission()` with:
  - screen
  - clock
  - base directory
  - lesson directory name
  - all keys learned through the current lesson

Mission wrapper flow:

```python
run_lesson_mission(screen, clock, base_dir, lesson_number)
    -> run_mission(screen, clock, base_dir, f"lesson_{lesson_number}", learned_keys_through(lesson_number), player)
```

`run_mission()` is a compatibility wrapper that instantiates `MissionEngine` and calls `MissionEngine.run()`.

`MissionEngine` handles:

- audio loading and playback
- drone spawning
- player input
- turret aiming and firing
- bullets and mega shots
- mini-bosses
- final boss logic
- shields
- power-ups
- pause menu
- HUD and end screen

Lesson-specific mission files now act as wrappers. For example, `src/lessons/lesson_1/lesson_1_mission.py` re-exports the shared engine for compatibility and passes lesson 1's directory and valid keys to `run_mission()`.

Return values are string commands consumed by `game.py`:

- `"won"`: lesson completed
- `"menu"`: return to mission menu
- `"quit"`: exit app
- `"restart"`: rerun the mission

## Mission Progression Rules

Drone target count is currently calculated in `lesson_drone_target()`:

- lessons 1-2: 30 drones
- lessons 3-4: 40 drones
- lessons 5+: `46 + lesson_number`

Mini-bosses start at lesson 3:

- `mini_bosses_enabled(lesson_number)`
- scheduled by `mini_boss_numbers_for_lesson()`
- default interval is every 10 mission drones

Mega shot and final boss start at lesson 5:

- `mega_shot_enabled(lesson_number)`
- `final_boss_enabled(lesson_number)`

Player shield starts at lesson 7:

- `player_shield_enabled(lesson_number)`

Recent accounting model:

- `Drone.level_value` controls whether a drone advances mission completion.
- Normal mission drones default to `1.0`.
- Split drone children divide the parent `level_value`.
- Boss projectiles use `level_value=0`.
- Non-final-boss lessons can spawn replacement mission drones if drones reach the player and leave the mission below target.

Relevant helpers:

- `drone_counts_for_level()`
- `active_level_value()`
- `should_spawn_mission_drone()`

## Input Handling

`event_to_lesson_key()` maps Pygame key events to lesson key labels.

Special labels include:

- `space`
- `enter`
- `backspace`
- `tab`
- `caps lock`
- `shift`

For printable characters, the lowercase `event.unicode` is used.

During missions:

- pressing a target key queues a turret shot
- holding space in later lessons enables mega-shot charging
- `Esc` opens the pause menu
- `F11` toggles fullscreen/windowed

## Rendering Helpers

- `src/lessons/key_render.py` owns inline key rendering.
- It replaces the internal space symbol with a rendered spacebar SVG icon.
- Main helpers:
  - `display_key()`
  - `inline_text_width()`
  - `render_inline_text()`
  - `render_inline_center()`
  - `render_key_label()`

The spacebar asset is `src/gfx/spacebar.svg`.

## Assets

Shared game assets:

- `src/gfx/`
  - `pod.png`
  - `turret.png`
  - `spacebar.svg`
  - `yellow_drone.png`
  - `orange_drone.png`
  - `red_drone.png`
  - `semi-boss.png`
  - `final-boss.png`
- `src/sfx/`
  - `laser.ogg`
  - `explosion.ogg`
  - `boss.ogg`
  - `split.ogg`
  - `health.ogg`
  - `victory.wav`
  - `bg_music.wav`

Lesson-specific assets live inside each lesson folder:

- intro text/audio
- mission instruction text/audio
- optional lesson-specific images

## Dependency And Environment Notes

- Project metadata is in `pyproject.toml`.
- Python requirement is `>=3.13`.
- Runtime depends on `pygame`.
- The repo has a `.venv`; use it for Pygame checks because system Python may not have Pygame installed.

Common checks:

```powershell
python -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in Path('src').rglob('*.py')]; print('syntax ok')"
```

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import game; print('game import ok')"
```

## Where To Make Common Changes

- Add or change lesson order: edit `src/lessons/lesson_config.py`.
- Add a new lesson folder: create `src/lessons/lesson_N/` with intro/mission wrappers and text/audio assets.
- Change player progression: edit `src/game.py`.
- Change mission rules, enemies, scoring, or win conditions: edit `src/lessons/mission_engine.py`.
- Change how keys render in text or drone labels: edit `src/lessons/key_render.py`.
- Change generic intro layout or scrolling: edit `src/lessons/generic_intro.py`.
- Change all generic mission lesson key sets: edit `src/lessons/generic_mission.py` or `lesson_config.py`.

## Current Structural Caveat

`mission_engine.py` now has a `MissionEngine` class that owns mission setup and mutable mission state. The first separation pass extracted frame timing, spawning, frame drawing, pending-shot handling, final-boss updates, drone updates, and particle updates into private methods. Event handling plus bullet and mega-shot hit resolution are still large blocks inside `MissionEngine.run()` and are the next candidates for extraction.
