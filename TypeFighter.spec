# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_dir = Path.cwd()
src_dir = project_dir / "src"

datas = [
    (str(src_dir / "gfx"), "gfx"),
    (str(src_dir / "sfx"), "sfx"),
    (str(src_dir / "lessons"), "lessons"),
]

players_path = project_dir / "players.json"
if players_path.exists():
    datas.append((str(players_path), "."))

hiddenimports = [
    "lessons.generic_intro",
    "lessons.generic_mission",
    "lessons.key_render",
    "lessons.lesson_config",
    "lessons.mission_engine",
]

for lesson_dir in sorted((src_dir / "lessons").glob("lesson_*")):
    if lesson_dir.is_dir():
        lesson_name = lesson_dir.name
        hiddenimports.extend(
            [
                f"lessons.{lesson_name}",
                f"lessons.{lesson_name}.{lesson_name}_intro",
                f"lessons.{lesson_name}.{lesson_name}_mission",
            ]
        )


a = Analysis(
    [str(src_dir / "game.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Type Fighter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(src_dir / "gfx" / "type-fighter-icon.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Type Fighter",
)
