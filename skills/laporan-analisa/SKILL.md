---
name: laporan-analisa
description: Menyusun laporan analisa keuangan & kinerja lengkap bergaya paket rapat direksi (HTML interaktif, bisa dicetak ke PDF) dari data laporan keuangan BULANAN, putusan & skor kesehatan, 5 cerita utama, 15 KPI berambang, analisa laba rugi/neraca/arus kas, selisih vs bulan lalu/tahun lalu/target, data operasional (piutang per pelanggan, margin produk, pemasok, umur stok, KPI pabrik), uji ketahanan kas, proyeksi kas 13 minggu, rencana kerja, dan lampiran rasio dengan rumus. Gunakan saat pengguna meminta laporan bulanan untuk direksi, paket rapat direksi, laporan pertanggungjawaban, atau analisa kinerja bulanan/triwulanan/YTD dari data Excel bulanan.
---

# Laporan Analisa (Paket Rapat Direksi)

Mengubah **paket data bulanan** menjadi laporan analisa lengkap. Semua angka, status, cerita, dan rencana kerja
disusun **skrip deterministik**. Anda tidak menghitung apa pun sendiri.

## Langkah kerja

1. **Siapkan paket data.**
   - Format: `templates/template-paket-data.xlsx` (skema: `references/skema-paket-data.md`).
   - Punya file **CSV atau Excel format bebas** bulanan? Konversi dulu dari root repo:
     `python tools/konversi_data.py <file.csv|file.xlsx> --jenis bulanan --out paket.xlsx`
     (tambah `--tulis-pemetaan pemetaan.json` bila ada akun yang perlu dipetakan manual).
   - Wajib: sheet `Info`, `LabaRugi`, `Neraca`, `ArusKas`, minimal 13 bulan (disarankan ≥ 22 bulan).
   - Opsional: `Target` (anggaran/RKAP), `Ambang_KPI` (kebijakan perusahaan), dan 6 tabel data operasional.
   - Contoh fiktif: `sample-data/<case>/Data-Keuangan-Bulanan.xlsx` (garmen, distribusi FMCG, makanan-minuman,
     komponen logam).
   - Jika pengguna hanya punya LK tahunan, arahkan ke skill **baca-laporan-keuangan** + **board-brief**.
2. **Cek isi paket:** `python scripts/baca_paket.py <paket.xlsx>`, sampaikan periode, ada/tidaknya target dan data
   operasional.
3. **Data rahasia?** Tawarkan penyamaran yang dijalankan pengguna sendiri **tanpa AI**:
   `python scripts/samarkan_paket.py <paket.xlsx> --out <paket-samaran.xlsx>` (rasio & status tetap sama).
4. **Susun laporan:**
   `python scripts/susun_laporan.py <paket.xlsx> --out laporan.html --json laporan.json`
   - **Exit code 2 = validasi gagal** (neraca tidak seimbang / periode tidak lengkap). **Berhenti**, sampaikan pesan,
     minta data diperbaiki. Jangan mengubah angka agar lolos.
5. **Sampaikan hasil** (format di bawah) dan sebutkan bahwa `laporan.html` dibuka di browser. Laporan dirancang
   untuk pembaca non-keuangan: tab **Ringkasan** (3 angka besar, lampu status, 3 hal yang perlu diketahui, usulan
   keputusan) → **Kesehatan** (15 indikator berbahasa awam) → **Arus kas** → **Tren** → **Laporan keuangan** →
   **Operasional** → **Rumus & data**. Tombol periode, pembanding, "Cara membaca", dan **Cetak / PDF** (mencetak semua
   tab) tersedia. Prinsip desain: `references/prinsip-desain-laporan.md`.
6. **Surat direksi (opsional).** Jika diminta, tulis draf surat ≤ 200 kata yang **hanya memakai angka dari
   `laporan.json`**, simpan sebagai `narasi.json` → `{"surat_direksi": "..."}`, lalu jalankan ulang langkah 4 dengan
   `--narasi narasi.json`. Tandai bagian yang harus diputuskan direksi dengan `[DIISI DIREKSI]`.

## Format jawaban di chat

1. Putusan 10 detik + skor kesehatan (dari ringkasan skrip).
2. 3-5 cerita utama: judul, fakta (angka dari skrip), penyebab. Jika penyebab berlabel **PERLU DATA**, sampaikan apa
   adanya, itu temuan penting, bukan kekurangan laporan.
3. Daftar bagian yang berstatus PERLU DATA dan data apa yang dibutuhkan.
4. Lokasi berkas `laporan.html`.
5. Disclaimer + footer:
   > Alat bantu analisis, bukan nasihat investasi atau hasil audit.
   >
   > Disusun dengan TQ Board Insight | totalquality.co.id

## Aturan

- Jangan menambah angka, cerita, atau penyebab yang tidak ada di keluaran skrip. Opsi tindakan adalah **kategori**
  untuk dibahas; pemilik dan tenggat selalu `[DIISI DIREKSI]`.
- Jangan menyebut merek, produk, vendor, atau konsultan tertentu.
- Ambang status bukan benchmark industri (lihat `references/kpi-dan-ambang.md`). Jika pengguna punya kebijakan
  internal (mis. covenant bank), sarankan mengisi sheet `Ambang_KPI`.
- Data berlabel disamarkan: sebut "unit samaran", jangan menebak angka asli atau identitas.
- Bagian **PERLU DATA** muncul bila tabel operasional kosong. Jelaskan bahwa pertanyaan "kenapa" di balik angka
  keuangan hanya bisa dijawab bila data penjualan, gudang, produksi, dan keuangan terhubung.

Struktur laporan: `references/struktur-laporan.md`.
