@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher tidak ditemukan.
  echo Install Python 3.11 64-bit, lalu jalankan file ini kembali.
  pause
  exit /b 1
)

if not exist "%PYTHON%" (
  echo Membuat virtual environment Python 3.11...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :error
)

echo Memastikan dependensi AI Project Control tersedia...
"%PYTHON%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Membuka AI Project Control...
"%PYTHON%" -m streamlit run app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Aplikasi gagal disiapkan atau dijalankan.
echo Periksa Python 3.11, koneksi internet, dan pesan error di atas.
pause
exit /b 1
