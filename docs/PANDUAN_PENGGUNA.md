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
python -m pip install -r requirements.txt -r ai_project_control/requirements.txt
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

Untuk penggunaan berikutnya, aplikasi juga dapat dijalankan dengan klik dua kali `START_AI_PROJECT_CONTROL.bat` pada folder utama repository. Browser biasanya terbuka otomatis. Jika tidak, buka alamat lokal yang ditampilkan Streamlit di terminal.

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
14. Simpan snapshot KPI historis secara berkala. Setelah tersedia minimal tiga tanggal untuk suatu indikator, jalankan early warning dari histori tersimpan.
15. Jika histori mencukupi, jalankan evaluasi baseline ML KPI dan bandingkan MAE dengan persistence baseline. Model hanya dievaluasi dalam memori; belum disimpan atau dipakai otomatis untuk keputusan.
16. Ekspor laporan untuk review dan persetujuan manajemen.

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


## O. Histori Kesehatan Portofolio dan Early Warning

Untuk menilai perubahan kinerja, impor dataset `portfolio_snapshots` dengan satu record per proyek per tanggal: `project_id`, `snapshot_date` (YYYY-MM-DD), dan nilai yang tersedia untuk `SPI`, `CPI`, serta `risk_score`. Simpan snapshot secara berkala setelah periode pelaporan disetujui. COO Cockpit membandingkan dua tanggal terbaru; penurunan SPI/CPI lebih dari 0,02 dan kenaikan risk score lebih dari 5 poin menghasilkan sinyal pemeriksaan. Satu snapshot saja berstatus NO_BASELINE. Metrik yang hilang tidak diganti nol. Jangan mengisi snapshot historis dengan angka perkiraan.


Untuk mengimpor histori snapshot, gunakan dataset `portfolio_snapshots`. Pemetaan kolom menerima `Project ID`/`Kode Proyek`, `Snapshot Date`/`Tanggal Snapshot`, `SPI`/`Schedule Performance Index`, `CPI`/`Cost Performance Index`, dan `Risk Score`/`Skor Risiko`. Tanggal harus valid `YYYY-MM-DD`; risk score dibatasi 0–100; SPI/CPI tidak boleh negatif. Sediakan satu baris per tanggal per proyek.


## P. Konflik Resource Lintas Proyek

COO Cockpit memeriksa resource yang dipakai bersama oleh beberapa proyek. Impor dataset `resources` dengan `project_id`, `resource_id`, `period`, `unit`, `planned_units`, dan `capacity_units`. Sistem hanya menyatakan overload bila resource ID, periode, satuan, dan kapasitas sama persis pada sedikitnya dua proyek. Pastikan ID yang sama memang menunjuk ke armada/peralatan/tenaga kerja yang sama. Jika kapasitas berbeda atau data wajib hilang, hasilnya tidak dinilai dan bukan dianggap aman. Jangan menjumlahkan resource yang satuannya berbeda.


## Q. Schedule & Cost Outlook pada COO Cockpit

Isi tanggal `Governance as-of date` dengan `YYYY-MM-DD` saat memuat portofolio. Untuk setiap aktivitas, impor `baseline_finish_date` dan `forecast_finish_date`; `planned_progress_pct` dan `actual_progress_pct` dapat melengkapi penilaian. Sistem menampilkan selisih tanggal finish dan aktivitas terlambat, serta tiga skenario EAC dari EVM (CPI, budget rate, CPI×SPI). Jika tanggal as-of tidak diberikan, outlook diberi status NOT_RUN. Jika tanggal aktivitas atau data EVM tidak lengkap, hasil tetap parsial/tidak dinilai. Skenario EAC bukan anggaran yang disetujui, bukan simulasi Monte Carlo, dan tidak memasukkan kalender kerja kecuali telah tercermin pada tanggal forecast.


## R. Resource Loading dan Capacity Alert

COO Cockpit menampilkan ringkasan utilisasi resource per proyek, resource ID, dan periode. Impor dataset `resources` dengan `resource_id`, `period`, `planned_units`, `capacity_units`, serta `unit`. Jika tersedia, `actual_units` juga ditampilkan. Status OVERLOADED muncul bila planned units melampaui kapasitas yang dinyatakan. Jika demand atau kapasitas tidak tersedia, hasil UNASSESSED—bukan dianggap nol atau aman. Baris dengan resource berbeda, satuan berbeda, atau periode berbeda tidak digabungkan dalam ringkasan per proyek.


## S. Portfolio Financial Position

COO Cockpit menampilkan anggaran (BAC atau jumlah BOQ jika BAC tidak tersedia), actual cost dari dataset `actual_cost`, sisa anggaran, dan status over-budget. Setiap proyek harus memiliki mata uang yang benar. Jika actual-cost record belum tersedia atau nilai biaya tidak lengkap, proyek ditandai belum dapat dinilai—tidak diasumsikan memiliki actual cost nol. Ringkasan lintas proyek dipisahkan menurut mata uang; tidak ada konversi kurs. Angka ini adalah posisi anggaran versus actual cost, bukan saldo kas atau proyeksi pembayaran.


## T. COO Decision Brief dan Project Director Priorities

Pada Saved Portfolio COO Cockpit, bagian COO Decision Brief merangkum proyek yang perlu ditinjau berdasarkan SPI, CPI, risk score yang tersedia, keterlambatan aktivitas bertanggal, dan overload resource. Daftar rekomendasi adalah agenda review, bukan instruksi otomatis. Periksa nilai sumber, periode cut-off, baseline yang disetujui, risk owner, resource, HSE, kontrak dan kewenangan biaya sebelum menetapkan tindakan. Jika SPI/CPI/risk score tidak tersedia, proyek ditandai UNASSESSED atau DATA_REVIEW; sistem tidak menganggapnya hijau.


## U. Predictive Early Warning dan Recovery Review

Bagian Predictive Early Warning menggunakan `portfolio_snapshots` bertanggal. Forecast trend memerlukan minimal tiga tanggal unik untuk setiap metrik; metrik yang belum cukup historinya tetap `INSUFFICIENT_HISTORY`. Metode yang digunakan adalah regresi linear sederhana 30 hari, bukan model ML atau probabilitas kegagalan. Recovery Review menggabungkan EVM dan Risk Exposure Matrix yang tersedia, lalu secara eksplisit menampilkan input Monte Carlo, scenario comparison, atau resource recovery yang belum tersedia. Rekomendasi adalah agenda validasi, bukan persetujuan tindakan.


## V. Primavera P6 XER dan drawing-to-BOQ

### Import jadwal Primavera P6

1. Buka **Primavera P6 XER & Drawing-to-BOQ Intake**.
2. Upload file `.xer` dan pilih project sumber jika file berisi lebih dari satu project.
3. Isi Project ID, nama proyek dan mata uang yang akan dipakai di workspace utama.
4. Periksa preview WBS dan Activities sebelum impor.
5. Pilih Upsert untuk menambah/memperbarui record. Pilih Replace hanya jika memang ingin mengganti seluruh dataset WBS dan Activities; aplikasi meminta konfirmasi tambahan.
6. Setelah impor, buka Project Workspace untuk meninjau CPM dan dataset.

Durasi P6 dikonversi dari jam ke hari nominal 8 jam. Kalender kerja, hari libur, lag, constraint, tipe relasi non-finish-to-start dan resource leveling tidak direkonstruksi. Validasi kembali baseline dan kalender pada Primavera P6 sebelum keputusan proyek.

### Draft BOQ dari gambar PDF

1. Pilih proyek yang sudah ada dan upload PDF gambar teknik.
2. Pilih halaman yang akan dianalisis. Preview dilakukan lokal.
3. Konfigurasikan `GEMINI_API_KEY` secara aman. Centang persetujuan pengiriman halaman ke Google Gemini, lalu tekan Analyze.
4. Periksa dan edit item, description, unit, quantity, metode pengukuran, confidence dan asumsi.
5. Isi quantity yang masih kosong berdasarkan pengukuran terverifikasi. Ubah `review_status` menjadi `VERIFIED` hanya setelah quantity surveyor memeriksa gambar sumber.
6. Centang konfirmasi review dan simpan BOQ draft. Unit rate dan amount sengaja tetap kosong sampai disuplai dan disetujui.

Hasil Gemini bukan quantity takeoff final. Model tidak dapat menggantikan pemeriksaan skala, dimensi, revisi gambar, metode ukur, spesifikasi, dan persetujuan quantity surveyor. Halaman PDF yang dipilih dikirim ke Google hanya setelah persetujuan eksplisit.

Launcher V1 di `ai_project_control` tetap tersedia sebagai aplikasi kompatibilitas dan memakai database terpisah di `%LOCALAPPDATA%\\AIProjectControl\\project_control.db`. Data V1 tidak otomatis tersinkron dengan workspace utama yang memakai `.project_control/project_control.sqlite3` atau path `PROJECT_CONTROL_DB`.


### Mengirim gambar melalui Telegram

1. Atur `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` pada environment/secrets aplikasi.
2. Kirim file PDF sebagai **Document** ke private chat bot yang sesuai dengan chat ID yang diizinkan.
3. Pada halaman Drawing Intake, buka panel **Ambil PDF gambar dari Telegram** dan tekan **Fetch latest Telegram PDF**.
4. Pilih halaman PDF yang diterima, periksa preview lokal, lalu ikuti persetujuan Gemini dan verifikasi quantity surveyor seperti langkah di atas.

Intake ini memakai polling `getUpdates`, bukan webhook. Jika bot masih memiliki webhook aktif, polling tidak akan berjalan. Aplikasi hanya mengambil PDF dari chat ID yang dikonfigurasi; dokumen lain diabaikan. File disimpan sementara dalam session aplikasi, bukan pada ProjectStore. Pengiriman ke Gemini tetap memerlukan persetujuan terpisah.


## AI Project Advisor — Groq / Gemini

1. Buka **AI Project Advisor — Groq / Gemini** dari sidebar.
2. Pilih Project ID yang sudah tersimpan pada Project Workspace.
3. Periksa metrik EVM, status jadwal, risiko dan tindakan yang ditampilkan pada bagian **Evidence sent to the AI provider**.
4. Pilih Groq atau Gemini dan model yang tersedia pada akun provider.
5. Centang persetujuan pengiriman data setelah memastikan informasi tersebut boleh dibagikan kepada provider eksternal.
6. Tekan **Generate AI project analysis**. Hasil dapat diunduh sebagai Markdown.

Konfigurasikan `GROQ_API_KEY` atau `GEMINI_API_KEY` melalui environment variable atau Streamlit secrets. API key tidak disimpan ke ProjectStore dan dikirim melalui header permintaan. Jangan gunakan data rahasia atau data klien tanpa izin organisasi. AI dapat salah menafsirkan konteks; verifikasi fakta, hipotesis dan rekomendasi sebelum mengambil keputusan. Advisor tidak mengubah baseline, anggaran, jadwal atau status tindakan.


## Validasi hubungan impor

Urutan impor yang disarankan: Project Master → WBS → Activities → BOQ → Resources → Progress → Actual Cost → Risk dan register lainnya. Isi `activity_id`, `wbs_id`, dan `boq_id` bila tersedia di sumber. Sistem memeriksa referensi silang terhadap data proyek yang sudah tersimpan sebelum impor CSV/XLSX dikomit. Bila hubungan tidak cocok, impor ditolak dan data lama tetap dipertahankan.

Untuk progres, gunakan satu tingkat pencatatan per aktivitas dan periode: satu baris total aktivitas, atau beberapa baris rincian BOQ. Jangan mencampur keduanya. Bila memakai rincian BOQ, kombinasi Activity ID + BOQ ID + periode harus unik. Lihat `docs/PROJECT_DATA_IMPORT_WORKFLOW.md` untuk aturan lengkap.
