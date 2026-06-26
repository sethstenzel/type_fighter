import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
VERSION_PATH = PROJECT_DIR / "build_version.json"
PREPARED_RELEASE_PATH = PROJECT_DIR / "build" / "release_name.txt"


def load_version_state():
    if not VERSION_PATH.exists():
        return {
            "major": 0,
            "minor": 1,
            "next_patch": 0,
            "suffix": "a",
        }

    with VERSION_PATH.open("r", encoding="utf-8") as version_file:
        state = json.load(version_file)

    return {
        "major": int(state.get("major", 0)),
        "minor": int(state.get("minor", 1)),
        "next_patch": int(state.get("next_patch", 0)),
        "suffix": str(state.get("suffix", "a")),
    }


def save_version_state(state):
    with VERSION_PATH.open("w", encoding="utf-8") as version_file:
        json.dump(state, version_file, indent=2)
        version_file.write("\n")


def main():
    build_suffix = sys.argv[1] if len(sys.argv) > 1 else ""
    state = load_version_state()
    version = f"{state['major']}.{state['minor']}.{state['next_patch']}{state['suffix']}"
    release_name = f"type-fighter-v{version}{build_suffix}"

    state["next_patch"] += 1
    save_version_state(state)

    PREPARED_RELEASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREPARED_RELEASE_PATH.write_text(release_name + "\n", encoding="utf-8")
    print(release_name)


if __name__ == "__main__":
    main()
