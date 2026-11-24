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
6. Periksa ringkasan gabungan risk-adjusted cost dan schedule, lalu Risk Exposure Matrix dan rekomendasi mitigasi. P80 biaya dan P80 jadwal adalah distribusi marginal terpisah, bukan satu skenario gabungan berkorelasi.
7. Bandingkan recovery scenario dan validasi asumsi produktivitas tambahan.
8. Catat rencana mitigasi pada Risk Mitigation Execution Tracker, termasuk risk ID, owner, due date, status, residual probability/impact, dan bukti. Status VERIFIED wajib memiliki bukti.
9. Gunakan ringkasan risk governance untuk melihat tindakan terkait, action overdue/blocked, dan risiko yang belum memiliki mitigasi.
10. Hubungkan executive action ke risk ID terkait bila tindakan berasal dari risiko yang tercatat.
11. Gunakan Portfolio Command Center dan Portfolio-wide Risk & Shared Resource Intelligence untuk memeriksa paparan risiko per mata uang dan konflik kapasitas resource lintas proyek. Pastikan resource ID, periode, unit, dan kapasitas benar-benar merujuk pada pool yang sama.
12. Tinjau COO Executive Portfolio Decision Brief sebagai daftar isu yang memerlukan perhatian manajemen. Rekomendasi merupakan bahan review, bukan persetujuan otomatis.
13. Gunakan Portfolio Cost & Cashflow Intelligence untuk membandingkan budget dan actual cost per mata uang. Remaining budget bukan saldo kas; pastikan sumber BAC/BOQ dan actual cost telah tervalidasi.
13. Simpan snapshot KPI historis secara berkala. Setelah tersedia minimal tiga tanggal untuk suatu indikator, jalankan early warning dari histori tersimpan.
14. Jika histori mencukupi, jalankan evaluasi baseline ML KPI dan bandingkan MAE dengan persistence baseline. Model hanya dievaluasi dalam memori; belum disimpan atau dipakai otomatis untuk keputusan.
15. Ekspor laporan untuk review dan persetujuan manajemen.

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


## G. Dated Cash Flow Forecast

1. Open the **Dated Cash Flow Forecast** page from the Streamlit sidebar.
2. Enter the reconciled opening cash balance separately for every currency used.
3. Enter each actual or planned transaction with a unique transaction ID, date, project ID, currency, direction, positive amount, and status ACTUAL or FORECAST.
4. Generate the daily running balance and monthly summary; inspect any dates with projected negative balances.
5. Download the JSON output for review and retain the source transaction evidence.

The page does not infer invoice due dates, collection probability, financing availability or FX rates. A forecast transaction is only a supplied plan, not a confirmed payment. Do not use sample values as actual treasury data.
