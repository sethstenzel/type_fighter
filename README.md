# Type Fighter

Type Fighter is a space-combat typing game built with Python and Pygame. Each lesson introduces new keyboard keys, then turns practice into short arcade missions where typed keys fire shots at matching enemy drones.

The game is designed as a structured typing trainer with progression, upgrades, achievements, boss fights, and local player profiles.

## Game Features

- 36 typing lessons with intro narration and mission briefing text.
- Mission-based combat where each enemy drone is destroyed by typing its displayed key.
- Progressive keyboard coverage, including shifted-symbol lessons starting later in the course.
- Mega Shot and Advanced Mega Shot mechanics for stronger targets.
- Shields, extra lives, defense drones, upgrade purchases, and upgrade selling.
- Final boss encounters, mini bosses, split drones, power ups, and mission rewards.
- Accuracy tracking, perfect-mission tracking, and achievement rewards.
- Player customization through splash color and shot color upgrades.
- Local-only player saves using per-player SQLite databases.
- Fullscreen/windowed display handling with 16:9 presentation support.
- Nuitka and NSIS build scripts for Windows release builds.

## Running From Source

This project uses `uv`.

```powershell
uv sync
uv run python .\src\game.py
```

Verbose logging can be enabled with:

```powershell
uv run python .\src\game.py --logging
```

Client logs are written under:

```text
%APPDATA%\TypeFighter\type_fighter.log
```

## Local Saves

Type Fighter currently uses local/offline saves only. Player profiles are stored as separate SQLite databases under:

```text
%APPDATA%\TypeFighter\saves\mock_steam_id\
```

Each player profile is saved as:

```text
<player-name>.tfp.db
```

The `mock_steam_id` folder is a temporary stand-in for future Steam integration.

## Building

Build a Windows standalone release with Nuitka:

```powershell
.\build_type_fighter_nuitka.bat
```

Build the Nuitka release and then create a Windows installer with NSIS:

```powershell
.\build_type_fighter_with_installer.bat
```

Build outputs are written to:

```text
releases\
```

## Tests

Run the current unit tests with:

```powershell
uv run python -m unittest tests.test_player_model tests.test_mission_mechanics
```

## Project Notes

- Achievement details are documented in [achievements.md](achievements.md).
- Lesson content and assets live under `src/lessons`.
- Main game assets live under `src/gfx` and `src/sfx`.
