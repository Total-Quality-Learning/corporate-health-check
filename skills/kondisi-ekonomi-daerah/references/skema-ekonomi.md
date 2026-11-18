# Skema Data Kondisi Ekonomi Daerah

Data kondisi ekonomi dapat berasal dari gabungan:
1. **API Makro Publik (World Bank API, tanpa API key)** lewat `scripts/ambil_makro.py` untuk indikator makro nasional (PDB, inflasi IHK, suku bunga pinjaman, kurs USD, pengangguran).
2. **Data Regional / Daerah** dari berkas `templates/template-ekonomi-daerah.csv`, JSON, argumen CLI, atau opsional BPS WebAPI (`--bps-key`).

## Kunci Indikator di `ekonomi.json`

| Kunci | Arti | Satuan | Sumber Umum |
|---|---|---|---|
| `daerah` | Nama provinsi / kabupaten / kota | teks | Input pengguna |
| `pdrb_pct` | Pertumbuhan PDRB daerah YoY | `%` | BPS Provinsi / Kabupaten / Kota |
| `inflasi_daerah_pct` | Inflasi IHK daerah YoY | `%` | BPS Daerah / TPID |
| `kenaikan_ump_pct` | Kenaikan UMP / UMK tahunan | `%` | SK Gubernur / Disnaker |
| `pengangguran_daerah_pct` | Tingkat Pengangguran Terbuka (TPT) | `%` | BPS (Sakernas) |
| `suku_bunga_pct` | Suku bunga acuan / bunga kredit | `%` | Bank Indonesia / OJK / Bank |
| `kurs_usd` | Nilai tukar IDR per USD | `IDR` | Bank Indonesia / World Bank |
| `catatan_risiko_daerah` | Risiko spesifik wilayah (cuaca, logistik, perda) | teks | BMKG / Pemda / internal |

Jika indikator daerah belum tersedia, nilainya dibiarkan `null` agar ditandai **PERLU DATA** oleh skrip (tidak ditebak). Untuk PDRB, inflasi, pengangguran, bunga, dan kurs, skrip dapat memakai data makro nasional sebagai **proksi awal** dan menandai secara eksplisit bahwa angka tersebut adalah proksi nasional, bukan angka spesifik daerah.
