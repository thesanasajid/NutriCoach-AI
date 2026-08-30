@echo off
title NutriCoach T2D - build the desktop app
cd /d "%~dp0"
echo.
echo  Building NutriCoach.exe (standalone Windows app) ...
echo.
echo  [1/3] Making sure PyInstaller is installed ...
python -m pip install pyinstaller --quiet --disable-pip-version-check
if errorlevel 1 goto :error

echo  [2/3] Stopping any running NutriCoach instance (it would lock the file) ...
taskkill /IM NutriCoach.exe /F >nul 2>&1

echo  [3/3] Packaging (this takes a minute) ...
python -m PyInstaller --onefile --noconsole --name NutriCoach ^
  --icon "%~dp0icon.ico" --splash "%~dp0splash.png" ^
  --add-data "%~dp0data\foods.json;data" ^
  --add-data "%~dp0data\guidelines.json;data" ^
  --add-data "%~dp0web\index.html;web" ^
  --distpath "%~dp0" --workpath "%~dp0build" --specpath "%~dp0build" "%~dp0app.py"
if errorlevel 1 goto :error

rmdir /s /q "%~dp0build" >nul 2>&1
echo.
echo  Done! NutriCoach.exe is ready in this folder.
pause
exit /b 0

:error
echo.
echo  Build failed - see the message above.
pause
exit /b 1
