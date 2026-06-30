# Suggestions — Type Fighter

Actionable improvements, ordered roughly by value. References use `file:line`. See `peer-review.md` for the full review and `danger.md` for the safety caveat.

---

## A. Quick wins (low effort, high value)

1. **Fix the undefined color crash.** Add `ONE_SHOT_DRONE_COLOR` to the import in `game.py:25` (or use `mission_engine.ONE_SHOT_DRONE_COLOR` at `game.py:412`). Without this, a missing drone sprite crashes the menu.
2. **Guard settings casts.** Replace the ~25 raw `int(settings.get(...))` calls in `mission_engine.py:200-226` with a `_safe_int(value, default)` helper so a bad config value can't prevent startup.
3. **Cache fonts instead of recreating them every frame.** Create the needed fonts once (e.g. on the engine / at module load) and reuse them:
   - `mission_engine.py:2814-2815` (drone labels), `:1568` (boss), `:1533` (power-up), `:2851` (footer)
   - `game.py:414` (mock-battle drone), `:2145` (perfect marker), `:1419-1421` (upgrades modal)

   Pattern already exists at `mission_engine.py:2163` (`self.font`).
4. **Delete dead server state.** Remove the `player_storage` dict (`game.py:102`), the `warning` read in `draw_version_label`, and the unreachable `if player_storage.get("warning")` bail in `menu_loop` (`:1914`). They're leftovers from the removed sync feature.
5. **Remove small dead code.** Unused `started_space_charge` in `draw_end_screen` (`mission_engine.py:1756`); the identical `if/else` branches in `display_key` (`key_render.py:33`); the `# TODO: Pretty sure this is old code` constant `PLAYER_SHIELD_RECHARGE_MS` (`mission_engine.py:130`) — resolve or delete.

---

## B. Correctness hardening

6. **Revalidate final-boss shot targets** (B2): at `mission_engine.py:3235`, also null the target when `isinstance(target, FinalBoss) and target not in self.final_bosses`, so a stray in-flight mega shot can't double-increment `final_bosses_defeated`.
7. **Resolve the dead shield-recharge logic** (B4): either implement `update_final_boss_shield` (`:1283`) or remove `shield_down_since` / `next_shield_recharge_time` and their shift logic.
8. **Guard empty key sets** in `random_spawn_key` (`:821`) and `spawn_final_boss` (`:1250`) before `random.choice`.
9. **Tighten boolean-vs-int checks.** Where booleans should not count as numbers (`game.py:443`, etc.), use `isinstance(x, int) and not isinstance(x, bool)`.
10. **Drop or use ignored parameters**: `final_boss_projectile_count` (`:727`), `should_spawn_mission_drone`'s `lesson_number` (`:754`).

---

## C. De-duplication / structure

11. **Consolidate the two `create_player_record` functions.** Have `game.py` either call `player_model.create_player_record` and add its extra metadata fields there, or rename one so it's obvious which is which. Two same-named functions with different signatures (`player_model.py:166`, `game.py:491`) is a foot-gun.
12. **Single source for mission settings.** `normalize_mission_settings`, `DEFAULT_MISSION_SETTINGS`, and `MIN/MAX/STEP` spawn-rate constants are duplicated in `player_model.py` and `mission_engine.py`. Keep one copy (in `player_model.py`) and import it.
13. **Collapse lessons 1-4 intros.** Convert `lesson_1_intro.py` … `lesson_4_intro.py` (~200 lines each) into 5-line wrappers around `generic_intro.run_intro`, the way lessons 5-36 already are. Move the per-lesson keyboard art into a small data table / callback that `generic_intro` can render, so there's one intro implementation.
14. **Extract helpers out of `MissionEngine.run()`** (`:3060-3294`): `_handle_keydown(event)`, `_update_bullets(dt, now)`, `_update_mega_shots(dt, now)`. This also makes the kill logic testable.
15. **Factor out the repeated "kill a drone" block.** The `destroyed += level_value; score += 100; explode; play explosion` sequence appears at `:3217-3225`, `:3275-3283`, and `_count_defense_drone_kill` (`:2954`). Extract `_kill_drone(drone)`.
16. **Factor the bullet/mega homing loops.** `:3188-3231` and `:3233-3289` are near-identical; a shared `_advance_homing_shot(...)` would remove a whole class of copy-paste bugs (B2 is exactly that class).
17. **De-duplicate text truncation.** `draw_wrapped_text` (`:469`) and `draw_wrapped_centered_text` (`:485`) share identical ellipsis code — extract `_truncate_lines`.

---

## D. Consistency

18. **Unify fullscreen handling.** The intro modules' private `toggle_fullscreen()` (e.g. `generic_intro.py:44`, `lesson_1_intro.py:44`) uses a 4:3 `BASE_SCREEN_SIZE` and bypasses the 16:9 letterbox system in `display_helpers.py`. Route all fullscreen toggles through `display_helpers` so F11 behaves the same everywhere.
19. **Promote magic numbers to named constants** in hot paths: bullet speed `560` (`:1154`), homing speed `650` (`:3229`), turret offsets `28`/`34`, mega-bar `y` `51/28`, trail scale `0.5625` (`:3239`/`:3288`), and the blocked-rect literals (`:2700-2707`).
20. **Consider a config dataclass** instead of the ~30 module globals rebound by `apply_game_settings`. Easier to test, immutable per run, no cross-module global mutation (`player_limits.MAX_PLAYER_LIVES`).

---

## E. Tooling, packaging, docs

21. **Flesh out `README.md`.** Currently two lines. Add: how to run (`uv run python src/game.py`), how to run tests (`uv run python -m unittest discover tests`), CLI flags (`--logging`, `--verbose-logging`, `--debug`), save-file location, and build instructions.
22. **Add a test runner / CI.** A GitHub Actions job running `unittest` on push would catch regressions in the well-tested logic layer.
23. **Pin / trim dependencies.** `pyproject.toml` bundles three TTS engines (`kokoro`, `piper-tts`, `pyttsx3`, `pykokoro`) plus `spacy`. These appear to be **build/dev-only** (used in `dev_tools/`), not by the game at runtime. Move them to an optional/dev dependency group so end-user installs and Nuitka builds stay lean.
24. **Add a `requires_upgrade`/data-integrity self-check** (optional): a tiny test that asserts every `UPGRADE_CATALOG` `requires_upgrade`/`icon` and every `ACHIEVEMENTS` `image` references an id/file that exists.
25. **`build_version.json` / `version_info.json` are tracked and edited by builds.** Consider documenting that `tools/prepare_alpha_build.py` bumps them, so the working-tree churn (they're modified in `git status`) is expected.

---

## F. Minor polish

26. `versioning.py:12` builds the version string with hardcoded default minor `1` and suffix `a`; fine, but a malformed `build_version.json` silently yields `"0.0.0"` — consider logging that fallback.
27. `mega_shot_speed` dict → module constant (`:1076`).
28. `final_boss_count` (`:586`) reads both `str` and `int` keys from `FINAL_BOSS_COUNT_BY_LESSON` to cope with JSON stringified keys — fine, but normalize keys once on load instead of probing both on every call.
