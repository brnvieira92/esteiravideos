#ifndef AppVersion
  #define AppVersion "0.4.6"
#endif
[Setup]
AppId={{27B6B310-68B9-4DC1-AF74-7835B270B9CE}
AppName=EsteiraVídeos
AppVersion={#AppVersion}
AppPublisher=EsteiraVídeos
DefaultDirName={localappdata}\Programs\esteira-videos
DefaultGroupName=EsteiraVídeos
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=EsteiraVideos-Setup
SetupIconFile=app.ico
UninstallDisplayIcon={app}\EsteiraVideos.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
InfoBeforeFile=INSTALL-NOTES.txt
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; Flags: unchecked
[Files]
Source: "..\dist\EsteiraVideos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "INSTALL-NOTES.txt"; DestDir: "{app}"
[Icons]
Name: "{group}\EsteiraVídeos"; Filename: "{app}\EsteiraVideos.exe"; WorkingDir: "{app}"
Name: "{group}\EsteiraVídeos — acesso pelo Wi-Fi"; Filename: "{app}\EsteiraVideos.exe"; Parameters: "--lan --https --open-browser"; WorkingDir: "{app}"
Name: "{group}\Desinstalar EsteiraVídeos"; Filename: "{uninstallexe}"
Name: "{autodesktop}\EsteiraVídeos"; Filename: "{app}\EsteiraVideos.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\EsteiraVideos.exe"; Description: "Abrir EsteiraVídeos"; Flags: nowait postinstall skipifsilent
; No UninstallDelete: projects, originals and database are intentionally retained.
