Unicode true
!include "MUI2.nsh"

!ifndef APP_VERSION
  !define APP_VERSION "0.0.0"
!endif

!ifndef RELEASE_NAME
  !define RELEASE_NAME "type-fighter"
!endif

!ifndef SOURCE_DIR
  !error "SOURCE_DIR must be provided"
!endif

!ifndef OUT_FILE
  !error "OUT_FILE must be provided"
!endif

!ifndef ICON_FILE
  !error "ICON_FILE must be provided"
!endif

Name "Type Fighter"
OutFile "${OUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\Type Fighter"
InstallDirRegKey HKCU "Software\Type Fighter" "InstallDir"
RequestExecutionLevel user
ShowInstDetails show
ShowUninstDetails show

Icon "${ICON_FILE}"
UninstallIcon "${ICON_FILE}"

VIProductVersion "0.1.0.0"
VIAddVersionKey "ProductName" "Type Fighter"
VIAddVersionKey "CompanyName" "Type Fighter"
VIAddVersionKey "FileDescription" "Type Fighter Installer"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "OriginalFilename" "${RELEASE_NAME}-setup.exe"

!define MUI_ABORTWARNING
!define MUI_ICON "${ICON_FILE}"
!define MUI_UNICON "${ICON_FILE}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Type Fighter" SecMain
  SetOutPath "$INSTDIR"
  File /r "${SOURCE_DIR}\*.*"

  WriteRegStr HKCU "Software\Type Fighter" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "DisplayName" "Type Fighter"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "Publisher" "Type Fighter"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "DisplayIcon" "$INSTDIR\Type Fighter.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter" "NoRepair" 1

  CreateDirectory "$SMPROGRAMS\Type Fighter"
  CreateShortcut "$SMPROGRAMS\Type Fighter\Type Fighter.lnk" "$INSTDIR\Type Fighter.exe"
  CreateShortcut "$SMPROGRAMS\Type Fighter\Uninstall Type Fighter.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\Type Fighter.lnk" "$INSTDIR\Type Fighter.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\Type Fighter.lnk"
  Delete "$SMPROGRAMS\Type Fighter\Type Fighter.lnk"
  Delete "$SMPROGRAMS\Type Fighter\Uninstall Type Fighter.lnk"
  RMDir "$SMPROGRAMS\Type Fighter"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter"
  DeleteRegKey HKCU "Software\Type Fighter"

  RMDir /r "$INSTDIR"
SectionEnd
