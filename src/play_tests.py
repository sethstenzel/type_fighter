"""Headless autoplay benchmark: --play_tests.

Plays every training mission RUNS_PER_LEVEL times with the auto-fire bot on a
virtual clock (no rendering, audio, or real-time wait) and reports the average
*base* score per level -- score with mega/mini-boss bonus points removed and
without power-up points (the bot never collects power-ups, so those never
count). This gives a stable per-level baseline for tuning high-score goals.

Enable with (on/off flag):

    uv run python src/game.py --play_tests 1
    uv run python src/game.py --play_tests=1

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


def requested(argv):
    """Return True if --play_tests is present with a truthy value.

    Accepts ``--play_tests 1``, ``--play_tests=1`` and a bare ``--play_tests``
    (treated as on). ``--play_tests 0`` (or false/no/off) turns it off.
    """
    for index, arg in enumerate(argv):
        if arg.startswith("--play_tests="):
            value = arg.split("=", 1)[1]
        elif arg == "--play_tests":
            nxt = argv[index + 1] if index + 1 < len(argv) else None
            value = nxt if (nxt is not None and not nxt.startswith("-")) else "1"
        else:
            continue
        return value.strip().lower() not in _FALSY
    return False


def _make_test_player():
    """A fresh, unencumbered pilot: no defense drones or shields (so they do not
    add score), default loadout. Infinite Mega comes from cheat 4 below."""
    return player_model.create_player_record("__play_tests__")


def _summarize(lesson_number, base_scores, won, timed_out, runs):
    return {
        "lesson_number": lesson_number,
        "runs": runs,
        "won": won,
        "timed_out": timed_out,
        "avg_base_score": round(statistics.fmean(base_scores), 1) if base_scores else 0,
        "min_base_score": min(base_scores) if base_scores else 0,
        "max_base_score": max(base_scores) if base_scores else 0,
        "stdev_base_score": round(statistics.pstdev(base_scores), 1) if len(base_scores) > 1 else 0.0,
        "base_scores": base_scores,
    }


def _log_progress(summary):
    print(
        "  lesson %2d: avg base %8.1f  (min %d / max %d, stdev %.1f)  won %d/%d%s"
        % (
            summary["lesson_number"],
            summary["avg_base_score"],
            summary["min_base_score"],
            summary["max_base_score"],
            summary["stdev_base_score"],
            summary["won"],
            summary["runs"],
            "  [!%d timed out]" % summary["timed_out"] if summary["timed_out"] else "",
        )
    )


def _print_table(results):
    print("\n" + "=" * 78)
    print("PLAY-TEST RESULTS  (base score = total minus bonuses and power-up points)")
    print("=" * 78)
    header = "%-7s %5s %5s %11s %9s %9s %9s" % (
        "Lesson", "Runs", "Won", "AvgBase", "Min", "Max", "StDev",
    )
    print(header)
    print("-" * 78)
    for row in results:
        print(
            "%-7d %5d %5d %11.1f %9d %9d %9.1f"
            % (
                row["lesson_number"],
                row["runs"],
                row["won"],
                row["avg_base_score"],
                row["min_base_score"],
                row["max_base_score"],
                row["stdev_base_score"],
            )
        )
    print("=" * 78)


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
             "avg_base_score", "min_base_score", "max_base_score", "stdev_base_score"]
        )
        for row in results:
            writer.writerow(
                [row["lesson_number"], row["runs"], row["won"], row["timed_out"],
                 row["avg_base_score"], row["min_base_score"],
                 row["max_base_score"], row["stdev_base_score"]]
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
            won += 1 if outcome["won"] else 0
            timed_out += 1 if outcome["timed_out"] else 0
        summary = _summarize(number, base_scores, won, timed_out, runs_per_level)
        results.append(summary)
        _log_progress(summary)

    _print_table(results)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = _write_results(base_dir, results, runs_per_level, stamp)
    print("\nResults written to:\n  %s\n  %s" % (paths["json"], paths["csv"]))
    return results
