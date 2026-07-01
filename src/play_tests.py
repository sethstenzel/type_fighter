"""Headless autoplay benchmark: --play_tests.

Plays every training mission RUNS_PER_LEVEL times with the auto-fire bot on a
virtual clock (no rendering, audio, or real-time wait) and reports the average
*base* score per level -- score with mega/mini-boss bonus points removed and
without power-up points (the bot never collects power-ups, so those never
count). This gives a stable per-level baseline for tuning high-score goals.

Enable with a bare flag (default 30 runs per level) or pass a run count:

    uv run python src/game.py --play_tests        # 30 runs per level
    uv run python src/game.py --play_tests 25      # 25 runs per level
    uv run python src/game.py --play_tests=25      # 25 runs per level

``--play_tests 0`` (or off/false/no) turns it off. Each run also records the
in-game time taken to complete the level; the table and results files report
average/min/max completion time alongside the base score.

Results are printed as a table and written to ``play_test_results/`` as JSON and
CSV. Implementation of the headless run lives in ``lessons/mission_engine.py``
(``simulate_mission`` / ``MissionEngine.simulate_autoplay``).
"""

from __future__ import annotations

import csv
import datetime
import json
import statistics
from pathlib import Path

import cheats
import player_model
from lessons.lesson_config import LESSON_PROGRESS, learned_keys_through
from lessons.mission_engine import simulate_mission


# Every level is played this many times to average out spawn RNG.
RUNS_PER_LEVEL = 30

# Falsy values that turn the flag off (anything else turns it on).
_FALSY = {"", "0", "false", "no", "off"}


def _flag_value(argv):
    """Raw string passed to --play_tests, or None if the flag is absent.

    A bare ``--play_tests`` (no value) yields the sentinel ``"on"`` so it reads
    as enabled with the default run count rather than "1 run".
    """
    for index, arg in enumerate(argv):
        if arg.startswith("--play_tests="):
            return arg.split("=", 1)[1]
        if arg == "--play_tests":
            nxt = argv[index + 1] if index + 1 < len(argv) else None
            return nxt if (nxt is not None and not nxt.startswith("-")) else "on"
    return None


def requested(argv):
    """Return True if --play_tests is present and not turned off.

    Accepts ``--play_tests``, ``--play_tests 1``, ``--play_tests=25`` and so on.
    ``--play_tests 0`` (or false/no/off) turns it off.
    """
    value = _flag_value(argv)
    return value is not None and value.strip().lower() not in _FALSY


def resolve_runs(argv, default=RUNS_PER_LEVEL):
    """Runs-per-level from ``--play_tests <n>`` (e.g. ``--play_tests 25`` -> 25).

    Falls back to ``default`` for a bare flag or any non positive-integer value.
    """
    value = _flag_value(argv)
    if value is not None:
        try:
            runs = int(value.strip())
        except ValueError:
            runs = 0
        if runs > 0:
            return runs
    return default


def _make_test_player():
    """A fresh, unencumbered pilot: no defense drones or shields (so they do not
    add score), default loadout. Infinite Mega comes from cheat 4 below."""
    return player_model.create_player_record("__play_tests__")


def _summarize(lesson_number, base_scores, times_ms, won, timed_out, runs):
    # times_ms is the in-game level timer per run (simulated time to complete
    # the level; it freezes during time-stop and the boss intro, matching what
    # the player sees on the end screen).
    return {
        "lesson_number": lesson_number,
        "runs": runs,
        "won": won,
        "timed_out": timed_out,
        "avg_base_score": round(statistics.fmean(base_scores), 1) if base_scores else 0,
        "min_base_score": min(base_scores) if base_scores else 0,
        "max_base_score": max(base_scores) if base_scores else 0,
        "stdev_base_score": round(statistics.pstdev(base_scores), 1) if len(base_scores) > 1 else 0.0,
        "avg_time_ms": round(statistics.fmean(times_ms)) if times_ms else 0,
        "min_time_ms": min(times_ms) if times_ms else 0,
        "max_time_ms": max(times_ms) if times_ms else 0,
        "base_scores": base_scores,
        "times_ms": times_ms,
    }


def _log_progress(summary):
    print(
        "  lesson %2d: avg base %8.1f  (min %d / max %d, stdev %.1f)  avg time %5.1fs  won %d/%d%s"
        % (
            summary["lesson_number"],
            summary["avg_base_score"],
            summary["min_base_score"],
            summary["max_base_score"],
            summary["stdev_base_score"],
            summary["avg_time_ms"] / 1000.0,
            summary["won"],
            summary["runs"],
            "  [!%d timed out]" % summary["timed_out"] if summary["timed_out"] else "",
        )
    )


def _print_table(results):
    width = 96
    print("\n" + "=" * width)
    print("PLAY-TEST RESULTS  (base score = total minus bonuses and power-up points;")
    print("                    time = simulated in-game seconds to complete the level)")
    print("=" * width)
    header = "%-7s %5s %5s %11s %9s %9s %9s %8s %8s" % (
        "Lesson", "Runs", "Won", "AvgBase", "Min", "Max", "StDev", "AvgTime", "MaxTime",
    )
    print(header)
    print("-" * width)
    for row in results:
        print(
            "%-7d %5d %5d %11.1f %9d %9d %9.1f %7.1fs %7.1fs"
            % (
                row["lesson_number"],
                row["runs"],
                row["won"],
                row["avg_base_score"],
                row["min_base_score"],
                row["max_base_score"],
                row["stdev_base_score"],
                row["avg_time_ms"] / 1000.0,
                row["max_time_ms"] / 1000.0,
            )
        )
    print("=" * width)


def _results_dir(base_dir):
    # base_dir is the src/ folder; write alongside the project root.
    return Path(base_dir).parent / "play_test_results"


def _write_results(base_dir, results, runs_per_level, stamp):
    out_dir = _results_dir(base_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"play_tests_{stamp}.json"
    csv_path = out_dir / f"play_tests_{stamp}.csv"

    json_path.write_text(
        json.dumps(
            {
                "generated_at": stamp,
                "runs_per_level": runs_per_level,
                "note": "base_score excludes mega/mini-boss bonus points and power-up points",
                "levels": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["lesson_number", "runs", "won", "timed_out",
             "avg_base_score", "min_base_score", "max_base_score", "stdev_base_score",
             "avg_time_ms", "min_time_ms", "max_time_ms"]
        )
        for row in results:
            writer.writerow(
                [row["lesson_number"], row["runs"], row["won"], row["timed_out"],
                 row["avg_base_score"], row["min_base_score"],
                 row["max_base_score"], row["stdev_base_score"],
                 row["avg_time_ms"], row["min_time_ms"], row["max_time_ms"]]
            )

    return {"json": json_path, "csv": csv_path}


def run(screen, clock, base_dir, runs_per_level=RUNS_PER_LEVEL):
    """Run the full benchmark and return the per-level summaries."""
    # The bot needs: ignore hits (never fail from a drone reaching the pod) and
    # infinite Mega (to clear multi-hp drones and the final boss).
    cheats.enable_from_argv(["--cheats", "3,4"])

    print(
        "Running play-tests: %d training missions x %d runs each (headless autoplay)..."
        % (len(LESSON_PROGRESS), runs_per_level)
    )

    results = []
    for number, _keys, *_rest in LESSON_PROGRESS:
        base_scores = []
        times_ms = []
        won = 0
        timed_out = 0
        valid_keys = learned_keys_through(number)
        for _ in range(runs_per_level):
            outcome = simulate_mission(
                screen,
                clock,
                base_dir,
                f"lesson_{number}",
                valid_keys,
                _make_test_player(),
            )
            base_scores.append(outcome["base_score"])
            times_ms.append(outcome["level_time_ms"])
            won += 1 if outcome["won"] else 0
            timed_out += 1 if outcome["timed_out"] else 0
        summary = _summarize(number, base_scores, times_ms, won, timed_out, runs_per_level)
        results.append(summary)
        _log_progress(summary)

    _print_table(results)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = _write_results(base_dir, results, runs_per_level, stamp)
    print("\nResults written to:\n  %s\n  %s" % (paths["json"], paths["csv"]))
    return results
