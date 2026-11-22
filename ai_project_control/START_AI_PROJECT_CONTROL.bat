@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher tidak ditemukan.
  echo Install Python 3.11 atau lebih baru, lalu jalankan file ini kembali.
  pause
  exit /b 1
)

if not exist ".venv\\Scripts\\python.exe" (
  echo Membuat lingkungan Python untuk AI Project Control...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :error
)

echo Memeriksa dependensi aplikasi...
".venv\\Scripts\\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\\Scripts\\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Membuka AI Project Control di browser...
".venv\\Scripts\\python.exe" -m streamlit run app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Terjadi masalah saat menyiapkan atau menjalankan aplikasi.
echo Periksa pesan di atas, koneksi internet, dan instalasi Python 3.11.
pause
exit /b 1
