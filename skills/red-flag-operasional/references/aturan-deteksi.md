# Aturan Deteksi Gejala

Dibandingkan: dua periode terakhir di `rasio.json` (A = sebelumnya, B = terbaru).
Ambang adalah **ambang umum yang konservatif**, bukan benchmark industri. Tujuannya menandai perubahan yang layak
ditanyakan, bukan memberi nilai baik/buruk.

| Kode | Gejala | Kuning | Merah |
|---|---|---|---|
| `persediaan_menumpuk` | DIO naik | +10 hari atau +15% | +20 hari atau +30% |
| `margin_tergerus` | Margin laba kotor turun | ≤ -1,0 poin | ≤ -2,0 poin |
| `laba_naik_kas_turun` | Laba bersih naik, arus kas operasi turun | Laba naik & kas operasi turun | Laba positif tetapi kas operasi negatif, atau kas operasi/laba < 0,5x |
| `piutang_melambat` | DSO naik | +10 hari atau +15% | +20 hari atau +30% |
| `overhead_naik` | Beban usaha tumbuh lebih cepat dari pendapatan | selisih pertumbuhan ≥ 5 poin | ≥ 10 poin |
| `utang_menopang_modal_kerja` | Utang bank naik ≥ 25% saat kas operasi turun (modal kerja atau investasi yang belum menghasilkan) | terpenuhi | + interest coverage < 3x |
| `data_tidak_sinkron` | Peringatan validasi: rincian ≠ total, kas arus kas ≠ kas neraca | ada peringatan | - |

## Angka dampak kas (perkiraan sederhana)

- **Kas yang dapat dilepas jika DIO kembali** = (DIO B - DIO A) / hari periode × HPP B
- **Kas yang dapat dilepas jika DSO kembali** = (DSO B - DSO A) / hari periode × Pendapatan B
- **Laba kotor yang hilang** = (margin A - margin B) × Pendapatan B
- **Tambahan modal kerja** = Δ piutang + Δ persediaan - Δ utang usaha

Angka ini adalah ilustrasi besaran, bukan target. Dua angka "dapat dilepas" tidak boleh dijumlahkan dengan
"tambahan modal kerja" karena saling tumpang tindih.
