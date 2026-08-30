@echo off
title NutriCoach T2D
cd /d "%~dp0"
echo.
echo  NutriCoach T2D - research prototype
echo  Opening http://localhost:8765 ...
echo  (close this window or press Ctrl+C to stop)
echo.
start /b "" cmd /c "timeout /t 2 /nobreak >nul & start "" http://localhost:8765"
python app.py
pause
