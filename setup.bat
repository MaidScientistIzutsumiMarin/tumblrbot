@echo off
timeout /t 3
echo We are going to install the necessary packages for the project
echo It is assumed that you already have Python 3.11, pip, and virtualenv installed.
echo If you don't have them installed, please install them before running this script.
set /p answer=Do you want to continue? (y/n): 
if /i "%answer%"=="y" (
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
    echo Installation completed
) else (
    echo Installation aborted
)
