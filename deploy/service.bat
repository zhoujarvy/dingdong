@echo off
rem ============================================================
rem  叮咚服务端 · NSSM Windows 服务管理脚本
rem  用法:
rem    service.bat install    安装并启动服务（开机自启）
rem    service.bat uninstall  停止并卸载服务
rem    service.bat restart    重启服务（更新代码后执行）
rem  前置:
rem    1. NSSM 已下载，nssm.exe 在 PATH 中或与本脚本同目录
rem       下载: https://nssm.cc/download
rem    2. 已按 deploy/部署说明.md 完成 venv 与依赖安装
rem ============================================================
setlocal
rem ---- 按实际部署路径修改以下三行 ----
set SERVICE_NAME=DingDongServer
set APP_DIR=D:\dingdong\server
set PYTHON_EXE=%APP_DIR%\venv\Scripts\python.exe

rem 定位 nssm.exe
set NSSM=nssm
where nssm >nul 2>&1 || set NSSM=%~dp0nssm.exe
if not exist "%NSSM%" (
  echo [错误] 未找到 nssm.exe，请将其放入本目录或加入 PATH。
  pause & exit /b 1
)

if "%1"=="install"   goto :install
if "%1"=="uninstall" goto :uninstall
if "%1"=="restart"   goto :restart
echo 用法: service.bat install ^| uninstall ^| restart
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
echo 服务 %SERVICE_NAME% 已安装并启动。管理: nssm status/restart/stop %SERVICE_NAME%
pause & exit /b 0

:uninstall
"%NSSM%" stop %SERVICE_NAME%
"%NSSM%" remove %SERVICE_NAME% confirm
echo 服务已卸载。
pause & exit /b 0

:restart
"%NSSM%" restart %SERVICE_NAME%
echo 服务已重启。
pause & exit /b 0
