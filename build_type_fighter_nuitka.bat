@echo off
setlocal

cd /d "%~dp0"

if not exist "releases" mkdir "releases"
if not exist "build\nuitka" mkdir "build\nuitka"

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Python was not found in .venv.
  exit /b 1
)

"%~dp0.venv\Scripts\python.exe" -m nuitka --version >nul 2>nul

if errorlevel 1 (
  echo Nuitka was not found in .venv. Run: uv add nuitka
  exit /b 1
)

"%~dp0.venv\Scripts\python.exe" "%~dp0tools\prepare_alpha_build.py" "_ntk"

if errorlevel 1 (
  echo Failed to prepare Type Fighter Nuitka release version.
  exit /b 1
)

if exist "%~dp0build\release_name.txt" (
  set /p TYPE_FIGHTER_RELEASE_NAME=<"%~dp0build\release_name.txt"
)

if "%TYPE_FIGHTER_RELEASE_NAME%"=="" (
  echo Failed to prepare Type Fighter Nuitka release version.
  exit /b 1
)

set "NUITKA_WORK_DIR=%~dp0build\nuitka"
set "NUITKA_DIST_DIR=%NUITKA_WORK_DIR%\game.dist"
set "RELEASE_DIR=%~dp0releases\%TYPE_FIGHTER_RELEASE_NAME%"

echo Building %TYPE_FIGHTER_RELEASE_NAME% with Nuitka

if exist "%NUITKA_DIST_DIR%" rmdir /s /q "%NUITKA_DIST_DIR%"
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"

"%~dp0.venv\Scripts\python.exe" -m nuitka ^
  --standalone ^
  --assume-yes-for-downloads ^
  --output-dir="%NUITKA_WORK_DIR%" ^
  --output-filename="Type Fighter.exe" ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico="%~dp0src\gfx\type-fighter-icon.ico" ^
  --include-package=lessons ^
  --include-data-dir="%~dp0src\gfx=gfx" ^
  --include-data-dir="%~dp0src\sfx=sfx" ^
  --include-data-dir="%~dp0src\lessons=lessons" ^
  --include-data-files="%~dp0src\settings.cfg=settings.cfg" ^
  --include-data-files="%~dp0src\version_info.json=version_info.json" ^
  --noinclude-data-files="*.psd" ^
  --noinclude-data-files="*.PSD" ^
  --noinclude-data-files="**/*.psd" ^
  --noinclude-data-files="**/*.PSD" ^
  "%~dp0src\game.py"

if errorlevel 1 (
  echo Nuitka build failed.
  exit /b 1
)

if not exist "%NUITKA_DIST_DIR%" (
  echo Nuitka did not create the expected dist folder: %NUITKA_DIST_DIR%
  exit /b 1
)

move "%NUITKA_DIST_DIR%" "%RELEASE_DIR%" >nul

if errorlevel 1 (
  echo Failed to move Nuitka release into releases.
  exit /b 1
)

echo Nuitka build complete: %RELEASE_DIR%

endlocal
