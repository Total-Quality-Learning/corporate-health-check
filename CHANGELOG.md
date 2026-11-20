# Catatan Pembaruan (Changelog)

Ringkasan fitur dan penyempurnaan yang telah ditambahkan ke **Corporate Health Check** setelah rilis awal.

---

## Pembaruan Terbaru (18 November 2026)

### 1. Skill Baru: `kondisi-ekonomi-daerah` (PR #6)
- Menambahkan [skills/kondisi-ekonomi-daerah/](skills/kondisi-ekonomi-daerah/SKILL.md) untuk menghubungkan kondisi makro & ekonomi daerah dengan risiko keuangan perusahaan:
  - [`ambil_makro.py`](skills/kondisi-ekonomi-daerah/scripts/ambil_makro.py): menarik indikator makro nasional resmi dari World Bank API (gratis tanpa API key, eksekusi paralel + *retry* aman), mendukung input CSV/JSON daerah ([`template-ekonomi-daerah.csv`](skills/kondisi-ekonomi-daerah/templates/template-ekonomi-daerah.csv)), mode `--offline`, serta opsi `--bps-key` untuk BPS WebAPI. Indikator yang belum tersedia ditandai **PERLU DATA**.
  - [`analisa_risiko_ekonomi.py`](skills/kondisi-ekonomi-daerah/scripts/analisa_risiko_ekonomi.py): menilai 5 dimensi risiko daerah (permintaan/PDRB, inflasi, kenaikan UMP/UMK, suku bunga, pelemahan kurs), memetakan paparan risiko langsung ke keuangan perusahaan (`rasio.json` tahunan maupun `laporan.json` bulanan), dan menurunkan `skenario-makro.json` yang siap dijalankan di [`uji_ketahanan_kas.py`](skills/uji-ketahanan-kas/scripts/uji_ketahanan_kas.py).
- Dilengkapi uji regresi di [`tests/test_ekonomi_daerah.py`](tests/test_ekonomi_daerah.py).

### 2. Panduan Agen AI: `SOUL.md` & Report Kombinasi (PR #5, diperbarui di PR #6)
- Menambahkan [`SOUL.md`](SOUL.md) di root repositori untuk memandu agen/asisten AI agar:
  - Tetap **interaktif** (4 titik tanya wajib: preferensi tampilan, konteks bisnis/tujuan rapat, konfirmasi akun bebas/PDF, kurasi emiten pembanding, dan konfirmasi skenario risiko).
  - Menggabungkan ketelitian angka skrip deterministik dengan kecerdasan konsultatif AI serta menyediakan kebebasan menyusun **report kombinasi** lintas-skill (`rasio.json`, `gejala.json`, `kesiapan.json`, `laporan.json`, `uji-kas.json`, `pembanding.json`, `risiko-ekonomi.json`).
  - Menghubungkan perbandingan emiten Tbk secara otomatis dengan analisis keuangan perusahaan pengguna.

### 3. Penyempurnaan Integrasi Emiten IDX: `data-emiten` (PR #4)
- Memperbarui [`skills/data-emiten/scripts/ringkas_emiten.py`](skills/data-emiten/scripts/ringkas_emiten.py) agar:
  - Menerima baik `rasio.json` (tahunan) **maupun** `laporan.json` (bulanan) pada argumen `--rasio`.
  - Menambahkan metrik **Rasio cepat** (`quick_ratio`) dan **Arus kas operasi / laba bersih** (`cfo_to_ni`), serta menghitung `cagr3` pengguna jika tersedia >= 4 periode.
  - Menjaga median agar tidak terdistorsi oleh emiten berekuitas nol/negatif (ROE/DER disetel kosong + peringatan), memperingatkan emiten sektor `Finance`, menghormati mata uang laporan (`fundamental_currency_code`), dan mengekspor map `posisi` ke JSON.

### 4. Konverter CSV & Excel Format Bebas: `tools/konversi_data.py` (PR #3)
- Menambahkan [`tools/konversi_data.py`](tools/konversi_data.py) untuk mengonversi berkas `.csv`, `.tsv`, `.xlsx`, atau `.xlsm` format bebas (ekspor akuntansi/ERP, multi-file, bertumpuk, atau format panjang/*tidy*) menjadi format standar `lk.json` / `template-lk.xlsx` (tahunan) maupun `template-paket-data.xlsx` / JSON paket (bulanan).
- Dilengkapi deteksi otomatis delimiter, encoding, posisi header, format angka ID/EN, normalisasi urutan periode, pemetaan sinonim ID/EN + pemetaan kustom (`--tulis-pemetaan`, `--pemetaan`), serta tetap menegakkan validasi ketat neraca seimbang (`exit code 2`).
- Dilengkapi uji regresi di [`tests/test_konversi_data.py`](tests/test_konversi_data.py).
