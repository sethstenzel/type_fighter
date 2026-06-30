# Danger Fixes — Type Fighter

Summary of the work resolving the three findings recorded in `danger.md`. Each was filed as a GitHub issue and fixed on the `fix/danger-issues` branch, then merged to `main`.

| Issue | Finding | Severity | Status |
|-------|---------|----------|--------|
| [#4](https://github.com/sethstenzel/type-fighter/issues/4) | Installer `RMDir /r "$INSTDIR"` could delete unrelated user files | Med–High (data loss) | Fixed |
| [#5](https://github.com/sethstenzel/type-fighter/issues/5) | Unguarded `int()` casts in `apply_game_settings` could crash startup | Low–Med (stability) | Fixed |
| [#6](https://github.com/sethstenzel/type-fighter/issues/6) | Undefined `ONE_SHOT_DRONE_COLOR` in `game.py` (`NameError`) | Low (stability) | Fixed |

---

## #4 — Installer data-loss footgun
**File:** `installer/type_fighter_installer.nsi`

The uninstaller ran `RMDir /r "$INSTDIR"` on a user-chosen install directory, so installing into an existing non-empty folder (e.g. `Documents`) and later uninstalling would recursively delete unrelated files.

**Fix — two complementary guards:**
1. **Install:** before copying files, the installer enumerates `$INSTDIR` with `FindFirst`/`FindNext` and **aborts with a message if the folder is not empty**, so `$INSTDIR` only ever contains files we created.
2. **Uninstall:** before `RMDir /r`, it checks `IfFileExists "$INSTDIR\Type Fighter.exe"` and **aborts if the folder doesn't look like a Type Fighter install**, so the recursive delete can't run against an unexpected location.

Together these make it impossible for uninstall to wipe a folder the installer didn't create and populate. (Saves already live in `%APPDATA%\TypeFighter`, unaffected either way.)

## #5 — Unguarded config casts could crash startup
**File:** `src/lessons/mission_engine.py` (`apply_game_settings`)

~25 calls of `int(settings.get(key, default))` would raise `ValueError`/`TypeError` on any non-numeric value in the on-disk config (`game_data.db` / config JSON), preventing the game from launching.

**Fix:** added a `_safe_int(value, default)` helper that returns the default on `TypeError`/`ValueError`, and routed every cast in `apply_game_settings` through it. Corrupt or hand-edited values now fall back to defaults instead of crashing — matching the defensive style of the existing `normalize_*` helpers.

## #6 — `NameError` on asset-load failure
**File:** `src/game.py`

`game.py` referenced `ONE_SHOT_DRONE_COLOR` (defined only in `mission_engine.py`) in the mock-battle drone fallback path. If a drone sprite failed to load, the menu crashed with `NameError`.

**Fix:** imported `ONE_SHOT_DRONE_COLOR` from `lessons.mission_engine` alongside the existing star-field imports.

---

## Verification
- `python -m py_compile` on `game.py` and `mission_engine.py` — OK.
- Import check confirms `ONE_SHOT_DRONE_COLOR` resolves the way `game.py` imports it.
- `apply_game_settings({...bad values...})` no longer raises and falls back to defaults.
- Full unit-test suite (`tests/`) passes under the project venv.
- Work was done in an isolated git worktree branched from `main`, so unrelated in-progress changes in the main working tree were not bundled into these fixes.

> Note: `installer/type_fighter_installer.nsi` was not compiled with `makensis` (not installed in this environment); the changes use standard NSIS instructions (`FindFirst`/`FindNext`/`IfFileExists`/`Abort`) and were reviewed by hand.
