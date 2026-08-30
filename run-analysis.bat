@echo off
title NutriCoach T2D - statistics pipeline
cd /d "%~dp0"
echo.
echo  [1/4] Checking required packages (numpy, pandas, scipy, matplotlib) ...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo  [2/4] Simulating pilot-study data ...
python research\simulate_data.py
if errorlevel 1 goto :error
echo.
echo  [3/4] Running statistical analysis (t-test, regression, power) ...
python research\analyze.py
if errorlevel 1 goto :error
echo.
echo  [4/4] Usage report from local chat logs ...
python research\usage_analysis.py
echo.
echo  Done! Results are in research\output\  (opening folder)
start "" "%~dp0research\output"
pause
exit /b 0

:error
echo.
echo  Something went wrong - see the message above.
pause
exit /b 1
