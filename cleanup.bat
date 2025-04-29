@echo off
echo Cleaning up duplicate and unnecessary files...

:: Remove old JavaScript files
if exist js\ rmdir /s /q js

:: Remove old CSS and HTML files from root
if exist styles.css del styles.css
if exist index.html del index.html
if exist script.js del script.js

:: Remove Python cache files
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul

:: Remove test coverage files if they exist
if exist htmlcov\ rmdir /s /q htmlcov
if exist .coverage del .coverage

echo Cleanup completed!
pause
