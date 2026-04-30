[Setup]
AppName=wallpy
AppVersion=1.0.0
AppPublisher=wallpy
AppPublisherURL=https://github.com/GG-241/wallpy
DefaultDirName={autopf}\wallpy
DefaultGroupName=wallpy
OutputDir=..\..\dist
OutputBaseFilename=wallpy-setup-1.0.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupentry"; Description: "Launch wallpy when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\..\dist\wallpy.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\wallpy"; Filename: "{app}\wallpy.exe"
Name: "{group}\{cm:UninstallProgram,wallpy}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\wallpy"; Filename: "{app}\wallpy.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "wallpy"; ValueData: """{app}\wallpy.exe"""; Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\wallpy.exe"; Description: "{cm:LaunchProgram,wallpy}"; Flags: nowait postinstall skipifsilent
