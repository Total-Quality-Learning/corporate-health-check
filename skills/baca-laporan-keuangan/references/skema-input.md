# Skema Input Format Standar (JSON)

Semua angka dalam **satu satuan** (mis. jutaan Rupiah). Setiap pos berupa objek `{label_periode: angka}`.
Periode diurutkan dari **terlama ke terbaru**. Tanda `*` = wajib.

```json
{
  "perusahaan": "PT Nama Perusahaan",
  "mata_uang": "IDR",
  "satuan": "juta",
  "periode": ["2024", "2025"],
  "hari_periode": {"2024": 365, "2025": 365},
  "sumber": "LK audit 2025, hal. 3-8",
  "neraca":    { "kas_dan_setara_kas": {"2024": 10299, "2025": 8941}, "...": {} },
  "laba_rugi": { "pendapatan": {"2024": 182400, "2025": 204288}, "...": {} },
  "arus_kas":  { "arus_kas_operasi": {"2024": 13999, "2025": -1358}, "...": {} }
}
```

`hari_periode` opsional (default 365). Isi untuk LK interim, mis. 9 bulan = 273, 1 kuartal = 90/91/92.

## `neraca`

| Kunci | Keterangan |
|---|---|
| `kas_dan_setara_kas`* | Kas dan setara kas |
| `piutang_usaha`* | Piutang usaha neto (pihak ketiga + berelasi) |
| `persediaan`* | Persediaan neto (bahan baku, WIP, barang jadi) |
| `aset_lancar_lainnya` | Semua aset lancar lain (uang muka, biaya dibayar di muka, pajak dibayar di muka, dll.) |
| `total_aset_lancar`* | Jumlah aset lancar |
| `aset_tetap_neto` | Aset tetap setelah akumulasi penyusutan |
| `aset_tidak_lancar_lainnya` | Aset tidak lancar lain |
| `total_aset`* | Jumlah aset |
| `utang_bank_jangka_pendek` | Utang bank jangka pendek **termasuk** bagian lancar utang bank jangka panjang |
| `utang_usaha`* | Utang usaha (pemasok) |
| `liabilitas_jangka_pendek_lainnya` | Beban akrual, utang pajak, uang muka pelanggan, dll. |
| `total_liabilitas_jangka_pendek`* | Jumlah liabilitas jangka pendek |
| `utang_bank_jangka_panjang` | Utang bank jangka panjang setelah dikurangi bagian lancar |
| `liabilitas_jangka_panjang_lainnya` | Imbalan kerja, sewa, dll. |
| `total_liabilitas`* | Jumlah liabilitas |
| `total_ekuitas`* | Jumlah ekuitas (termasuk kepentingan nonpengendali) |
| `saldo_laba` | Saldo laba (opsional; dipakai skor Altman Z'') |
| `total_liabilitas_dan_ekuitas` | Jika diisi, dicek sama dengan total aset |

## `laba_rugi`

| Kunci | Keterangan |
|---|---|
| `pendapatan`* | Penjualan / pendapatan neto |
| `beban_pokok_penjualan`* | HPP, **angka positif** |
| `laba_kotor` | Jika kosong = pendapatan - HPP |
| `beban_penjualan` | Positif |
| `beban_umum_administrasi` | Positif |
| `beban_usaha` | Total beban usaha; jika kosong = penjualan + umum |
| `laba_usaha` | Jika kosong = laba kotor - beban usaha |
| `beban_bunga` | Beban keuangan/bunga, positif |
| `pendapatan_beban_lain` | Neto lain-lain; negatif jika beban |
| `laba_sebelum_pajak` | |
| `beban_pajak` | Positif |
| `laba_bersih`* | Laba tahun berjalan (sebelum penghasilan komprehensif lain) |
| `penyusutan` | Dari catatan atau arus kas |

## `arus_kas`

| Kunci | Keterangan |
|---|---|
| `arus_kas_operasi`* | Arus kas neto dari aktivitas operasi (negatif jika keluar) |
| `arus_kas_investasi` | |
| `arus_kas_pendanaan` | |
| `belanja_modal` | Perolehan aset tetap, **angka positif** |
| `kas_akhir` | Jika diisi, dicek sama dengan kas di neraca |

## Aturan validasi (oleh `hitung_rasio.py`)

**Error (rasio tidak dihitung):** total aset ≠ liabilitas + ekuitas (toleransi: maks(2 unit, 0,1% total aset));
total liabilitas & ekuitas yang disajikan ≠ total aset; aset lancar > total aset; liabilitas jangka pendek > total
liabilitas; kas + piutang + persediaan > aset lancar; pendapatan ≤ 0; kolom wajib kosong.

**Peringatan (rasio tetap dihitung):** rincian aset lancar ≠ total; laba kotor disajikan ≠ pendapatan - HPP;
kas akhir arus kas ≠ kas neraca; ekuitas ≤ 0; pos beban bernilai negatif (dibalik otomatis).
