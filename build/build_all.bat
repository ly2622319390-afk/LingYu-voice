@echo off
chcp 65001 >nul
title 智能语音输入法 - 一键构建

echo ============================================
echo   智能语音输入法 — 完整构建
echo ============================================
echo.

:: Step 1: 安装前端依赖
echo [1/5] 安装前端依赖...
cd /d "%~dp0..\frontend"
call npm install
if %errorlevel% neq 0 ( echo 前端依赖安装失败 & pause & exit /b 1 )

:: Step 2: 构建前端
echo [2/5] 构建前端...
call npm run build
if %errorlevel% neq 0 ( echo 前端构建失败 & pause & exit /b 1 )

:: Step 3: 打包 Python 后端
echo [3/5] 打包 Python 后端...
cd /d "%~dp0.."
python build/build_backend.py
if %errorlevel% neq 0 ( echo 后端打包失败 & pause & exit /b 1 )

:: Step 4: 安装 Electron 依赖
echo [4/5] 安装 Electron 依赖...
cd /d "%~dp0..\electron"
call npm install
if %errorlevel% neq 0 ( echo Electron 依赖安装失败 & pause & exit /b 1 )

:: Step 5: 构建 Electron
echo [5/5] 构建 Electron 安装包...
cd /d "%~dp0..\electron"
call npx electron-builder
if %errorlevel% neq 0 ( echo Electron 打包失败 & pause & exit /b 1 )

echo.
echo ============================================
echo   构建完成！
echo   安装包位置: electron/release/
echo ============================================
pause
