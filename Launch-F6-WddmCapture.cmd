@echo off
setlocal
rem User-invoked entry: only launches UE after the Windows UAC prompt.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Tools\Performance\Start-WddmCaptureEditor.ps1"
if errorlevel 1 (
    echo.
    echo Capture launch did not complete. Read the message above.
    pause
    exit /b 1
)
endlocal
