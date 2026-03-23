@echo off
echo Installing required Python packages...
pip install -r requirements.txt

echo.
echo Starting Adaptive Traffic Control System...
python adaptive_traffic_control.py

echo.
echo Program finished.
pause