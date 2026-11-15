@echo off
setlocal
cd /d "c:\Users\KRISHNA\Desktop\agent"
if not exist "logs" mkdir logs
echo =========================================================================== >> logs\automation.log
echo [AUTOMATION RUN] Starting Daily Algorithm Publisher at %DATE% %TIME% >> logs\automation.log
echo =========================================================================== >> logs\automation.log
".venv\Scripts\python.exe" app\autonomous\daily_algorithm_publisher.py >> logs\automation.log 2>&1
echo [AUTOMATION RUN] Finished with exit code %ERRORLEVEL% at %DATE% %TIME% >> logs\automation.log
