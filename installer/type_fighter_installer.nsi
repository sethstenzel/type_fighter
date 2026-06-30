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
  ; If a previous Type Fighter is installed in this folder, run its uninstaller
  ; first so we start from a clean directory (and don't trip the not-empty guard
  ; below). Runs silently and in-place so we can wait for it to finish.
  IfFileExists "$INSTDIR\Uninstall.exe" 0 no_previous_uninstaller
    DetailPrint "Removing the previous Type Fighter installation..."
    ExecWait '"$INSTDIR\Uninstall.exe" /S _?=$INSTDIR'
    ; A running uninstaller cannot delete itself; remove the leftover copy so the
    ; folder is empty for the fresh install.
    Delete "$INSTDIR\Uninstall.exe"
  no_previous_uninstaller:

  ; Refuse to install into an existing, non-empty folder. This guarantees the
  ; uninstaller's recursive delete can only ever remove files we created, never
  ; a user's pre-existing data (e.g. if they point InstallDir at Documents).
  FindFirst $0 $1 "$INSTDIR\*.*"
  check_dir_entry:
    StrCmp $1 "" dir_is_empty
    StrCmp $1 "." dir_next_entry
    StrCmp $1 ".." dir_next_entry
    FindClose $0
    MessageBox MB_OK|MB_ICONSTOP "The selected folder is not empty:$\n$INSTDIR$\n$\nPlease choose a new or empty folder. This protects your files: uninstalling Type Fighter removes everything in its install folder."
    Abort
  dir_next_entry:
    FindNext $0 $1
    Goto check_dir_entry
  dir_is_empty:
  FindClose $0

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
  ; Only recursively delete the install folder if it actually looks like a
  ; Type Fighter installation. Prevents wiping an unrelated folder if the
  ; uninstaller is ever pointed somewhere unexpected.
  IfFileExists "$INSTDIR\Type Fighter.exe" tf_install_confirmed 0
    MessageBox MB_OK|MB_ICONEXCLAMATION "This folder does not look like a Type Fighter installation:$\n$INSTDIR$\n$\nAborting to avoid deleting your files."
    Abort
  tf_install_confirmed:

  Delete "$DESKTOP\Type Fighter.lnk"
  Delete "$SMPROGRAMS\Type Fighter\Type Fighter.lnk"
  Delete "$SMPROGRAMS\Type Fighter\Uninstall Type Fighter.lnk"
  RMDir "$SMPROGRAMS\Type Fighter"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Type Fighter"
  DeleteRegKey HKCU "Software\Type Fighter"

  RMDir /r "$INSTDIR"
SectionEnd
