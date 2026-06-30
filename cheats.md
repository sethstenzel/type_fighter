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
| 14 | Auto-fire | Auto-fires the turret at drones within **70% of half the screen height** from the pod. Toggle on/off with **Left Ctrl x5** (tapped quickly) | During missions |
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
