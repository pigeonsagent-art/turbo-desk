@echo off
title PCPolish - Installing Dependencies
echo.
echo  ================================================
echo    PCPolish - Installing Dependencies
echo  ================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

echo  [OK] Python found
echo.
echo  Installing required packages...
echo.

pip install PyQt6>=6.4.0 psutil>=5.9.0 watchdog>=3.0.0 schedule>=1.2.0 requests>=2.28.0 pywin32>=305

echo.
if %errorlevel% equ 0 (
    echo  ================================================
    echo    Installation complete!
    echo    Run PCPolish.bat to start the application.
    echo  ================================================
) else (
    echo  [ERROR] Some packages failed to install.
    echo  Try running: pip install -r requirements.txt
)
echo.
pause
