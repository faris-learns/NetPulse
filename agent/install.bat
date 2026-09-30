@echo off
setlocal

:: Auto-detects its own folder, so it works no matter where the
:: project is cloned to on someone else's machine.
set AGENT_DIR=%~dp0

:: Finds the real Python install automatically (skips the Windows
:: Store stub some systems also register under the same name).
for /f "delims=" %%P in ('where python') do (
    set PYTHON_PATH=%%P
    goto :found
)
:found

echo Registering NetPulse Scanner as an hourly scheduled task...
schtasks /create /tn "NetPulse Scanner" /tr "\"%PYTHON_PATH%\" \"%AGENT_DIR%scanner.py\"" /sc hourly /rl highest /f

echo.
echo Done. NetPulse will now scan automatically every hour.
echo Check agent\scanner.log after it runs to confirm it worked.
pause