@echo off
chcp 65001 >nul
title 智能语音输入法 v2.0 — 行业词库版

echo ============================================
echo   智能语音输入法 — 行业专业词库版
echo ============================================
echo.
echo   启动模式:
echo     [1] 完整模式 (后端 + Web 前端)
echo     [2] 仅启动后端
echo     [3] 初始化行业词库 (首次使用)
echo.
set /p mode="请选择 (默认 1): "
if "%mode%"=="" set mode=1
if "%mode%"=="3" goto seed

:: Start Backend (always)
echo.
echo [启动] 后端服务 (FastAPI :8000)...
cd /d "%~dp0backend"
start "语音输入法-后端" cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

if "%mode%"=="2" goto backend_only

:: Web 前端
echo [启动] 前端服务 (React :3000)...
cd /d "%~dp0frontend"
start "语音输入法-前端" cmd /c "npm run dev"
echo.
echo ============================================
echo   启动完成！
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000
echo   行业词库 API: http://localhost:8000/api/industry-lexicon/industries
echo   文档: http://localhost:8000/docs
echo ============================================
goto end

:backend_only
echo.
echo ============================================
echo   后端已启动！
echo   API:  http://localhost:8000
echo   文档: http://localhost:8000/docs
echo ============================================
goto end

:seed
echo.
echo [初始化] 正在导入行业词库数据...
cd /d "%~dp0backend"
python -c "from database.industry_lexicon_db import ensure_seeded; from database.seed_industry_words import get_word_count; c=ensure_seeded(); print(f'完成: 共 {c} 条词条'); [print(f'  {k}: {v}条') for k,v in get_word_count().items()]"
echo.
echo ============================================
echo   行业词库初始化完成！
echo   共 9 个行业分类
echo ============================================
pause
goto end

:end
echo.
echo 提示: 关闭窗口即可停止服务
echo.
pause
