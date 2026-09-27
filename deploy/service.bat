@echo off
rem ============================================================
rem  DingDong server - NSSM Windows service management script
rem
rem  Usage:
rem    service.bat install    Install and start the service (auto start on boot)
rem    service.bat uninstall  Stop and remove the service
rem    service.bat restart    Restart the service (after code updates)
rem
rem  Prerequisites:
rem    1. NSSM downloaded, nssm.exe in PATH or in this directory
rem       Download: https://nssm.cc/download
rem    2. venv and dependencies installed (see deploy/offline guide)
rem
rem  NOTE: keep this file ASCII-only and CRLF, or cmd.exe may
rem        fail to parse it under non-UTF8 code pages (GBK etc).
rem ============================================================
setlocal
rem ---- Adjust these three lines to your deployment path ----
set SERVICE_NAME=DingDongServer
set APP_DIR=D:\dingdong\server
set PYTHON_EXE=%APP_DIR%\venv\Scripts\python.exe

rem Locate nssm.exe
set NSSM=nssm
where nssm >nul 2>&1 || set NSSM=%~dp0nssm.exe
if not exist "%NSSM%" (
  echo [ERROR] nssm.exe not found. Put it in this directory or add to PATH.
  pause & exit /b 1
)

if "%1"=="install"   goto :install
if "%1"=="uninstall" goto :uninstall
if "%1"=="restart"   goto :restart
echo Usage: service.bat install ^| uninstall ^| restart
exit /b 1

:install
"%NSSM%" install %SERVICE_NAME% "%PYTHON_EXE%" "run.py"
"%NSSM%" set %SERVICE_NAME% AppDirectory "%APP_DIR%"
"%NSSM%" set %SERVICE_NAME% AppStdout "%APP_DIR%\logs\service.log"
"%NSSM%" set %SERVICE_NAME% AppStderr "%APP_DIR%\logs\error.log"
"%NSSM%" set %SERVICE_NAME% AppRotateFiles 1
"%NSSM%" set %SERVICE_NAME% AppRotateBytes 5242880
"%NSSM%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM%" start %SERVICE_NAME%
echo Service %SERVICE_NAME% installed and started. Manage: nssm status/restart/stop %SERVICE_NAME%
pause & exit /b 0

:uninstall
"%NSSM%" stop %SERVICE_NAME%
"%NSSM%" remove %SERVICE_NAME% confirm
echo Service removed.
pause & exit /b 0

:restart
"%NSSM%" restart %SERVICE_NAME%
echo Service restarted.
pause & exit /b 0
