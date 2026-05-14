@echo off
chcp 65001 >nul
title Garment Tracker - Starting...
color 0A

echo Checking dependencies...
python -c "import pdfplumber, openpyxl, pandas, fpdf, tkcalendar, matplotlib" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Installing required libraries for the first time...
    echo This may take a minute. Please wait...
    pip install pdfplumber openpyxl pandas fpdf tkcalendar matplotlib --quiet
    if %errorlevel% neq 0 (
        color 0C
        echo.
        echo [ERROR] Failed to install dependencies! 
        echo Please ensure Python is installed and added to PATH.
        pause
        exit /b 1
    )
)

start /b pythonw garment_tracker.py
exit
