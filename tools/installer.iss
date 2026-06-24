; 싹싹김치 캡처 Inno Setup 인스톨러
; tools/package.py 가 자동으로 컴파일.
; 수동 빌드: "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" tools\installer.iss

#define MyAppName "싹싹김치 캡처"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "싹싹김치"
#define MyAppURL "https://github.com/gyqls051/ssakssak-capture"
#define MyAppExeName "싹싹김치 캡처.exe"
#define SourceDir "..\dist\싹싹김치 캡처"

[Setup]
AppId={{B7A4F5E2-9C2D-4B1A-8E3F-1F2A3B4C5D6E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={userpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=Setup_SsakKimchiCapture_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=
UninstallDisplayIcon={app}\{#MyAppExeName}
; LGPL 의무 충족 + 사용자 라이선스 인지 위해 동의 화면 표시
LicenseFile=..\LICENSE

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"; Flags: unchecked
Name: "autostart"; Description: "Windows 시작 시 자동 실행"; GroupDescription: "추가 작업:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 라이선스/문서 — LGPL 의무 충족 (번들된 ffmpeg, PySide6 등의 라이선스 텍스트 보존)
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\제거"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "지금 실행"; Flags: nowait postinstall skipifsilent
