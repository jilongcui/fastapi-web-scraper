@echo off
chcp 65001 >nul
echo ================================================
echo FastAPI Web Scraper Server (Windows)
echo ================================================
echo 启动服务器... 使用 Ctrl+C 来停止
echo 服务器地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo ================================================

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请确保Python已安装并在PATH中
    pause
    exit /b 1
)

REM 启动服务器
python run_server.py

echo.
echo 服务器已停止
pause