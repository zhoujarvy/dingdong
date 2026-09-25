@echo off
rem ============================================
rem  叮咚客户端 - 一键打包安装程序
rem  产物: server\downloads\DingDongSetup.exe（供官网下载）
rem ============================================
setlocal
cd /d %~dp0

rem 定位 Inno Setup 6（ISCC.exe）
set ISCC=
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
  echo [错误] 未找到 Inno Setup 6，请先安装 ISCC.exe。
  pause & exit /b 1
)

echo [1/2] 发布客户端（.NET 6 自包含单文件，目标机无需安装运行时）...
dotnet publish DingDong\DingDong.csproj -c Release -v q
if errorlevel 1 ( echo [错误] 编译失败 & pause & exit /b 1 )

echo [2/2] 生成安装包...
"%ISCC%" "installer\DingDong.iss"
if errorlevel 1 ( echo [错误] 打包失败 & pause & exit /b 1 )

rem 输出版本信息，供官网展示
powershell -NoProfile -Command "$v=(Get-Item '..\..\server\downloads\DingDongSetup.exe').VersionInfo.ProductVersion; Set-Content -Path '..\..\server\downloads\version.txt' -Value $v -Encoding ascii"

echo.
echo ============================================
echo  打包完成: %~dp0..\..\server\downloads\DingDongSetup.exe
echo  该文件已就位于官网下载目录。
echo ============================================
pause
