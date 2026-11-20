# Corporate Health Check

Kumpulan **Agent Skills** untuk membantu direksi membaca laporan keuangan dengan AI secara konsisten:
menemukan **gejala** di laporan keuangan, menyusun laporan rapat direksi, dan memetakan pertanyaan operasional
yang perlu dijawab tim.

> Alat bantu analisis, bukan nasihat investasi atau hasil audit.

## Isi

| Skill | Fungsi | Input |
|---|---|---|
| [`tampilan-direksi`](skills/tampilan-direksi/SKILL.md) | Menanyakan & menyimpan preferensi (untuk siapa, narasi singkat/detail/checklist, grafik/penjelasan grafik, fokus) + aturan tampilan ramah direksi | 4 pertanyaan bernomor |
| [`baca-laporan-keuangan`](skills/baca-laporan-keuangan/SKILL.md) | LK → validasi → sekitar 28 rasio **dengan perhitungannya** (termasuk DuPont & Altman Z''), metode saldo akhir/rata-rata, narasi singkat/detail/checklist, grafik atau penjelasan grafik | LK tahunan (PDF/Excel/JSON) |
| [`red-flag-operasional`](skills/red-flag-operasional/SKILL.md) | Gejala keuangan → kemungkinan penyebab operasional → data pembukti → pertanyaan untuk tim | hasil rasio |
| [`cek-kesiapan-data`](skills/cek-kesiapan-data/SKILL.md) | 8 pertanyaan → Level 1-4 kesiapan data & sistem | jawaban A-D |
| [`board-brief`](skills/board-brief/SKILL.md) | Ringkasan 1 halaman untuk direksi | hasil skill di atas |
| [`data-emiten`](skills/data-emiten/SKILL.md) | Pilih perusahaan Tbk (per sektor/industri/kata kunci) → tarik data dari TradingView → tabel pembanding + posisi perusahaan Anda vs median | kode emiten |
| [`laporan-analisa`](skills/laporan-analisa/SKILL.md) | **Paket rapat direksi** (tampilan Direksi atau Lengkap; cerita narasi atau checklist) (HTML interaktif, cetak PDF): putusan & skor, 5 cerita, 15 KPI, analisa laporan, selisih vs bulan lalu/tahun lalu/target, data operasional, uji ketahanan kas, proyeksi kas 13 minggu, rencana kerja, lampiran rasio | data bulanan (Excel) |
| [`uji-ketahanan-kas`](skills/uji-ketahanan-kas/SKILL.md) | **Stress test kas**: skenario penjualan turun, bahan naik, piutang molor, pemasok, bunga, gabungan; bulan kas di bawah minimum, plafon kredit, kovenan DSCR/ICR, uji balik | data bulanan (Excel) + skenario (opsional) |
| [`kondisi-ekonomi-daerah`](skills/kondisi-ekonomi-daerah/SKILL.md) | **Forecast risiko ekonomi daerah**: PDRB, inflasi, UMP/UMK, suku bunga, kurs (World Bank API / CSV daerah / opsional BPS) → paparan ke keuangan perusahaan & skenario stress test kas | data daerah (CSV/JSON) / makro + `rasio.json`/`laporan.json` |
| [`efisiensi-sdm-departemen`](skills/efisiensi-sdm-departemen/SKILL.md) | **Rp per karyawan & KPI budgeting departemen**: menanyakan struktur organisasi & jumlah karyawan → produktivitas/beban Rp per orang & rekomendasi KPI serta arah budgeting tiap departemen | struktur organisasi & headcount (CSV/CLI) + `rasio.json`/`laporan.json` |

Prinsipnya: **angka dihitung skrip Python yang deterministik; AI hanya menulis narasi.** Jika neraca tidak seimbang,
skrip berhenti dan tidak menghitung apa pun. Bagian yang tidak bisa dijawab dari data yang ada ditandai
**PERLU DATA**, tidak ditebak.

## Data contoh (fiktif): 4 case industri

| Folder | Perusahaan fiktif | Cerita utama |
|---|---|---|
| [`01-manufaktur-garmen`](sample-data/01-manufaktur-garmen/) | PT Contoh Garmen Nusantara | Laba naik, kas operasi negatif; persediaan & piutang membengkak |
| [`02-distribusi-fmcg`](sample-data/02-distribusi-fmcg/) | PT Contoh Niaga Distribusi | Omzet naik, laba anjlok; potongan & retur naik, piutang ritel modern lambat, utang bank melonjak |
| [`03-makanan-minuman`](sample-data/03-makanan-minuman/) | PT Contoh Pangan Sejahtera | Kas sehat, tetapi margin kotor tergerus harga bahan & waste |
| [`04-komponen-logam`](sample-data/04-komponen-logam/) | PT Contoh Presisi Teknik | Volume turun, utilisasi mesin baru rendah, bunga menekan laba |

Setiap folder berisi: LK tahunan 2025 (PDF bergaya laporan keuangan umum, dengan catatan), LK 2023-2025 (Excel &
JSON), data keuangan bulanan Jan 2023 - Okt 2026 (Excel), dan contoh jawaban cek kesiapan.

## Cara memakai

### 1. Di aplikasi AI (tanpa coding)

1. Unduh file `.zip` tiap skill (folder `dist/`, atau buat sendiri: `python tools/buat_zip.py`).
2. Unggah ke aplikasi AI yang mendukung Agent Skills **dan eksekusi kode** (mis. Claude.ai: *Settings → Capabilities →
   Skills*). Ketersediaan fitur berbeda per aplikasi dan paket langganan; cek di aplikasi Anda.
3. Ketik, misalnya: *"Pakai data contoh distribusi FMCG. Buat laporan analisa Oktober 2026 untuk rapat direksi."*

### 2. Di CLI (staf IT/finance)

Salin folder `skills/` ke lokasi skill alat Anda (mis. `.claude/skills/` untuk Claude Code; untuk Codex CLI,
Gemini CLI, dan lainnya lihat dokumentasi masing-masing tentang Agent Skills), lalu minta seperti di atas.

### 3. Langsung dengan Python (tanpa AI)

```
pip install -r requirements.txt
python skills/laporan-analisa/scripts/susun_laporan.py sample-data/01-manufaktur-garmen/Data-Keuangan-Bulanan.xlsx --out laporan.html
python skills/uji-ketahanan-kas/scripts/uji_ketahanan_kas.py sample-data/02-distribusi-fmcg/Data-Keuangan-Bulanan.xlsx --horizon 6
python tools/analisis_lengkap.py sample-data/01-manufaktur-garmen/lk-tahunan.json --kesiapan B,B,A,B,A,B,A,C
```

Buka `laporan.html` di browser (tombol *Cetak / PDF* untuk versi kertas). Alur kedua menghasilkan folder `hasil/`
berisi `rasio.md`, `gejala.md`, `kesiapan.md`, `brief.md`, dan `brief.html`.

### 4. Portal Web Peserta (antarmuka browser lokal)

```
python tools/portal_peserta.py
```

Membuka antarmuka web lokal (`http://127.0.0.1:8765`) untuk mengunggah Excel/CSV/JSON (termasuk penyamaran angka, konversi format bebas, Trial Balance, & Arus Kas otomatis), menjalankan Laporan Direksi Bulanan, Analisis LK Tahunan, Stress Test Kas, Risiko Ekonomi Daerah, Benchmark Emiten IDX, Efisiensi SDM & Budgeting, serta menyusun Report Kombinasi.

## Pilih gaya tampilan

Sebelum analisis, AI menanyakan 4 hal (untuk siapa, bentuk narasi, bentuk visual, fokus) lalu menyimpannya di
`preferensi.json`. Semua skrip menerima `--preferensi preferensi.json`:

```
python skills/tampilan-direksi/scripts/preferensi.py --pertanyaan
python skills/tampilan-direksi/scripts/preferensi.py --jawaban 1A,2C,3C,4B --out preferensi.json
python skills/baca-laporan-keuangan/scripts/hitung_rasio.py lk.json --out-json rasio.json --preferensi preferensi.json
python skills/baca-laporan-keuangan/scripts/visualisasi.py rasio.json --out visual.html --mode keduanya
```

## Data emiten IDX (TradingView)

```
cd skills/data-emiten/scripts && npm install        # sekali; butuh Node.js >= 20 & internet
node tv_emiten.mjs daftar --cari tekstil --limit 15
node tv_emiten.mjs ambil UNVR ICBP MYOR --out emiten.json
python ringkas_emiten.py emiten.json --rasio ../../../rasio.json
```

> **Penting:** TradingView tidak menyediakan API data publik resmi. Skill ini memakai pustaka komunitas
> [TradingView-API](https://github.com/Mathieu2301/TradingView-API) yang tidak berafiliasi dengan TradingView, dan
> ketentuan layanan TradingView membatasi pengambilan data otomatis. Data bisa tertunda atau berbeda dengan laporan
> keuangan resmi (uji internal: laba kotor bisa selisih hingga sekitar 4%). Gunakan secukupnya dan verifikasi ke idx.co.id.

## Memakai data perusahaan Anda sendiri

Panduan lengkap: [`panduan-data-sendiri.md`](skills/baca-laporan-keuangan/references/panduan-data-sendiri.md).

Punya **CSV atau Excel format bebas** (ekspor akuntansi/ERP, multi-file CSV, atau format panjang/tidy)? Konversi dulu secara deterministik ke format standar:

```
python tools/konversi_data.py laporan-bebas.xlsx --out lk.json
python tools/konversi_data.py neraca.csv labarugi.csv aruskas.csv --out lk.json
python tools/konversi_data.py ekspor-bulanan.csv --jenis bulanan --out paket.xlsx
python tools/konversi_data.py laporan-bebas.xlsx --tulis-pemetaan pemetaan.json   # jika ada akun khusus
```

| Punya data | Template | Samarkan (jalankan sendiri, tanpa AI) | Skill |
|---|---|---|---|
| LK tahunan | [`template-lk.xlsx`](skills/baca-laporan-keuangan/templates/template-lk.xlsx) | `python skills/baca-laporan-keuangan/scripts/samarkan_lk.py lk.json --out lk-samaran.json --samarkan-periode` | baca-laporan-keuangan → red-flag-operasional → board-brief |
| LK bulanan (≥ 13 bulan) | [`template-paket-data.xlsx`](skills/laporan-analisa/templates/template-paket-data.xlsx) | `python skills/laporan-analisa/scripts/samarkan_paket.py Data.xlsx --out Data-samaran.xlsx` | laporan-analisa |

Penyamaran mengalikan semua angka uang dengan satu faktor acak dan mengganti nama. **Semua rasio, hari modal kerja,
dan status KPI tetap sama persis**, tetapi omzet, laba, dan utang asli tidak terlihat. Bagikan hanya file samaran
ke AI. Sebelum mengunggah data asli ke layanan AI mana pun, cek kebijakan penggunaan AI di perusahaan Anda dan
pengaturan privasi layanan tersebut.

## Struktur

```
corporate-health-check/
├── skills/
│   ├── baca-laporan-keuangan/   SKILL.md | scripts/ | references/ | templates/template-lk.xlsx
│   ├── red-flag-operasional/    SKILL.md | scripts/ | references/peta-gejala.json
│   ├── cek-kesiapan-data/       SKILL.md | scripts/ | references/pertanyaan.json
│   ├── board-brief/             SKILL.md | scripts/ | templates/brief.md
│   ├── tampilan-direksi/        SKILL.md | scripts/preferensi.py | references/prinsip-tampilan-direksi.md
│   ├── data-emiten/             SKILL.md | scripts/ (tv_emiten.mjs, ringkas_emiten.py, package.json)
│   ├── laporan-analisa/         SKILL.md | scripts/ | references/ | templates/ (laporan.html, template-paket-data.xlsx)
│   ├── uji-ketahanan-kas/       SKILL.md | scripts/ | references/skema-skenario.md
│   ├── kondisi-ekonomi-daerah/  SKILL.md | scripts/ | references/ | templates/template-ekonomi-daerah.csv
│   └── efisiensi-sdm-departemen/ SKILL.md | scripts/ | references/ | templates/template-sdm-departemen.csv
├── sample-data/                 4 case industri FIKTIF
├── tools/                       analisis_lengkap.py | buat_zip.py | format_data.py | konversi_data.py | portal_peserta.py
└── tests/                       python -m unittest discover tests -v
```

Kebutuhan: Python 3.8+. Node.js ≥ 20 hanya untuk `data-emiten`. `openpyxl` untuk Excel; `pypdf`/`pymupdf`/`pdfplumber` (salah satu, opsional) untuk
mengekstrak teks PDF.

## Batas cakupan

Skill ini menemukan **gejala** dan menyusun laporan dari data yang tersedia. Menjawab *mengapa*, pelanggan mana,
produk mana, lini mana, proses mana, membutuhkan data operasional yang terintegrasi. Tanpa data itu, laporan
menandai bagian terkait sebagai **PERLU DATA**.

## Lisensi

Lihat [`LICENSE`](LICENSE). Bebas dipakai untuk keperluan internal perusahaan; tidak untuk dijual ulang.

---

Disusun dengan TQ Board Insight | totalquality.co.id

## Kontribusi

Lihat [CONTRIBUTING.md](CONTRIBUTING.md).
