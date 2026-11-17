# Skema Paket Data Bulanan

Satu file Excel (`templates/template-paket-data.xlsx`). Semua angka uang dalam **satu satuan** (isi di `Info.satuan`,
mis. `juta`). Judul kolom bulan berformat `YYYY-MM`. Beban, belanja modal, cicilan, dividen, cadangan piutang, dan
akumulasi penyusutan diisi **positif**.

## Sheet wajib

**Info**, `perusahaan`, `industri`, `mata_uang` (IDR), `satuan`, `bulan_aktif` (YYYY-MM, bulan laporan), `sumber`.

**LabaRugi** (kolom = bulan)

| kode | isi |
|---|---|
| `penjualan_bruto`, `potongan_dan_retur` | opsional; untuk melihat tren potongan/retur |
| `pendapatan` * | pendapatan neto |
| `hpp_bahan` * | bahan baku / barang dagangan |
| `hpp_upah`, `hpp_overhead`, `hpp_penyusutan` | komponen HPP lain |
| `beban_penjualan` *, `beban_umum_adm` * | beban usaha |
| `beban_penyusutan_usaha` | penyusutan di luar HPP |
| `pendapatan_beban_lain` | neto, negatif jika beban |
| `beban_bunga`, `beban_pajak` | |
| `laba_bersih` * | untuk pengecekan (gerbang G5) |

**Neraca** (kolom = bulan, **mulai 1 bulan sebelum** bulan pertama L/R)

`kas`*, `piutang_usaha_bruto`*, `cadangan_kerugian_piutang`, `persediaan_bahan_baku`, `persediaan_barang_dalam_proses`,
`persediaan_barang_jadi`*, `uang_muka_dan_dibayar_dimuka`, `aset_tetap_perolehan`*, `akumulasi_penyusutan`*,
`aset_tidak_lancar_lain`, `utang_usaha`*, `utang_bank_pendek`, `bagian_lancar_utang_panjang`, `beban_akrual`,
`utang_pajak`, `utang_bank_panjang` (setelah bagian lancar), `liabilitas_imbalan_kerja`, `modal_disetor`*, `saldo_laba`*.

**ArusKas** (kolom = bulan)

`arus_kas_operasi`*, `belanja_modal`, `penerimaan_pinjaman_panjang`, `pembayaran_pinjaman_panjang`,
`perubahan_utang_bank_pendek` (bertanda), `dividen`, `kas_akhir` (pengecekan).

## Sheet opsional

| Sheet | Isi | Dipakai untuk |
|---|---|---|
| `Target` | `pendapatan`, `laba_kotor`, `beban_usaha`, `laba_bersih` per bulan | Pembanding target |
| `Ambang_KPI` | `kpi`, `nama`, `waspada`, `kritis`, `arah` (tinggi/rendah) | Ambang kebijakan perusahaan |
| `Piutang_Pelanggan` | per pelanggan: wilayah, berelasi, batas kredit, termin, penjualan YTD, saldo per umur, margin | Bagian 7.1, cerita piutang/konsentrasi |
| `Penjualan_Produk` | per bulan × produk: pendapatan, HPP, volume | Bagian 7.2, cerita margin |
| `Pemasok` | pembelian YTD, perubahan harga 12 bln, hari bayar | Bagian 7.3 |
| `Persediaan_Rincian` | per item: jenis (bahan/wip/jadi), nilai per umur | Bagian 7.4, cerita persediaan |
| `Operasional` | KPI bulanan: kode, uraian, satuan, arah, nilai per bulan | Bagian 7.5 |
| `Produksi_Lini` | per lini/gudang: rencana, realisasi, WIP, reject, utilisasi | Bagian 7.6 |

Pada sheet tabel operasional: baris 1 = kode kolom (jangan diubah), baris 2 = judul tampilan, data mulai baris 3.

Kode KPI untuk `Ambang_KPI`: `gross_margin`, `ebitda_margin`, `net_margin`, `rev_growth`, `roe_ltm`, `roa_ltm`,
`cash_conversion`, `dso`, `dio`, `dpo`, `ccc`, `current_ratio`, `quick_ratio`, `net_debt_ebitda`, `icr`.
