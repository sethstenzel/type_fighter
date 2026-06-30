# Peer Review — Type Fighter

**Reviewer:** Claude (automated peer review)
**Date:** 2026-06-29
**Scope:** Application source under `src/`, tests under `tests/`, build/installer tooling, and `dev_tools/`. The bundled `.venv/` and `build/` artifacts were excluded.

---

## 1. Overall assessment

This is a well-structured, single-player PyGame typing game in good shape. The codebase is **defensive and self-contained**: no network calls, no `eval`/`exec`/`subprocess`, no `pickle`, and no secrets. The recent move away from server-based sync (per the latest commit) to local SQLite save files (`*.tfp.db` in the user data dir) is clean and sensible.

The data layer (`player_model.py`, `game_config.py`, `player_storage_sqlite.py`) is the strongest part of the code: it validates and normalizes almost every external input, clamps numeric ranges, and tolerates malformed save data without crashing. There is also a real unit-test suite (`tests/`) covering the trickiest game-balance logic (mega-shot charges, accuracy bands, ranks, defense-drone counts).

The two weak spots are **size/duplication** (`game.py` 2.2k lines, `mission_engine.py` 3.3k lines, both with large multi-purpose functions) and **per-frame allocation in the render loop** (fonts and surfaces created every frame). Neither is a correctness emergency, but both will make the game harder to maintain and tune.

| Area | Rating |
|------|--------|
| Correctness / robustness | Good (a few latent crashes) |
| Security / safety | Good (one installer caveat — see `danger.md`) |
| Performance | Fair (per-frame font/surface churn) |
| Maintainability | Fair (large files, duplication, dead code) |
| Testing | Fair-to-good for logic; none for UI/engine loop |

---

## 2. Strengths

- **Input hardening.** `normalize_*` helpers in `player_model.py` / `game_config.py` defensively coerce types, clamp ranges, and fall back to defaults. Save loading (`read_player_db`) survives `JSONDecodeError` and non-dict payloads.
- **Filename safety.** `safe_player_filename` (`player_storage_sqlite.py:35`) strips path-dangerous characters and length-caps the result, so player names can't escape the saves directory.
- **Cross-platform user-data paths.** `user_data_dir()` handles Windows `APPDATA`, `XDG_DATA_HOME`, and a POSIX fallback.
- **Graceful asset/audio degradation.** Image and sound loaders (`load_image`, `load_sound`, `load_ui_image`) catch `OSError`/`pygame.error` and return `None`, and every draw path has a vector fallback — except one (see B1 below).
- **Good test coverage of game-balance math.** `test_player_model.py` and `test_mission_mechanics.py` lock down the subtle rules.
- **Crash logging.** `setup_logging` installs a `sys.excepthook` and a rotating log, and `main()` wraps the loop in try/except/finally with clean shutdown.

---

## 3. Bugs & correctness issues

### B1 — `ONE_SHOT_DRONE_COLOR` is undefined in `game.py` (latent `NameError`). HIGH
`game.py:412` references `ONE_SHOT_DRONE_COLOR` in the mock-battle drone fallback, but the symbol is **never imported or defined in `game.py`** — it only exists in `mission_engine.py:36`. `game.py:25` imports only `create_star_field, draw_star_field, update_star_field`. This path is dormant because drone images normally load, but if `drones/*.png` is missing/corrupt the menu background crashes with `NameError`. Fix: `from lessons.mission_engine import ONE_SHOT_DRONE_COLOR` (or reference `mission_engine.ONE_SHOT_DRONE_COLOR`).

### B2 — Final boss can be counted as defeated twice (state desync). MEDIUM
In the mega-shot loop (`mission_engine.py:3233`), a target that is a `FinalBoss` is **not** revalidated against `self.final_bosses` the way `Drone` targets are at `:3235`. If a second mega shot is already in flight toward a boss that another shot just killed (possible in multi-boss lessons), it re-enters the `isinstance(target, FinalBoss)` branch (`:3250`) and calls `_complete_final_boss` again; the `if target in self.final_bosses` guard skips removal but `self.final_bosses_defeated += 1` (`:2689`) still runs. Fix: at `:3235` also null mega/bullet targets when `isinstance(target, FinalBoss) and target not in self.final_bosses`.

### B3 — `apply_game_settings` casts are unguarded. MEDIUM
`mission_engine.py:200-226` calls `int(settings.get(...))` ~25 times with no try/except. A single non-numeric value in the game-data DB / config JSON raises `ValueError` at startup and the app fails to launch. The sibling `normalize_*` functions are careful here; this one isn't. Fix: a `_safe_int(value, default)` helper.

### B4 — `update_final_boss_shield` is a no-op; shield recharge is dead. MEDIUM
`mission_engine.py:1283` just `return`s. As a result `FINAL_BOSS_SHIELD_DOWN_MS`, `FINAL_BOSS_SHIELD_RECHARGE_MS`, `shield_down_since`, and `next_shield_recharge_time` (maintained in `_shift_gameplay_timers` `:2620-2623` and set at `:3254-3255`) are all inert. Either an unfinished feature or abandoned state — decide and implement or remove.

### B5 — `random.choice` on possibly-empty sequences. LOW/MEDIUM
`random_spawn_key` (`:821`) and `spawn_final_boss` (`:1250`) call `random.choice(... or list(valid_keys))`; if `valid_keys` is also empty this throws `IndexError`. Not reachable with current lesson data, but unguarded.

### B6 — `bool` is a subclass of `int`, so type checks accept booleans. LOW
`normalize_players` (`game.py:443`) and `create_player_record` use `isinstance(lives, int)` etc. `True`/`False` pass these checks and would be coerced into life/score counts. Harmless today but a latent data-quality hole.

### B7 — Functions that ignore their parameters. LOW
`final_boss_projectile_count(lesson_number)` (`:727`) always returns `3`; `should_spawn_mission_drone(lesson_number, ...)` (`:754`) ignores `lesson_number`; `update_final_boss_shield(final_boss, now)` ignores both. Dead parameters mislead readers about behavior.

### B8 — Duplicated, divergent `create_player_record`. LOW
There are two functions of this name: `player_model.py:166` and `game.py:491`, with **different signatures** (the `game.py` one adds `updated_at`/`game_version`). The tests use the model one; the app uses the game one. This is confusing and a refactor hazard — easy to call the wrong one.

---

## 4. Design / structure observations

- **Oversized modules.** `game.py` (2.2k) and `mission_engine.py` (3.3k) each hold dozens of responsibilities. `MissionEngine.run()` alone is ~240 lines (`:3060-3294`) with the event loop, pause logic, bullet loop and mega-shot loop all inline.
- **Duplicated logic across modules.** `normalize_mission_settings`, `DEFAULT_MISSION_SETTINGS`, and the spawn-rate min/max/step constants exist **in both** `player_model.py` and `mission_engine.py`. Shield/upgrade helpers also exist in parallel forms (`player_model.has_upgrade/upgrade_ids` vs `mission_engine.player_upgrade_ids`). These can drift out of sync.
- **Duplicated intro screens.** Lessons 1-4 each ship a ~200-line near-clone of `generic_intro.py` (`lesson_N_intro.py`), differing only in the drawn keyboard art. Lessons 5+ are correct 5-line wrappers. ~800 lines of copy-paste with the same `read_text/play_audio/toggle_fullscreen/get_wav_duration/wrap_lines/run` helpers repeated.
- **Inconsistent fullscreen handling.** The intro modules define their own `toggle_fullscreen()` using `BASE_SCREEN_SIZE = (1024, 768)` (a 4:3 size) and `pygame.display.set_mode`, bypassing the 16:9 letterbox system in `display_helpers.py` that the rest of the game uses. Pressing F11 in an intro can leave the display in a state inconsistent with `game.py`/`mission_engine.py`.
- **Module-global mutable config.** `apply_game_settings` rebinds ~30 module globals and mutates `player_limits.MAX_PLAYER_LIVES`. Works, but makes behavior order-dependent and hard to test in isolation; a config object/dataclass would be safer.
- **Dead code from the removed server feature.** The `player_storage` dict in `game.py:102` (`server_url`, `warning`) is read in `draw_version_label` and `menu_loop` (`:1914`) but **never written anywhere**. The whole `warning`-bail path in `menu_loop` is unreachable now.
- **Minor dead bits.** `started_space_charge = False` in `draw_end_screen` (`:1756`) is unused; `display_key` (`key_render.py:33`) has an `if/else` whose branches are identical.

---

## 5. Performance (render/update loop)

- **P1 (HIGH): per-frame, per-object `pygame.font.SysFont`.** `SysFont` does a font-file lookup and is expensive. It's called:
  - per drone, per frame — `mission_engine.py:2814-2815`
  - per final boss, per frame — `:1568`; per power-up, per frame — `:1533`; HUD footer every frame — `:2851`
  - per drone in the menu mock-battle, per frame — `game.py:414`; per perfect-lesson marker, per frame — `:2145`
  - three fonts rebuilt every frame in `draw_upgrades_modal` — `:1419-1421`

  The HUD font is correctly cached once (`:2163`) — follow that pattern everywhere. Cache the handful of needed (size, bold) fonts at startup.
- **P2 (MED/HIGH): per-particle / per-star `Surface` allocation each frame.** `draw_shot_trails` (`:1413`) and `draw_star_field` (`:1708`) allocate a fresh `SRCALPHA` surface for every particle/star every frame (150 stars + N trails). Pre-render a small bucketed set of circle/star surfaces and blit them.
- **P3 (MED): drone sprite rotated from scratch each frame.** `rotated_drone_image` (`:1208`) caches the *scaled* image but re-runs `pygame.transform.rotate` every frame per drone. Consider caching rotations bucketed by whole-degree angle.
- **P4 (LOW): `mega_shot_speed` rebuilds a dict literal every call** (`:1076`), and it's called per mega-shot per frame. Hoist to a module constant.
- **Positive:** all images/sounds are loaded and scaled once in `MissionEngine.__init__`, not in the loop. The remaining cost is fonts and surface churn.

---

## 6. Testing

- Good logic coverage in `tests/`. Gaps worth filling: save round-trip (`write_player_db`/`read_player_db`), `normalize_players` dedup/clamp behavior, `accuracy_thresholds_for_lesson` boundary at lesson 0/negative, and the credit/score award math in `_calculate_credits_earned`.
- The engine loop and UI modals are untested (understandable given PyGame), but the pure helpers extracted out of them (e.g. a future `_kill_drone`) would be unit-testable.

---

## 7. Conclusion

Solid, shippable hobby/indie codebase with good defensive data handling and a real test suite. Priorities, in order:

1. Fix **B1** (undefined `ONE_SHOT_DRONE_COLOR`) and **B3** (unguarded settings casts) — both can crash the app.
2. Fix **P1** (per-frame `SysFont`) — the single biggest, easiest performance win.
3. Address **B2/B4** final-boss state issues.
4. Reduce duplication (intro screens, shared normalize helpers) and break up the two giant files over time.

See `suggestions.md` for concrete improvement steps and `danger.md` for the one data-loss caveat in the installer.
