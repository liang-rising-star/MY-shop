@echo off
chcp 65001 >nul
echo ====================================
echo    MY-Shop 启动中...
echo ====================================
echo.
echo 访问地址: http://localhost:8080
echo 管理后台: http://localhost:8080/admin
echo.
echo 按 Ctrl+C 停止服务
echo.

python main.py

pause
