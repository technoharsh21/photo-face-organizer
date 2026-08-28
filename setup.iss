; Inno Setup Script for Photo Face Organizer (Windows 11 / 64-bit Installer)
; Configured for native 64-bit Windows installation and SmartApp Control compatibility

[Setup]
AppId={{C6A7B8E9-4F2A-4D3B-9C1E-8F7A6B5C4D3E}}
AppName=Photo Face Organizer
AppVersion=1.0.0
AppPublisher=Photo Face Organizer Team
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultDirName={autopf}\Photo Face Organizer
DefaultGroupName=Photo Face Organizer
OutputDir=Output
OutputBaseFilename=PhotoFaceOrganizer_Setup
SetupIconFile=icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\PhotoFaceOrganizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Photo Face Organizer"; Filename: "{app}\PhotoFaceOrganizer.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\{cm:UninstallProgram,Photo Face Organizer}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Photo Face Organizer"; Filename: "{app}\PhotoFaceOrganizer.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\PhotoFaceOrganizer.exe"; Description: "{cm:LaunchProgram,Photo Face Organizer}"; Flags: nowait postinstall skipifsilent
