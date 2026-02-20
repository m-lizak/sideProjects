@echo off
:: Set the path to pythonw.exe and the script
set PYTHON_PATH=C:\Users\lizakm\AppData\Local\miniforge3\envs\geo\python.exe
set SCRIPT_PATH=C:\Users\lizakm\OneDrive - AGR-AGR\Desktop\Quick Scripts\wallpaperScraper.py

:: Check if pythonw.exe is installed
%PYTHON_PATH% --version
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not found. Please install Python and add it to the PATH.
    pause
    exit /b
)

:: Check if the script file exists
if not exist "%SCRIPT_PATH%" (
    echo The script file %SCRIPT_PATH% was not found.
    pause
    exit /b
)

:: Run the Python script without opening a command window
echo Running the Python script...
start "" %PYTHON_PATH% "%SCRIPT_PATH%"

:: Check if the script ran successfully
if %ERRORLEVEL% neq 0 (
    echo There was an error running the Python script.
    pause
    exit /b
)

echo Python script executed successfully.
exit
