# PT Contoh Presisi Teknik (FIKTIF)

**Industri:** Manufaktur Komponen Logam Presisi (stamping & machining) untuk Otomotif
**Lokasi:** Kawasan Industri Contoh, Banten (fiktif) | **Berdiri:** 2001 | **Karyawan:** sekitar 410

> Seluruh data di folder ini **fiktif** dan dibuat untuk pelatihan. Bukan data perusahaan nyata.

## Gambaran singkat

Pemasok komponen logam untuk perakitan otomotif (job order). Investasi lini CNC baru 2024-2025 dibiayai pinjaman bank, tetapi volume order turun mengikuti pasar otomotif. Utilisasi mesin rendah, beban tetap & bunga naik, margin tertekan, dan rasio utang mendekati batas covenant bank.

| Ringkasan (Rp juta) | 2023 | 2024 | 2025 |
|---|---:|---:|---:|
| Pendapatan | 151.227 | 159.380 | 158.925 |
| Laba bersih | 13.462 | 14.070 | 6.278 |
| Arus kas operasi | 23.331 | 23.389 | 18.722 |

## Berkas

| Berkas | Isi | Dipakai oleh skill |
|---|---|---|
| `LK-2025-PT-Contoh-Presisi-Teknik.pdf` | Laporan keuangan tahunan 2025 & 2024 (posisi keuangan, laba rugi, perubahan ekuitas, arus kas, catatan) | `baca-laporan-keuangan` (latihan ekstraksi PDF) |
| `LK-Tahunan.xlsx` | LK 2023-2025 dalam format template | `baca-laporan-keuangan` |
| `lk-tahunan.json` | LK 2023-2025 dalam format standar | `baca-laporan-keuangan`, `red-flag-operasional`, `board-brief` |
| `Data-Keuangan-Bulanan.xlsx` | Laba rugi, neraca, arus kas bulanan Jan 2023 - Okt 2026 + target (RKAP) 2026 | `laporan-analisa` |
| `jawaban-cek-kesiapan.json` | Contoh jawaban kuesioner | `cek-kesiapan-data` |

## Coba

```
python tools/analisis_lengkap.py sample-data/04-komponen-logam/lk-tahunan.json --kesiapan C,C,C,C,B,C,B,C
python skills/laporan-analisa/scripts/susun_laporan.py sample-data/04-komponen-logam/Data-Keuangan-Bulanan.xlsx --out laporan-04-komponen-logam.html
```

Atau minta asisten AI: *"Analisis LK PT Contoh Presisi Teknik lalu buat laporan analisa bulan Oktober 2026."*

Disusun dengan TQ Board Insight | totalquality.co.id
