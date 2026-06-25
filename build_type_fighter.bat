@echo off
setlocal

cd /d "%~dp0"

if not exist "releases" mkdir "releases"

".venv\Scripts\pyinstaller.exe" ^
  --noconfirm ^
  --clean ^
  --distpath "releases" ^
  --workpath "build\pyinstaller" ^
  "TypeFighter.spec"

endlocal
