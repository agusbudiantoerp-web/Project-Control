@echo off
setlocal
rem Keep the historical launcher path but always start the repository's
rem documented root Streamlit application and root dependency manifest.
call "%~dp0..\START_AI_PROJECT_CONTROL.bat"
exit /b %errorlevel%
