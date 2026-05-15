@echo off
chcp 65001 >nul
title Garment Tracker - Setup
color 0A
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Garment Order Tracking System                  ║
echo  ║   Tasniah Fabrics Ltd · Masco Group              ║
echo  ║   Setup - Run only once                        ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Installing libraries...
python -m pip install --upgrade pip --quiet
python -m pip install pdfplumber openpyxl pandas fpdf tkcalendar matplotlib Pillow babel --quiet
if %errorlevel% neq 0 (
    echo  [ERROR] Install failed!
    pause & exit /b 1
)
echo.
echo  ✓ Setup complete! Run with run.bat.
echo  Default login:  admin / admin123
echo.
pause
