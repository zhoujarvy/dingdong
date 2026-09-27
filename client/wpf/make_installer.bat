@echo off
rem ============================================
rem  DingDong client - one-click installer build
rem  Output: server\downloads\DingDongSetup.exe (served by the website)
rem
rem  NOTE: keep this file ASCII-only and CRLF, or cmd.exe may
rem        fail to parse it under non-UTF8 code pages (GBK etc).
rem ============================================
setlocal
cd /d %~dp0

rem Locate Inno Setup 6 (ISCC.exe)
set ISCC=
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
  echo [ERROR] Inno Setup 6 not found. Please install ISCC.exe first.
  pause & exit /b 1
)

echo [1/2] Publishing client (.NET 6 self-contained single file)...
dotnet publish DingDong\DingDong.csproj -c Release -v q
if errorlevel 1 ( echo [ERROR] Build failed & pause & exit /b 1 )

echo [2/2] Building installer...
"%ISCC%" "installer\DingDong.iss"
if errorlevel 1 ( echo [ERROR] Installer build failed & pause & exit /b 1 )

rem Write version info for the website download page
powershell -NoProfile -Command "$v=(Get-Item '..\..\server\downloads\DingDongSetup.exe').VersionInfo.ProductVersion; Set-Content -Path '..\..\server\downloads\version.txt' -Value $v -Encoding ascii"

echo.
echo ============================================
echo  Done: %~dp0..\..\server\downloads\DingDongSetup.exe
echo  The installer is ready in the website download folder.
echo ============================================
pause
