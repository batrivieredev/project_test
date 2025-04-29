@echo off
echo DJ Online Studio - Quick Start Script
echo ====================================

echo Checking Python version...
python --version

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install -r requirements.txt

echo Creating directories...
if not exist instance mkdir instance
if not exist instance\uploads mkdir instance\uploads
if not exist migrations mkdir migrations

echo Setting environment variables...
set FLASK_APP=run.py
set FLASK_ENV=development

echo Initializing database...
if exist instance\dj_studio.db (
    echo Removing old database...
    del instance\dj_studio.db
)

flask db init
flask db migrate -m "Initial migration"
flask db upgrade

echo.
echo Setup complete! Start the application with:
echo python run.py
echo.
echo Then visit http://localhost:5000 in your browser
pause
