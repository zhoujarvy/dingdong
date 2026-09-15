; 叮咚客户端 Inno Setup 打包脚本
; 编译: 运行 client\make_installer.bat，产物输出到 server\site\downloads\DingDongSetup.exe
; 安装为「当前用户」模式（无需管理员权限，适合 Win7/Win10 普通用户环境）

#define MyAppName "叮咚"
#define MyAppNameFull "叮咚消息推送客户端"
#define MyAppExeName "DingDong.exe"
#define MyAppSrc "..\DingDong\bin\Release\net6.0-windows\win-x64\publish\DingDong.exe"
#define MyOutputDir "..\..\server\downloads"
#ifndef MyAppVersion
#define MyAppVersion GetVersionNumbersString(MyAppSrc)
#endif

[Setup]
AppId={{7B3F2C1A-58D9-4E62-9A41-1C0FD3A8B2E6}
AppName={#MyAppNameFull}
AppVersion={#MyAppVersion}
AppVerName={#MyAppNameFull} {#MyAppVersion}
DefaultDirName={localappdata}\DingDong
DefaultGroupName={#MyAppNameFull}
PrivilegesRequired=lowest
OutputDir={#MyOutputDir}
OutputBaseFilename=DingDongSetup
SetupIconFile=..\DingDong\Assets\app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
CloseApplications=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
; 版本信息
VersionInfoDescription={#MyAppNameFull} 安装程序

[Languages]
Name: "chinesesimplified"; MessagesFile: "Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "runafter"; Description: "安装完成后立即运行叮咚"; Flags: unchecked

[Files]
Source: "{#MyAppSrc}"; DestDir: "{app}"; Flags: ignoreversion; AfterInstall: UpdateExeVersion

[Icons]
Name: "{group}\{#MyAppNameFull}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppNameFull}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppNameFull}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppNameFull}"; Flags: nowait postinstall skipifsilent; Tasks: runafter

[Code]
// 客户端为 .NET 6 self-contained 单文件发布，目标机器无需安装任何运行时
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure UpdateExeVersion;
begin
  // 预留：安装时版本登记（当前无需额外处理）
end;
