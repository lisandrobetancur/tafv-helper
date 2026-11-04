; Instalador de Windows (Inno Setup 6, gratis). Lo llama escritorio/construir.py con:
;   /DVersion=...  /DOrigen=<carpeta que armó PyInstaller>  /DIcono=<icono.ico>
; Se instala para el usuario actual (no pide permisos de administrador). Al desinstalar NO se borra la
; biblioteca (está en %APPDATA%\Biblioteca de Estudio): así una reinstalación conserva los datos.

#ifndef Version
  #define Version "1.0"
#endif

[Setup]
AppId={{6E0B7C1A-5D3F-4C2B-9A8E-2F1D4B7C9E10}
AppName=Biblioteca de Estudio
AppVersion={#Version}
AppPublisher=Biblioteca de Estudio
DefaultDirName={localappdata}\Programs\Biblioteca de Estudio
DefaultGroupName=Biblioteca de Estudio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=Instalador-Biblioteca-de-Estudio
SetupIconFile={#Icono}
UninstallDisplayIcon={app}\Biblioteca de Estudio.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#Origen}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Biblioteca de Estudio"; Filename: "{app}\Biblioteca de Estudio.exe"
Name: "{autodesktop}\Biblioteca de Estudio"; Filename: "{app}\Biblioteca de Estudio.exe"; Tasks: escritorio

[Run]
Filename: "{app}\Biblioteca de Estudio.exe"; Description: "Abrir la Biblioteca de Estudio"; Flags: nowait postinstall skipifsilent
