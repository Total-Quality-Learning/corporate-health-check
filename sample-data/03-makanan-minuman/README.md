# PT Contoh Pangan Sejahtera (FIKTIF)

**Industri:** Manufaktur Makanan Ringan & Minuman Kemasan
**Lokasi:** Kabupaten Contoh, Jawa Tengah (fiktif) | **Berdiri:** 2011 | **Karyawan:** sekitar 780

> Seluruh data di folder ini **fiktif** dan dibuat untuk pelatihan. Bukan data perusahaan nyata.

## Gambaran singkat

Pabrik makanan ringan dan minuman kemasan dengan 4 lini. Penjualan tumbuh tipis, tetapi margin kotor turun tajam karena kenaikan harga gula & tepung serta waste/reject yang meningkat di lini minuman setelah pergantian kemasan. Arus kas masih positif; masalah utamanya profitabilitas.

| Ringkasan (Rp juta) | 2023 | 2024 | 2025 |
|---|---:|---:|---:|
| Pendapatan | 261.605 | 278.658 | 295.805 |
| Laba bersih | 28.609 | 30.479 | 30.686 |
| Arus kas operasi | 41.268 | 43.531 | 44.819 |

## Berkas

| Berkas | Isi | Dipakai oleh skill |
|---|---|---|
| `LK-2025-PT-Contoh-Pangan-Sejahtera.pdf` | Laporan keuangan tahunan 2025 & 2024 (posisi keuangan, laba rugi, perubahan ekuitas, arus kas, catatan) | `baca-laporan-keuangan` (latihan ekstraksi PDF) |
| `LK-Tahunan.xlsx` | LK 2023-2025 dalam format template | `baca-laporan-keuangan` |
| `lk-tahunan.json` | LK 2023-2025 dalam format standar | `baca-laporan-keuangan`, `red-flag-operasional`, `board-brief` |
| `Data-Keuangan-Bulanan.xlsx` | Laba rugi, neraca, arus kas bulanan Jan 2023 - Okt 2026 | `laporan-analisa` |
| `jawaban-cek-kesiapan.json` | Contoh jawaban kuesioner | `cek-kesiapan-data` |

## Coba

```
python tools/analisis_lengkap.py sample-data/03-makanan-minuman/lk-tahunan.json --kesiapan C,B,C,B,C,B,C,B
python skills/laporan-analisa/scripts/susun_laporan.py sample-data/03-makanan-minuman/Data-Keuangan-Bulanan.xlsx --out laporan-03-makanan-minuman.html
```

Atau minta asisten AI: *"Analisis LK PT Contoh Pangan Sejahtera lalu buat laporan analisa bulan Oktober 2026."*

Disusun dengan TQ Board Insight | totalquality.co.id
