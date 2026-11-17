# Skema skenario.json

```json
{
  "horizon_bulan": 6,
  "plafon_tersedia": 2500,
  "batas_dscr": 1.25,
  "batas_icr": 2,
  "kas_minimum": null,
  "skenario": [
    {"nama": "Dasar"},
    {"nama": "Penjualan turun 20% selama 3 bulan", "penjualan_pct": -20, "durasi_bulan": 3},
    {"nama": "Resesi", "penjualan_pct": -15, "harga_bahan_pct": 8, "tambah_dso_hari": 20, "bunga_poin": 1.5},
    {"nama": "Mesin rusak bulan ke-2", "belanja_tambahan": 1200, "mulai_bulan": 2}
  ]
}
```

Boleh juga berupa daftar skenario saja (`[ {...}, {...} ]`). Semua nilai uang memakai **satuan paket data**
(mis. juta rupiah).

## Kunci guncangan

| Kunci | Arti | Cara dihitung |
|---|---|---|
| `penjualan_pct` | Perubahan penjualan (%), negatif = turun | Δ pendapatan × margin kontribusi (pendapatan - bahan - beban penjualan), tiap bulan |
| `harga_bahan_pct` | Kenaikan harga bahan tanpa kenaikan harga jual (%) | bahan × % × (1 + perubahan volume), tiap bulan |
| `biaya_tetap_pct` | Kenaikan biaya tetap tunai (%) | (upah + overhead + beban umum) × %, tiap bulan |
| `bunga_poin` | Kenaikan suku bunga (poin per tahun) | utang bank × poin / 12, tiap bulan |
| `tambah_dso_hari` | Penagihan piutang molor (hari) | pendapatan bulanan × hari / 30,4, **sekali** |
| `kurang_dpo_hari` | Pemasok minta bayar lebih cepat (hari) | bahan bulanan × hari / 30,4, **sekali** |
| `tambah_dio_hari` | Persediaan menumpuk (hari) | (bahan + biaya tetap) bulanan × hari / 30,4, **sekali** |
| `belanja_tambahan` | Pengeluaran sekali (satuan paket) | dikurangkan di bulan mulai |
| `mulai_bulan` | Bulan ke- guncangan mulai | bawaan 1 |
| `durasi_bulan` | Lama guncangan berulang | bawaan sampai akhir horizon |

## Status

- **KRITIS**: kas akhir di bawah kas minimum, atau kas pernah negatif.
- **WASPADA**: kas akhir di bawah 1,5 × kas minimum.
- **AMAN**: selain itu.

Dengan horizon 3 bulan, lima skenario pertama bawaan memberi angka yang sama dengan bagian *Uji ketahanan kas* di
laporan **laporan-analisa** (diuji otomatis).
