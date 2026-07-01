# Special Command-Line Arguments

Developer/testing arguments for Type Fighter, passed on the command line when
launching the game. Two families are documented here:

- [`--cheats`](#cheats) — developer cheats.
- [`--secret_level`](#secret-levels) — arm a hidden bonus level.

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
| 14 | Auto-fire | Auto-fires the turret at drones within **90% of half the screen height** from the pod. Toggle on/off with **Left Ctrl x5** (tapped quickly) | During missions |
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
  times quickly** to toggle it off or back on mid-mission. It only targets
  regular drones/mini-bosses within range, not the final boss.
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
