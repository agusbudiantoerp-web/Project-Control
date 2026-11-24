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


## H. EVM & Cost Forecast Control

1. Open **EVM & Cost Forecast Control** in the Streamlit sidebar.
2. Enter project ID, BAC and currency.
3. Supply progress records containing planned_value and earned_value and actual-cost records containing actual_cost. Use one consistent period convention: period deltas can be summed; cumulative snapshots must be reduced to the latest snapshot per activity before calculation.
4. Optionally enter an as-of period to limit the records included.
5. Review PV, EV, AC, BAC, SPI, CPI, EAC, ETC, VAC and the three EAC scenarios.
6. Treat missing data as unassessed and validate source valuation and currency before management use.

CPI-based EAC assumes current cost efficiency continues. CPI×SPI is a scenario, not a probabilistic prediction. These values do not represent payment timing, cash balance, approved budget changes or commitments.


## I. Telegram Executive Report

1. Create a Telegram bot through the official BotFather process and obtain its bot token securely.
2. Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the hosting platform's secrets/environment settings. `.env.example` is a blank template; do not commit actual credentials.
3. Open **Telegram Executive Report**, enter the reporting date and provide the portfolio intelligence/action-register JSON objects.
4. Generate and review the message preview. Download the text if it needs approval first.
5. To deliver, check the explicit authorization checkbox and press **Send Telegram report**. The page will report whether Telegram accepted the message.

A successful API response confirms Telegram accepted the message, not that the intended recipient read or acted on it. Test with a private chat before any operational group. Never place bot credentials in the form or source repository.


## J. Saved Project Financial Control

1. Impor `project_master` terlebih dahulu melalui Project Workspace, termasuk Project ID, BAC dan currency.
2. Impor dataset `progress` dengan Project ID, Activity ID, period, planned_value dan earned_value.
3. Impor dataset `actual_cost` dengan Project ID, period, cost_code dan actual_cost.
4. Pastikan semua nilai menggunakan basis valuasi yang konsisten. Bila currency dicantumkan pada baris, currency harus sama dengan Project Master. Baris tanpa currency menggunakan asumsi mata uang proyek dan harus diverifikasi terhadap dokumen sumber.
5. Buka **Saved Project Financial Control**, masukkan Project ID dan periode bila diperlukan.
6. Tinjau validasi workspace, PV/EV/AC/BAC, SPI/CPI dan skenario EAC. Unduh JSON untuk review.

Halaman ini membaca database lokal dan tidak mengubah dataset. Mesin EVM menjumlahkan semua baris sampai periode batas; data harus berupa delta periode. Jika sumber berupa snapshot kumulatif, siapkan data menjadi delta atau pilih snapshot terbaru per aktivitas sebelum impor. Jangan gabungkan mata uang atau basis valuasi berbeda.


## K. Ekspor laporan Financial Control

Setelah Saved Project Financial Control berhasil menghitung data tersimpan, gunakan tombol PDF, Excel atau JSON untuk mengunduh ringkasan yang sama. Periksa nama proyek, periode, mata uang, status validasi, dan keterbatasan sebelum membagikan laporan. File yang diunduh merupakan output analisis, bukan dokumen yang ditandatangani atau persetujuan perubahan anggaran.


## L. Saved Portfolio — COO Executive Cockpit

1. Impor Project Master, Progress dan Actual Cost untuk setiap proyek melalui workspace lokal.
2. Pastikan semua proyek memakai definisi periode dan basis valuasi yang konsisten. Data periode harus berupa delta; snapshot kumulatif perlu dinormalisasi sebelum impor.
3. Buka **Saved Portfolio — COO Executive Cockpit**.
4. Isi periode pelaporan bila ingin membatasi perhitungan dan pilih Bahasa Indonesia atau English.
5. Tekan **Load saved portfolio** untuk melihat jumlah proyek, status penilaian, RED/AMBER, scorecard dan BAC per mata uang.
6. Buka detail proyek untuk melihat EVM, jumlah sumber data dan validasi. Proyek dengan data tidak cukup atau currency mismatch ditandai perlu pemeriksaan.
7. Tinjau preview dan unduh laporan PDF, Excel atau JSON.

Cockpit hanya membaca proyek dalam SQLite lokal pada komputer ini. Nilai BAC antar mata uang tidak dijumlahkan. Scorecard SPI/CPI adalah indikator ringkas, bukan pengganti risk review, critical-path analysis atau keputusan pemilik proyek.


## M. Workspace Backup & Import History

1. Buka **Workspace Backup & Import History**.
2. Pilih Project ID untuk melihat hingga 100 peristiwa impor terbaru (waktu, dataset, mode, jumlah baris dan status).
3. Tekan **Prepare SQLite backup**, kemudian unduh file backup.
4. Simpan backup di media terenkripsi dan lokasi terpisah dari komputer kerja. Batasi akses karena database dapat memuat informasi komersial dan operasional sensitif.
5. Jangan unggah database atau backup ke repository GitHub publik. Lakukan uji pemulihan pada salinan terpisah sebelum mengandalkan backup untuk pemulihan operasional.

Fitur ini membuat snapshot konsisten dari SQLite lokal; belum ada penjadwalan backup otomatis, enkripsi backup otomatis, retensi terkelola, atau pemulihan satu klik.


## N. Risk Governance di COO Cockpit

1. Impor dataset `risk`, `activities` dan `wbs` untuk setiap proyek melalui Project Workspace.
2. Pastikan `risk_id` unik per proyek, probabilitas berada pada rentang 0–1, dan impact menggunakan unit serta mata uang yang konsisten dalam proyek.
3. Buat executive action dengan `risk_id` yang sama untuk menautkannya ke risiko. Tindakan tanpa risk_id tidak dihitung sebagai tindakan mitigasi risiko.
4. Catat mitigation pada Risk Mitigation Store. Status VERIFIED memerlukan evidence.
5. Buka COO Cockpit, pilih periode EVM dan tanggal governance. Tinjau risk priority, activity/WBS link, tindakan terlambat/blocked, mitigasi yang belum direncanakan dan residual exposure.
6. Periksa orphan action dan orphan mitigation; hubungan yang tidak cocok tidak ditebak oleh sistem.

Risk matrix menggunakan probabilitas × impact. Nilai impact hanya dapat dibandingkan dalam satuan yang konsisten. Label `created_by`, `changed_by`, dan `updated_by` merupakan atribusi, bukan identitas terautentikasi. Persetujuan dan penerimaan risiko tetap dilakukan oleh manajemen.
