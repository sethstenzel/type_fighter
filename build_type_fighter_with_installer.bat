@echo off
setlocal

cd /d "%~dp0"

if not exist "releases" mkdir "releases"
if not exist "build" mkdir "build"

set "MAKENSIS="
where makensis.exe >nul 2>nul
if not errorlevel 1 set "MAKENSIS=makensis.exe"

if "%MAKENSIS%"=="" if exist "%ProgramFiles(x86)%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if "%MAKENSIS%"=="" if exist "%ProgramFiles%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"

if "%MAKENSIS%"=="" (
  echo NSIS was not found.
  echo Install NSIS from https://nsis.sourceforge.io/Download or add makensis.exe to PATH.
  exit /b 1
)

call "%~dp0build_type_fighter_nuitka.bat"

if errorlevel 1 (
  echo Nuitka build failed; installer was not created.
  exit /b 1
)

if exist "%~dp0build\release_name.txt" (
  set /p TYPE_FIGHTER_RELEASE_NAME=<"%~dp0build\release_name.txt"
)

if "%TYPE_FIGHTER_RELEASE_NAME%"=="" (
  echo Failed to read build\release_name.txt.
  exit /b 1
)

set "RELEASE_DIR=%~dp0releases\%TYPE_FIGHTER_RELEASE_NAME%"
set "INSTALLER_OUT=%~dp0releases\%TYPE_FIGHTER_RELEASE_NAME%-setup.exe"
set "NSI_FILE=%~dp0installer\type_fighter_installer.nsi"
set "ICON_FILE=%~dp0src\gfx\type-fighter-icon.ico"

if not exist "%RELEASE_DIR%\Type Fighter.exe" (
  echo Built release does not contain Type Fighter.exe:
  echo %RELEASE_DIR%
  exit /b 1
)

for /f "usebackq delims=" %%V in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content -Raw '%~dp0src\version_info.json' | ConvertFrom-Json).version"`) do set "APP_VERSION=%%V"

if "%APP_VERSION%"=="" (
  echo Failed to read app version from src\version_info.json.
  exit /b 1
)

echo Building installer for %TYPE_FIGHTER_RELEASE_NAME%

"%MAKENSIS%" ^
  /DAPP_VERSION="%APP_VERSION%" ^
  /DRELEASE_NAME="%TYPE_FIGHTER_RELEASE_NAME%" ^
  /DSOURCE_DIR="%RELEASE_DIR%" ^
  /DOUT_FILE="%INSTALLER_OUT%" ^
  /DICON_FILE="%ICON_FILE%" ^
  "%NSI_FILE%"

if errorlevel 1 (
  echo NSIS installer build failed.
  exit /b 1
)

if not exist "%INSTALLER_OUT%" (
  echo NSIS completed but installer was not found:
  echo %INSTALLER_OUT%
  exit /b 1
)

echo Installer build complete: %INSTALLER_OUT%

endlocal
