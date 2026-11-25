# UAT AI Project Control — Panduan Pengujian Windows

Dokumen ini dipakai untuk uji penerimaan pengguna (UAT) sebelum aplikasi dinyatakan siap dipakai. Jalankan pada salinan aplikasi lokal, bukan database produksi.

## A. Persiapan

- [ ] Windows 10/11 64-bit.
- [ ] Python 3.11 64-bit terpasang dan perintah `py -3.11 --version` berhasil.
- [ ] Clone branch `ai-project-control-release-candidate`.
- [ ] Jalankan `START_AI_PROJECT_CONTROL.bat`.
- [ ] Browser membuka Streamlit pada komputer lokal.
- [ ] Catat versi aplikasi/commit, tanggal, nama penguji, dan versi Python.
- [ ] Gunakan data proyek contoh atau data yang sudah mendapat izin pemilik. Jangan gunakan data kontrak rahasia untuk uji AI.

## B. Uji Project Data Hub dan impor

- [ ] Buat proyek uji dengan kode unik, nama, mata uang, tanggal mulai dan tanggal status.
- [ ] Unduh template yang disediakan aplikasi.
- [ ] Impor file Excel dan CSV yang valid.
- [ ] Impor file dengan kolom wajib hilang; aplikasi harus memberi pesan validasi yang jelas dan tidak membuat angka nol palsu.
- [ ] Impor file rusak/format tidak didukung; aplikasi harus menolak dengan aman.
- [ ] Periksa ringkasan jumlah baris diterima/ditolak dan jejak impor.
- [ ] Tutup dan buka ulang aplikasi; proyek tersimpan harus tetap tersedia.

Catat nama file, jumlah record, hasil validasi, dan pesan kesalahan yang terlihat. Hapus data uji setelah bukti UAT disimpan.

## C. Uji WBS, BOQ, jadwal dan XER

- [ ] Impor WBS/BOQ dengan ID unik, kuantitas, satuan, harga dan bobot yang diketahui.
- [ ] Periksa subtotal BOQ: kuantitas × harga satuan.
- [ ] Periksa total BOQ dan alokasi bobot; jumlah bobot harus sesuai aturan aplikasi dan tidak boleh diam-diam dinormalisasi tanpa pemberitahuan.
- [ ] Uji aktivitas jadwal dengan relasi FS dan lag yang diketahui.
- [ ] Periksa tanggal mulai/selesai, total float, jalur kritis, dan durasi proyek terhadap perhitungan referensi yang disetujui.
- [ ] Jika menggunakan XER, bandingkan hasil aplikasi dengan Primavera P6 untuk kalender, constraint, relationship, lag, dan tanggal.
- [ ] Catat perbedaan. CPM aplikasi adalah screening/decision support; Primavera P6 tetap referensi otoritatif untuk recalculation kalender proyek.

## D. Uji progress dan EVM

Gunakan angka uji yang disetujui penguji. Untuk pemeriksaan aritmetika dasar:

- PV = Planned Value pada tanggal status.
- EV = Earned Value pada tanggal status.
- AC = Actual Cost pada tanggal status.
- SV = EV − PV.
- CV = EV − AC.
- SPI = EV / PV bila PV > 0.
- CPI = EV / AC bila AC > 0.

- [ ] Masukkan PV, EV dan AC yang sudah dihitung manual.
- [ ] Cocokkan SV, CV, SPI, CPI dengan rumus di atas dan toleransi pembulatan yang disepakati.
- [ ] Uji kondisi PV=0 dan AC=0; aplikasi tidak boleh menampilkan pembagian nol atau angka tak terhingga seolah valid.
- [ ] Periksa EAC/ETC/VAC/TCPI terhadap metode yang dipilih dan dokumentasikan asumsi.
- [ ] Periksa status date, baseline version, satuan mata uang, serta sumber data.

Jangan menyetujui EVM sebelum metode EAC/ETC dan aturan progress weighting disepakati oleh Project Controls/Cost Control.

## E. Uji cashflow, sumber daya, risiko dan recovery

- [ ] Cocokkan time-phased cashflow dengan periode dan total kontrol.
- [ ] Uji manpower/equipment loading terhadap jumlah dan kapasitas yang dimasukkan.
- [ ] Uji risk register dengan probabilitas dan dampak contoh; cocokkan exposure dengan rumus/metode yang ditampilkan aplikasi.
- [ ] Jalankan Monte Carlo dua kali dengan seed dan input yang sama; hasil harus reproducible bila aplikasi menyediakan seed.
- [ ] Ubah satu asumsi risiko; hasil skenario harus berubah secara masuk akal.
- [ ] Buat recovery scenario; bandingkan baseline, forecast dan skenario.
- [ ] Pastikan rekomendasi tidak mengubah baseline yang sudah disetujui tanpa workflow change control.

## F. Uji laporan dan integrasi opsional

- [ ] Ekspor Excel dan PDF; buka file hasil dan periksa isi, satuan, tanggal status, serta identitas proyek.
- [ ] Uji AI Advisor hanya dengan data non-rahasia dan persetujuan eksplisit. Pastikan fakta dibedakan dari hipotesis.
- [ ] Uji Groq atau Gemini hanya jika pemilik API menyediakan key. Jangan tempel API key ke screenshot, log, chat, atau repository.
- [ ] Uji Telegram hanya dengan bot/chat uji yang diotorisasi. Pastikan penerima dan isi laporan benar sebelum pengiriman.
- [ ] Pastikan aplikasi tetap berfungsi ketika API key tidak tersedia; fitur opsional harus memberi pesan yang jelas.

## G. Uji backup dan restore

- [ ] Buat backup dari workspace uji.
- [ ] Pastikan file backup terunduh dan bukan file kosong.
- [ ] Buat proyek uji tambahan setelah backup.
- [ ] Restore backup uji; verifikasi proyek kembali ke kondisi pada saat backup.
- [ ] Pastikan safety backup sebelum restore tercipta.
- [ ] Uji file backup rusak atau file bukan database; restore harus ditolak dan database aktif tidak berubah.

Lakukan restore hanya saat aplikasi ditutup dan tidak ada proses lain yang menulis database.

## H. Keamanan dan batas produksi

- [ ] Pastikan API key hanya berada di environment lokal/Streamlit secrets dan tidak ada di Git.
- [ ] Pastikan aplikasi lokal hanya diakses dari komputer yang diizinkan.
- [ ] Pastikan data proyek tidak dikirim ke AI tanpa persetujuan.
- [ ] Pastikan file unggahan dan hasil ekspor disimpan pada lokasi yang disetujui.
- [ ] Lakukan pemeriksaan dependency/security dan backup retention sebelum penggunaan operasional.
- [ ] Untuk multi-user/hosting, desain autentikasi, otorisasi, database bersama, enkripsi, audit log, monitoring, backup terjadwal dan incident response harus ditetapkan terlebih dahulu.

## I. Keputusan UAT

Status setiap butir: PASS / FAIL / BLOCKED / NOT APPLICABLE.

| Area | Penguji | Bukti / referensi | Status | Catatan / defect |
|---|---|---|---|---|
| Instalasi & startup | | | | |
| Project Data Hub & impor | | | | |
| BOQ & WBS | | | | |
| CPM & XER | | | | |
| Progress & EVM | | | | |
| Cashflow & resource | | | | |
| Risk & Monte Carlo | | | | |
| Recovery & change control | | | | |
| Excel/PDF | | | | |
| AI Advisor / Telegram | | | | |
| Backup & restore | | | | |
| Security & data handling | | | | |

**Kriteria penerimaan:** tidak ada defect kritis/tinggi yang terbuka; semua hasil keuangan dan jadwal cocok dengan referensi yang disetujui; backup/restore berhasil; pemilik proses menandatangani hasil UAT.

Nama dan persetujuan penguji: ____________________

Tanggal: ____________________

**Catatan:** Lulus CI otomatis tidak sama dengan lulus UAT. Aplikasi belum dinyatakan production-ready sampai UAT, keamanan, dan operasional ditandatangani.
