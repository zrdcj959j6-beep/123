@echo off
chcp 65001 >nul
REM ============================================
REM  AI 日报 — 每日自动更新 + 推送到 Gitee
REM  配合 Windows 任务计划程序使用
REM ============================================

cd /d "%~dp0"

echo.
echo ========================================
echo  AI 日报更新 — %date% %time%
echo ========================================
echo.

REM 检查 OpenAI API Key
if "%OPENAI_API_KEY%"=="" (
    echo [警告] OPENAI_API_KEY 未设置！
    echo 请在系统环境变量中添加 OPENAI_API_KEY=sk-xxx
    echo 或在命令行执行: set OPENAI_API_KEY=你的Key
    echo.
)

echo [1/3] DeepSeek 一键生成全部内容...
python gen_all.py
if %errorlevel% neq 0 (
    echo [错误] gen_all.py 执行失败
    pause
    exit /b 1
)

echo.
echo [2/3] 提交到 Git...
git add news.json hot_news.json learning.json daily.json
git commit -m "🤖 自动更新 — %date% %time%" 2>&1
if %errorlevel% neq 0 (
    echo [提示] 没有新的更改需要提交
    echo.
    echo [3/3] 跳过推送
    goto :done
)

echo.
echo [3/3] 推送到 Gitee...
git push
if %errorlevel% neq 0 (
    echo [错误] 推送失败，请检查网络或 Git 配置
    pause
    exit /b 1
)

:done
echo.
echo ========================================
echo  完成！请去 Gitee Pages 点击"更新"部署
echo  网站地址: https://你的用户名.gitee.io/仓库名
echo ========================================
echo.

REM 3 秒后自动关闭
timeout /t 3 >nul
exit /b 0
