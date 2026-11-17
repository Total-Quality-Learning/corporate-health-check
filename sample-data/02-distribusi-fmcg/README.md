# PT Contoh Niaga Distribusi (FIKTIF)

**Industri:** Distribusi Barang Konsumsi (FMCG) ke toko tradisional & ritel modern
**Lokasi:** Kota Contoh, Jawa Timur (fiktif) · **Berdiri:** 2004 · **Karyawan:** ±620

> Seluruh data di folder ini **fiktif** dan dibuat untuk pelatihan. Bukan data perusahaan nyata.

## Gambaran singkat

Distributor 6 prinsipal FMCG. Ekspansi ke ritel modern sejak 2025 mendongkrak omzet, tetapi potongan & retur naik, piutang ritel modern lambat, stok mendekati kedaluwarsa bertambah, dan kebutuhan modal kerja ditutup pinjaman bank sehingga bunga menggerus laba.

| Ringkasan (Rp juta) | 2023 | 2024 | 2025 |
|---|---:|---:|---:|
| Pendapatan | 528.119 | 575.416 | 642.491 |
| Laba bersih | 14.857 | 16.045 | 14.838 |
| Arus kas operasi | 8.643 | 12.513 | -16.940 |

## Berkas

| Berkas | Isi | Dipakai oleh skill |
|---|---|---|
| `LK-2025-PT-Contoh-Niaga-Distribusi.pdf` | Laporan keuangan tahunan 2025 & 2024 (posisi keuangan, laba rugi, perubahan ekuitas, arus kas, catatan) | `baca-laporan-keuangan` (latihan ekstraksi PDF) |
| `LK-Tahunan.xlsx` | LK 2023-2025 dalam format template | `baca-laporan-keuangan` |
| `lk-tahunan.json` | LK 2023-2025 dalam format standar | `baca-laporan-keuangan`, `red-flag-operasional`, `board-brief` |
| `Data-Keuangan-Bulanan.xlsx` | Laba rugi, neraca, arus kas bulanan Jan 2023 - Okt 2026 | `laporan-analisa` |
| `jawaban-cek-kesiapan.json` | Contoh jawaban kuesioner | `cek-kesiapan-data` |

## Coba

```
python tools/analisis_lengkap.py sample-data/02-distribusi-fmcg/lk-tahunan.json --kesiapan B,A,B,A,A,A,A,B
python skills/laporan-analisa/scripts/susun_laporan.py sample-data/02-distribusi-fmcg/Data-Keuangan-Bulanan.xlsx --out laporan-02-distribusi-fmcg.html
```

Atau minta asisten AI: *"Analisis LK PT Contoh Niaga Distribusi lalu buat laporan analisa bulan Oktober 2026."*

Disusun dengan TQ Board Insight · totalquality.co.id
