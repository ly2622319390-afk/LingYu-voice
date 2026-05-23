@echo off
chcp 65001 >nul
title 智能语音输入法 v2.0

echo ============================================
echo   智能语音输入法 v2.0 — 桌面版
echo ============================================
echo.
echo   启动模式:
echo     [1] Web 版 — 浏览器打开 (http://localhost:3000)
echo     [2] 桌面版 — Electron 桌面应用
echo     [3] 仅启动后端
echo.
set /p mode="请选择 (默认 1): "
if "%mode%"=="" set mode=1

:: Start Backend (always)
echo.
echo [启动] 后端服务 (FastAPI :8000)...
cd /d "%~dp0backend"
start "语音输入法-后端" cmd /c "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak >nul

if "%mode%"=="2" goto desktop
if "%mode%"=="3" goto backend_only

:: ─── Web 模式 ───
:web
echo [启动] 前端服务 (React :3000)...
cd /d "%~dp0frontend"
start "语音输入法-前端" cmd /c "npm run dev"
echo.
echo ============================================
echo   Web 版启动完成！
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000
echo ============================================
goto end

:: ─── 桌面模式 ───
:desktop
echo [启动] Electron 桌面应用...
cd /d "%~dp0electron"
start "语音输入法-桌面" cmd /c "npx tsc && npx electron ."
echo.
echo ============================================
echo   桌面版启动完成！
echo   托盘图标出现后按 Ctrl+Space 呼出浮窗
echo   后端: http://localhost:8000
echo ============================================
goto end

:: ─── 仅后端 ───
:backend_only
echo.
echo ============================================
echo   后端已启动！
echo   API:  http://localhost:8000
echo   文档: http://localhost:8000/docs
echo ============================================
goto end

:end
echo.
echo 提示: 关闭窗口即可停止服务
echo.
pause
