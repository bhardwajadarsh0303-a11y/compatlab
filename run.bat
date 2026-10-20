@echo off
setlocal
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%~dp0main.py" %*
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        py "%~dp0main.py" %*
    ) else (
        echo Error: Python was not found in PATH. Please install Python 3.10 or newer.
        pause
        exit /b 1
    )
)
echo %cmdcmdline% | find /i "%~0" >nul
if not errorlevel 1 pause
endlocal
