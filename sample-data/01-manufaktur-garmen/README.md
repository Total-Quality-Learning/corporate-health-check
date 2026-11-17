# PT Contoh Garmen Nusantara (FIKTIF)

**Industri:** Manufaktur Garmen (pakaian jadi, order ekspor & domestik)
**Lokasi:** Kabupaten Contoh, Jawa Barat (fiktif) · **Berdiri:** 2009 · **Karyawan:** ±1.450

> Seluruh data di folder ini **fiktif** dan dibuat untuk pelatihan. Bukan data perusahaan nyata.

## Gambaran singkat

Pabrik garmen dengan 6 lini jahit. Penjualan dan laba terus naik, tetapi kas operasi berbalik negatif sejak 2025 karena persediaan (WIP & barang jadi) dan piutang distributor domestik menumpuk.

| Ringkasan (Rp juta) | 2023 | 2024 | 2025 |
|---|---:|---:|---:|
| Pendapatan | 165.624 | 182.688 | 203.741 |
| Laba bersih | 10.063 | 12.597 | 14.880 |
| Arus kas operasi | 14.288 | 16.587 | -3.085 |

## Berkas

| Berkas | Isi | Dipakai oleh skill |
|---|---|---|
| `LK-2025-PT-Contoh-Garmen-Nusantara.pdf` | Laporan keuangan tahunan 2025 & 2024 (posisi keuangan, laba rugi, perubahan ekuitas, arus kas, catatan) | `baca-laporan-keuangan` (latihan ekstraksi PDF) |
| `LK-Tahunan.xlsx` | LK 2023-2025 dalam format template | `baca-laporan-keuangan` |
| `lk-tahunan.json` | LK 2023-2025 dalam format standar | `baca-laporan-keuangan`, `red-flag-operasional`, `board-brief` |
| `Data-Keuangan-Bulanan.xlsx` | Laba rugi, neraca, arus kas bulanan Jan 2023 - Okt 2026 + target (RKAP) 2026 | `laporan-analisa` |
| `jawaban-cek-kesiapan.json` | Contoh jawaban kuesioner | `cek-kesiapan-data` |

## Coba

```
python tools/analisis_lengkap.py sample-data/01-manufaktur-garmen/lk-tahunan.json --kesiapan B,B,A,B,A,B,A,C
python skills/laporan-analisa/scripts/susun_laporan.py sample-data/01-manufaktur-garmen/Data-Keuangan-Bulanan.xlsx --out laporan-01-manufaktur-garmen.html
```

Atau minta asisten AI: *"Analisis LK PT Contoh Garmen Nusantara lalu buat laporan analisa bulan Oktober 2026."*

Disusun dengan TQ Board Insight · totalquality.co.id
