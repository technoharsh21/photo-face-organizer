; Inno Setup Script for Photo Face Organizer (Windows 11 / 64-bit Standard Admin Installer)

[Setup]
AppId={{C6A7B8E9-4F2A-4D3B-9C1E-8F7A6B5C4D3E}}
AppName=Photo Face Organizer
AppVersion=1.0.0
AppPublisher=Photo Face Organizer Team
AppPublisherURL=https://github.com/technoharsh21/photo-face-organizer
AppSupportURL=https://github.com/technoharsh21/photo-face-organizer/issues
AppUpdatesURL=https://github.com/technoharsh21/photo-face-organizer/releases
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
PrivilegesRequiredOverridesAllowed=commandline dialog
VersionInfoVersion=1.0.0.0
VersionInfoCompany=Photo Face Organizer Team
VersionInfoDescription=Photo Face Organizer Desktop Installer
VersionInfoCopyright=Copyright (C) 2026 Photo Face Organizer Team
VersionInfoProductName=Photo Face Organizer
VersionInfoProductVersion=1.0.0.0

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
