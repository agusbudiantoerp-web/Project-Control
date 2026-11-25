# Panduan Instalasi Windows — AI Project Control

## Tujuan

Panduan ini menjalankan aplikasi secara lokal pada Windows untuk evaluasi internal. Ini bukan panduan deployment multi-user/produksi.

## Prasyarat

- Windows 10/11
- Python 3.11 (64-bit) tersedia dari python.org
- Git for Windows
- Koneksi internet untuk instalasi dependensi

## 1. Ambil kode

Buka PowerShell, lalu jalankan:

```powershell
git clone --branch ai-project-control-integration https://github.com/agusbudiantoerp-web/Project-Control.git
cd Project-Control
```

Jika folder sudah ada, masuk ke folder tersebut dan perbarui branch:

```powershell
git switch ai-project-control-integration
git pull
```

## 2. Buat virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Jika PowerShell memblokir aktivasi script, jalankan perintah aktivasi melalui Command Prompt:

```bat
.venv\Scripts\activate.bat
```

## 3. Jalankan aplikasi

```powershell
python -m streamlit run app.py
```

Alternatif untuk penggunaan berikutnya: klik dua kali `START_AI_PROJECT_CONTROL.bat` di folder utama repository. Launcher V1 di folder `ai_project_control` tetap tersedia untuk kompatibilitas dan menjalankan aplikasi lama dengan database terpisah; data V1 tidak otomatis tersinkron ke workspace utama. Browser biasanya terbuka otomatis. Jika tidak, salin alamat lokal yang ditampilkan Streamlit ke browser.

Halaman multipage tersedia melalui navigasi sidebar, termasuk:
- Workspace dashboard
- Dated Cash Flow Forecast
- EVM & Cost Forecast Control
- Telegram Executive Report
- Saved Project Financial Control
- Saved Portfolio COO Executive Cockpit
- Workspace Backup & Import History
- Primavera P6 XER & Drawing-to-BOQ Intake

## 4. Telegram (opsional)

Untuk mengaktifkan pengiriman Telegram, atur environment variables pada terminal sebelum menjalankan Streamlit:

```powershell
$env:TELEGRAM_BOT_TOKEN = "ISI_TOKEN_BOT_DI_MESIN_LOKAL"
$env:TELEGRAM_CHAT_ID = "ISI_CHAT_ID_TUJUAN"
python -m streamlit run app.py
```

Jangan menaruh token asli di file kode, commit, screenshot, atau pesan. Untuk hosting, gunakan secret manager platform hosting. Mulai pengujian Telegram dari private chat.

## 5. Gemini drawing intake (opsional)

Untuk menggunakan analisis gambar, atur `GEMINI_API_KEY` sebagai environment variable Windows atau Streamlit secret. Contoh untuk sesi PowerShell saat ini:

```powershell
$env:GEMINI_API_KEY = "ISI_API_KEY_GEMINI_DI_MESIN_LOKAL"
python -m streamlit run app.py
```

Halaman PDF menampilkan preview lokal terlebih dahulu. Gambar hanya dikirim ke Google Gemini setelah pengguna mencentang persetujuan dan menekan tombol analisis. Jangan mengirim gambar kontrak/proyek rahasia sebelum disetujui pemilik data.

## 6. Penyimpanan data

Workspace SQLite bersifat lokal dan tidak otomatis tersinkron ke komputer lain. Simpan backup terenkripsi di lokasi aman. Jangan menempatkan database lokal pada folder publik atau repository.

## 7. Batas penggunaan

- Gunakan data contoh hanya untuk mempelajari tampilan.
- Validasi data proyek, periode, satuan, mata uang, PV/EV/AC/BAC dan transaksi terhadap sumber resmi.
- EAC, Monte Carlo, early warning dan recovery planner adalah alat bantu analisis; bukan persetujuan perubahan baseline atau instruksi otomatis ke lapangan.
- Telegram mengirim pesan hanya setelah pengguna menekan tombol kirim dan memberi konfirmasi.
- Jangan gunakan untuk data rahasia perusahaan sebelum kontrol akses, backup, keamanan jaringan dan kebijakan data disetujui.

## 8. Belum menjadi deployment produksi

Sebelum digunakan banyak pengguna, organisasi harus menetapkan autentikasi, role-based access, database server bersama, enkripsi, audit trail, backup/restore, pemantauan, secret management, retensi data dan prosedur pemulihan bencana. Jalankan pengujian penerimaan dengan data referensi yang sudah disetujui pemilik proyek.
