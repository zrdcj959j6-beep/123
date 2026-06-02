@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo  🤖 AI 日报 — 一键更新内容
echo ============================================
echo.

REM 设置 DeepSeek API Key
set OPENAI_API_KEY=sk-7f243b7fdbb1451db765364db7ecc34c

echo [1/2] DeepSeek 生成最新内容...
python gen_all.py
if %errorlevel% neq 0 (
    echo [错误] 生成失败
    pause
    exit /b 1
)

echo.
echo [2/2] 打开网站...
start "" http://localhost:8080

echo.
echo ============================================
echo  完成！浏览器已打开最新内容
echo ============================================
echo.
pause
