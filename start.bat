@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo  🤖 AI 日报 — 本地启动
echo ============================================
echo.

start "" http://localhost:8080
echo 📡 网站已在浏览器打开: http://localhost:8080
echo.
echo 按 Ctrl+C 关闭服务器
echo.
python -m http.server 8080
