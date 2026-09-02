#define MyAppName "Laxmi Electricals Billing"
#define MyAppVersion "1.1.0"
#define MyAppExeName "LaxmiElectricalsBilling.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=release
OutputBaseFilename=LaxmiElectricalsBillingSetup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\app.ico

[Files]
; Copy the main application files
Source: "..\dist\LaxmiElectricalsBilling\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Copy the icon file explicitly so shortcuts can use it reliably
Source: "..\assets\app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Point IconFilename directly to the .ico file, NOT the .exe
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
