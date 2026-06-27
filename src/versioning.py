import json
import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
CLIENT_VERSION_INFO_PATH = MODULE_DIR / "version_info.json"
BUILD_VERSION_PATH = MODULE_DIR.parent / "build_version.json"


def _version_from_state(data):
    return f"{int(data.get('major', 0))}.{int(data.get('minor', 1))}.{int(data.get('next_patch', 0))}{data.get('suffix', 'a')}"


def client_version():
    data_paths = [CLIENT_VERSION_INFO_PATH]
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        data_paths.insert(0, Path(sys.executable).resolve().parent / "version_info.json")

    for path in data_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        version = data.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()

    try:
        data = json.loads(BUILD_VERSION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "0.0.0"
    return _version_from_state(data)


CLIENT_VERSION = client_version()
