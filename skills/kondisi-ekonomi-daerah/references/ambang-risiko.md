# Ambang Risiko Makro Daerah & Transmisi ke Keuangan

Semua penilaian dan penyusunan skenario dilakukan secara deterministik oleh `scripts/analisa_risiko_ekonomi.py`.

## 1. Ambang 5 Dimensi Risiko Daerah

| Dimensi | Indikator Utama | Aman | Perlu perhatian | Kritis |
|---|---|---|---|---|
| Permintaan & daya beli | Pertumbuhan PDRB (proksi: PDB) | >= 5,0% | 3,0% s.d. < 5,0% | < 3,0% |
| Tekanan harga & bahan baku | Inflasi IHK daerah (proksi: nasional) | <= 3,5% | > 3,5% s.d. 5,0% | > 5,0% |
| Tekanan biaya upah | Kenaikan UMP / UMK | <= 5,0% | > 5,0% s.d. 8,5% | > 8,5% |
| Biaya pendanaan & bunga | Suku bunga kredit / acuan | <= 8,5% (naik < 0,5 poin) | > 8,5%-10,5% atau naik >= 0,5 poin | > 10,5% atau naik >= 1,5 poin |
| Nilai tukar & rantai pasok | Pelemahan kurs YoY | <= 3,0% | > 3,0% s.d. 7,0% | > 7,0% |

Indikator yang kosong (termasuk `kenaikan_ump_pct` yang tidak tersedia dari API nasional) diberi status **Perlu data**.

## 2. Pemetaan Eksposur ke Keuangan Perusahaan (`rasio.json` / `laporan.json`)

| Saluran Transmisi | Indikator Perusahaan yang Dicek | Kondisi Rentan |
|---|---|---|
| Pendapatan & piutang | `dso`, pertumbuhan pendapatan | `dso >= 45` hari atau penjualan sudah negatif |
| Margin & bahan baku | `gross_margin` | `gross_margin < 25%` atau turun >= 1 poin YoY |
| Beban usaha & upah | `opex_ratio` | `opex_ratio >= 20%` |
| Utang & beban bunga | `der_berbunga`, `interest_coverage` / `icr`, `net_debt_ebitda` | `der_berbunga >= 0,5x` atau `icr < 3,0x` atau `net_debt_ebitda >= 2,5x` |
| Penyangga likuiditas | `current_ratio`, `cfo_to_ni` / `cash_conversion` | `current_ratio < 1,5x` atau `cfo_to_ni < 0,75x` |

## 3. Penurunan Skenario Stress Test Kas (`skenario-makro.json`)

Skrip menghasilkan 4 skenario siap pakai untuk `uji_ketahanan_kas.py`:
1. **Dasar**: tanpa guncangan tambahan.
2. **Tekanan Biaya Daerah**: `harga_bahan_pct` berasal dari inflasi daerah/nasional ditambah 50% porsi pelemahan kurs (minimal 3%, dibulatkan 0,5%); `biaya_tetap_pct` berasal dari 50% kenaikan UMP (jika tersedia, atau setengah inflasi).
3. **Perlambatan Daerah & Penagihan Molor**: `penjualan_pct` negatif (-5% s.d. -15% bergantung perlambatan PDRB/PDB) dan `tambah_dso_hari` (+7 s.d. +20 hari bergantung status permintaan).
4. **Gabungan Berat Daerah**: kombinasi tekanan permintaan, biaya bahan, biaya tetap, penagihan molor, dan `bunga_poin` (+1,0 s.d. +2,5 poin bergantung tekanan bunga).
