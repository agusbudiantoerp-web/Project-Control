# Panduan Pengguna AI Project Control

Panduan ini untuk menjalankan aplikasi lokal di Windows. Pengujian sistem menyeluruh dilakukan setelah tahap implementasi dinyatakan selesai.

## A. Persiapan

1. Pastikan Python 3.11 sudah terpasang.
2. Clone repository dan checkout branch `ai-project-control-integration`.
3. Buka folder repository di PowerShell.

```powershell
git clone https://github.com/agusbudiantoerp-web/Project-Control.git
cd Project-Control
git checkout ai-project-control-integration
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jika PowerShell memblokir aktivasi virtual environment, jalankan perintah berikut hanya untuk sesi terminal saat ini, lalu ulangi aktivasi:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## B. Menjalankan aplikasi

```powershell
streamlit run app.py
```

Browser biasanya terbuka otomatis. Jika tidak, buka alamat lokal yang ditampilkan Streamlit di terminal.

Database lokal dibuat pada `.project_control/project_control.sqlite3`. Jangan menghapus folder tersebut jika data proyek masih diperlukan. Buat backup berkala dan jangan unggah database yang berisi informasi proyek rahasia ke repository publik.

## C. Urutan penggunaan

1. Buka **Project Workspace** dan masukkan Project ID.
2. Siapkan serta impor dataset proyek sesuai tabel yang tersedia.
3. Periksa validasi data, peringatan, satuan, tanggal pelaporan, dan mata uang.
4. Lengkapi baseline biaya, jadwal, aktivitas, predecessor, resource, WBS dan risk register.
5. Periksa EVM, resource loading, cost forecast, schedule forecast dan Monte Carlo.
6. Periksa Risk Exposure Matrix dan rekomendasi mitigasi.
7. Bandingkan recovery scenario dan validasi asumsi produktivitas tambahan.
8. Catat executive actions beserta owner, due date, status dan bukti.
9. Gunakan Portfolio Command Center untuk melihat ringkasan lintas proyek.
10. Simpan snapshot KPI historis secara berkala. Setelah tersedia minimal tiga tanggal untuk suatu indikator, jalankan early warning dari histori tersimpan.
11. Ekspor laporan untuk review dan persetujuan manajemen.

## D. Data historis

Simpan satu snapshot aktual per proyek per tanggal pelaporan. Gunakan definisi SPI, CPI, risk score, planned value, earned value, actual cost dan produktivitas yang konsisten. Jangan mencampur mata uang dalam satu pasangan data pembelajaran.

Dataset pembelajaran memasangkan snapshot saat ini dengan snapshot berikutnya pada proyek yang sama. Data yang berurutan dapat saling berkaitan; validasi model masa depan harus mempertimbangkan pemisahan berdasarkan waktu dan proyek.

## E. Batasan dan keselamatan operasional

- Hasil prediksi adalah sinyal tinjauan, bukan kepastian keterlambatan atau cost overrun.
- Estimasi resource bukan pengganti CPM, kalender kerja, validasi workface, HSE atau persetujuan resource.
- P80 biaya dan jadwal tidak otomatis membentuk distribusi gabungan berkorelasi.
- Keputusan recovery, perubahan baseline, kontrak, procurement dan mobilisasi harus disetujui pejabat berwenang.
- SQLite lokal dan nama pengguna yang dicatat pada action register bukan autentikasi.
- Untuk penggunaan multi-user/produksi, diperlukan autentikasi, role-based access, database bersama, backup, secrets management, audit retention dan monitoring.

## F. Jangan lakukan dulu

Jangan menggunakan data contoh sebagai data proyek aktual. Jangan mengirim token Telegram/API ke chat, source code, issue publik atau commit. Masukkan rahasia hanya melalui mekanisme secrets yang aman pada lingkungan deployment.
