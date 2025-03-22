@echo off
echo FL Studio MCP Script Installer
echo ============================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

echo Checking for FL Studio installation...

:: Try to find FL Studio in Program Files
set "FL_STUDIO_DIR=C:\Program Files\Image-Line\FL Studio 20"
if not exist "%FL_STUDIO_DIR%" (
    set "FL_STUDIO_DIR=C:\Program Files\Image-Line\FL Studio"
)

if not exist "%FL_STUDIO_DIR%" (
    echo FL Studio installation not found in Program Files.
    echo Checking user directory...
    
    set "FL_STUDIO_DIR=%USERPROFILE%\Documents\Image-Line\FL Studio"
    
    if not exist "%FL_STUDIO_DIR%" (
        echo FL Studio installation not found.
        echo Please enter the path to your FL Studio installation:
        set /p FL_STUDIO_DIR="FL Studio path: "
    )
)

echo Using FL Studio directory: %FL_STUDIO_DIR%

:: Check for MIDI scripts directory
set "MIDI_SCRIPTS_DIR=%FL_STUDIO_DIR%\Shared\Python\Lib\site-packages\flmcp"
if not exist "%MIDI_SCRIPTS_DIR%" (
    echo MIDI scripts directory not found.
    echo Creating directory: %MIDI_SCRIPTS_DIR%
    mkdir "%MIDI_SCRIPTS_DIR%"
)

:: Create the script directory
set "SCRIPT_DIR=%MIDI_SCRIPTS_DIR%\FlStudioMCP_Remote_Script"
if exist "%SCRIPT_DIR%" (
    echo Script directory already exists. Removing old files...
    rd /s /q "%SCRIPT_DIR%"
)

echo Creating script directory: %SCRIPT_DIR%
mkdir "%SCRIPT_DIR%"

:: Copy the script files
echo Copying script files...
xcopy /s /y "%~dp0FlStudioMCP_Remote_Script\*.*" "%SCRIPT_DIR%\"

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Start FL Studio
echo 2. Go to Options ^> MIDI Settings
echo 3. In the "Controller type" dropdown, select "FL Studio MCP"
echo 4. Restart FL Studio
echo.
echo After FL Studio restarts, run the test_connection.py script to verify
echo that the server is running properly.
echo.

pause
