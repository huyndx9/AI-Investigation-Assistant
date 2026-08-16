@echo off
title AI Investigation Assistant
cd /d "%~dp0"

echo Starting AI Investigation Assistant...
echo This window shows the server log - keep it open while using the app.
echo Your browser will open automatically at http://localhost:7860
echo.
echo To stop the app, close this window or press Ctrl+C.
echo.

python app.py

echo.
echo The app has stopped. Press any key to close this window.
pause >nul
