# Skema Data Struktur Organisasi, Karyawan, & Budgeting Departemen

Digunakan oleh `scripts/analisa_sdm_budget.py` bersama `rasio.json` (tahunan) atau `laporan.json` (bulanan).

## Kolom di `template-sdm-departemen.csv`

| Kolom | Wajib | Arti |
|---|---|---|
| `departemen` | Ya | Nama departemen/divisi sesuai struktur organisasi perusahaan |
| `kategori_fungsi` | Opsional | Salah satu: `produksi`, `penjualan`, `gudang_logistik`, `keuangan_adm`, `umum_it_hr`, `manajemen` (jika kosong ditebak dari nama departemen, atau `umum`) |
| `karyawan_kini` | Ya | Jumlah karyawan periode berjalan |
| `karyawan_lalu` | Opsional | Jumlah karyawan periode pembanding (tahun lalu) |
| `biaya_sdm_tahunan` | Opsional | Total biaya gaji, tunjangan, lembur departemen (satu satuan dengan laporan keuangan; jika kosong ditandai **PERLU DATA**) |
| `anggaran_tahun_depan` | Opsional | Usulan anggaran tahun depan departemen (jika kosong ditandai **PERLU DATA**) |
| `catatan` | Opsional | Keterangan peran/fokus operasional departemen |

## Rasio Rp per Karyawan yang Dihitung

1. **Pendapatan per karyawan** = `Pendapatan / Total karyawan`
2. **Laba kotor per karyawan** = `Laba kotor / Total karyawan`
3. **Laba bersih per karyawan** = `Laba bersih / Total karyawan`
4. **Beban usaha per karyawan** = `Beban usaha / Total karyawan`
5. **Biaya SDM per karyawan** = `Total biaya SDM / Total karyawan` (jika diisi)
6. **Porsi biaya SDM terhadap pendapatan & laba kotor (%)** (jika biaya SDM diisi)

## Prinsip Rekomendasi KPI & Budgeting per Departemen

Rekomendasi bersifat deterministik berdasarkan **kombinasi fungsi departemen + gejala keuangan aktual**:
- **Penjualan (`penjualan`)**: fokus pertumbuhan neto, margin per produk/pelanggan, dan DSO penagihan.
- **Produksi (`produksi`)**: fokus utilisasi, output per karyawan produksi, tingkat reject/waste, dan biaya konversi.
- **Gudang & Logistik (`gudang_logistik`)**: fokus hari persediaan (DIO), stok berumur >90/>180 hari, dan akurasi stok.
- **Keuangan & Administrasi (`keuangan_adm`)**: fokus DSO/DPO, kecepatan tutup buku, rekonsiliasi kas, dan rasio konversi kas.
- **HR, Umum, & IT (`umum_it_hr`)**: fokus rasio beban usaha (`opex_ratio`), produktivitas pendapatan per karyawan, dan disiplin lembur.
- **Manajemen (`manajemen`)**: fokus ROE/ROA, siklus konversi kas (CCC), dan alokasi belanja modal.
