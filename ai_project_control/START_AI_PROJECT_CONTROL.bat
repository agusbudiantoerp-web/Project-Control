@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher tidak ditemukan.
  echo Install Python 3.11, lalu jalankan file ini kembali.
  pause
  exit /b 1
)

if not exist "%PYTHON%" (
  echo Membuat lingkungan Python 3.11 untuk aplikasi V1...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :error
)

echo Memeriksa dependensi aplikasi V1...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :error
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Membuka aplikasi AI Project Control V1...
"%PYTHON%" -m streamlit run app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Terjadi masalah saat menyiapkan atau menjalankan aplikasi V1.
echo Pastikan Python 3.11 terpasang dan koneksi internet tersedia.
pause
exit /b 1
