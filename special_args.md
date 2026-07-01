# Special Command-Line Arguments

Developer/testing arguments for Type Fighter, passed on the command line when
launching the game. Three families are documented here:

- [`--cheats`](#cheats) — developer cheats.
- [`--secret_level`](#secret-levels) — arm a hidden bonus level.
- [`--play_tests`](#play-tests) — headless autoplay score benchmark.

---

# Cheats

Developer cheats for Type Fighter, enabled from the command line via the
`--cheats` flag. Pass a **comma-delimited list of cheat numbers**.

## How to enable

```bash
# space form
uv run python src/game.py --cheats 1,4,5

# equals form
uv run python src/game.py --cheats=1,4,5

# list the available cheats (logs them, enables nothing)
uv run python src/game.py --cheats list
```

So `--cheats 1,4,5` enables cheats **1**, **4**, and **5** together. Unknown
entries are ignored (and logged as a warning), and the set of enabled cheats is
logged as a warning at startup. Implementation lives in `src/cheats.py`.

## Available cheats

| # | Cheat | What it does | When it applies |
|---|-------|--------------|-----------------|
| 1 | Max lives | Player lives set to **99** | On player select (save) |
| 2 | No life loss | Player does **not lose a life** when hit (the hit still counts) | During missions |
| 3 | Ignore hits | A hit does nothing — **no life lost and not counted** as a hit | During missions |
| 4 | Infinite Mega | Mega Shot charge is **always 5** and never drains when fired (Mega forced available) | During missions |
| 5 | Infinite Shields | Shield charges are **always 3** and never drain when used (shields forced available) | During missions |
| 6 | Infinite Time Stop | Time Stop charges are **always 3** and are never consumed (Time Stop forced available) | During missions |
| 7 | Rich | Player credits set to **100,000** | On player select (save) |
| 8 | Reset high score | Resets the player's high score (lifetime score) to **0** | On player select (save) |
| 9 | Reset achievements | Clears achievements earned so they can **trigger again** | On player select (save) |
| 0 | Full reset | Clears credits, score, unlocked levels, achievements, achievement rewards, and **all purchases** (pod upgrades, extra lives, shield/time-stop charges) | On player select (save) |
| 10 | Unlock all (save) | Marks every level as **unlocked in the save** (persists after relaunch) | On player select (save) |
| 11 | Unlock all (run) | Every training mission is **selectable in the menu** for this run only (no save change) | In the mission menu |
| 12 | Mute error sound | Disables the **wrong-key error sound** | During missions |
| 13 | Mute explosions | Disables the **drone explosion sound** when enemies are destroyed | During missions |
| 14 | Auto-fire | Auto-fires the turret at drones within **90% of the smaller screen dimension** from the pod (the same range the defense drones use), and finishes the final boss with a full Mega Shot. Toggle on/off with **Left Ctrl x5** (tapped quickly) | During missions |
| 15 | 10x spawn rate | Increases the drone **spawn rate to 10x** | During missions |

## Notes

- **Save-modifying cheats** — **1, 7, 8, 9, 10, 0** are written to the player's
  save the moment that player is selected, so their effects persist after you
  quit, even if you relaunch without `--cheats`. Use **8, 9, and especially 0**
  with care on a real profile (0 is a full progress wipe).
- **Mission cheats** — **2, 3, 4, 5, 6, 12, 13, 14, 15** only take effect while
  playing a mission and leave the save alone. Cheats 4/5/6 also force the
  relevant ability to be available even if you have not unlocked it yet.
- **Auto-fire (14)** starts enabled when the cheat is on; tap **Left Ctrl five
  times quickly** to toggle it off or back on mid-mission. It targets regular
  drones and mini-bosses within range and, on a boss level, unloads a full Mega
  Shot to finish the final boss once charged.
- **Unlock-all variants** — **10** marks every level unlocked *in the save*
  (persists); **11** unlocks every mission in the menu for the current run only
  (no save change).
- Cheats are intended for development/testing. They do not gate badges fairly
  (e.g. cheat 2 still counts hits, so it will not grant a no-damage perfect run).

---

# Secret Levels

Hidden bonus stages, armed from the command line via the `--secret_level` flag.
Pass a **single level number**. Implementation lives in `src/secret_levels.py`
(argument parsing) and `src/lessons/secret_level.py` (the level itself).

## How to enable

```bash
# space form
uv run python src/game.py --secret_level 1

# equals form
uv run python src/game.py --secret_level=1
```

Arming a secret level does **not** launch it directly. It only makes it
reachable from the mission menu:

1. Launch the game with `--secret_level 1` (a warning is logged confirming the
   armed level).
2. In the mission menu, **hold Shift** and select **training mission one**
   (Enter/Space or click) — this launches the secret level instead of the normal
   lesson 1 mission.

Selecting mission one **without** Shift held still plays the normal lesson, and
Shift+selecting any other mission does nothing special.

## Available secret levels

| # | Level | What it is |
|---|-------|------------|
| 1 | Reposition Mission 1 | Pilot the pod from the right side of the field to a goal zone far off screen to the left, then hold station inside the target for 10 continuous seconds. Thrust is a limited resource (the orange gauge) with real thruster physics — the pod is pushed opposite whichever thruster you fire (Shift+S/F left/right, Shift+E/D top/bottom). Your normal loadout (defense drones, shields, mega shot, time stop) works if unlocked. 3-minute time limit. |

## Notes

- Only the numbers listed above have an implementation. Passing an unimplemented
  number (e.g. `--secret_level 2`) is accepted and logged, but nothing becomes
  reachable — Shift+selecting mission one just plays the normal lesson.
- Secret levels are reached only through **training mission one**; the armed
  number does not map to any other menu entry.
- Completing a secret level shows its own summary screen but does **not** mark
  lesson 1 complete or alter save progress.

---

# Play Tests

A headless benchmark that autoplays **every training mission 30 times** and
reports the **average base score** per level, to calibrate scoring/high-score
goals. Implementation lives in `src/play_tests.py`, with the headless run in
`src/lessons/mission_engine.py` (`simulate_mission` / `simulate_autoplay`).

## How to enable

`--play_tests` is an **on/off flag**:

```bash
# space form
uv run python src/game.py --play_tests 1

# equals form
uv run python src/game.py --play_tests=1

# a bare flag also turns it on
uv run python src/game.py --play_tests
```

Any value other than `0`/`false`/`no`/`off` turns it on. When on, the game skips
the menu entirely: it runs the benchmark and then exits.

## What it does

- For each of the 36 training missions, it plays **30 runs** with the auto-fire
  bot (cheat **14** logic) on a **virtual clock** — no rendering, audio, or
  real-time wait, so a full run takes roughly a second each.
- It forces cheats **3** (ignore hits, so a stray drone can't end a run) and
  **4** (infinite Mega, needed to clear multi-hp drones and the final boss).
  Each run uses a **fresh throwaway pilot**, so your saves are never touched.
- **Base score** = the mission score with **mega/mini-boss bonus points removed**
  and **without power-up points** (the bot never collects power-ups, so those
  never count). Because splitting drones award the same base whether cleared by
  typing or by Mega Shot, the bot's base score matches normal play.

## Output

- A per-level table is printed to the console (avg / min / max / stdev of base
  score, and how many of the 30 runs were won).
- Machine-readable results are written to `play_test_results/` as timestamped
  `play_tests_<stamp>.json` and `play_tests_<stamp>.csv`.

## Notes

- The mode needs a working display/audio init like the normal game (it reuses
  the real mission engine), so run it on a machine that can open the game window.
- Defense drones and shields are **off** for the test pilot so they don't add
  score noise; Mega Shot is available (via cheat 4) because the bot needs it.
- A run that fails to finish within the simulated time cap (~6 minutes of game
  time) is counted as `timed_out` and still contributes its score so far; the
  per-level line flags any timeouts.
