# Panduan Pemetaan Akun LK Indonesia → Format Standar

Gunakan saat mengekstrak dari PDF atau Excel dengan format bebas.

## Prinsip

1. **Ambil angka dari laporan utama**, bukan dari catatan, kecuali pos memang hanya ada di catatan (mis. penyusutan).
2. **Satu satuan.** Jika LK "dalam jutaan Rupiah", tulis apa adanya dan isi `"satuan": "juta"`. Jangan mencampur.
3. **Tanda kurung = negatif.** `(155.463)` = -155.463. Untuk pos beban, tulis angka **positif** (155463).
4. **Titik = pemisah ribuan** di LK Indonesia. `204.288` = dua ratus empat ribu dua ratus delapan puluh delapan.
5. **Kolom periode**: LK biasanya menyajikan tahun berjalan di kiri, pembanding di kanan. Format standar meminta
   urutan **terlama → terbaru**. Periksa ulang setelah menulis JSON.
6. **Pakai subtotal yang disajikan** (`total_aset_lancar`, `total_aset`, `total_liabilitas`, dll.) apa adanya;
   jangan menjumlah ulang sendiri. Skrip yang mengecek konsistensinya.
7. Jika ada pos yang tidak yakin, **tanyakan ke pengguna**, jangan menebak.

## Sinonim yang sering muncul

| Di LK | Kunci |
|---|---|
| Kas dan bank; Kas dan setara kas | `kas_dan_setara_kas` |
| Piutang usaha - pihak ketiga + pihak berelasi (neto setelah cadangan kerugian) | `piutang_usaha` |
| Persediaan - neto | `persediaan` |
| Uang muka, biaya dibayar di muka, pajak dibayar di muka, piutang lain-lain, aset lancar lain | `aset_lancar_lainnya` (jumlahkan) |
| Aset tetap - neto | `aset_tetap_neto` |
| Aset pajak tangguhan, properti investasi, aset hak guna, aset tak berwujud, uang jaminan | `aset_tidak_lancar_lainnya` (jumlahkan) |
| Utang bank jangka pendek; pinjaman bank; cerukan; **bagian lancar** utang bank jangka panjang | `utang_bank_jangka_pendek` (jumlahkan) |
| Utang usaha - pihak ketiga + berelasi | `utang_usaha` |
| Beban akrual, utang pajak, uang muka pelanggan, utang lain-lain, liabilitas sewa jangka pendek | `liabilitas_jangka_pendek_lainnya` (jumlahkan) |
| Utang bank jangka panjang - setelah dikurangi bagian lancar | `utang_bank_jangka_panjang` |
| Liabilitas imbalan kerja, liabilitas pajak tangguhan, liabilitas sewa jangka panjang | `liabilitas_jangka_panjang_lainnya` (jumlahkan) |
| Jumlah ekuitas (termasuk kepentingan nonpengendali) | `total_ekuitas` |
| Penjualan neto; Pendapatan usaha; Pendapatan kontrak | `pendapatan` |
| Beban pokok penjualan / pendapatan; Harga pokok penjualan | `beban_pokok_penjualan` |
| Beban penjualan; Beban penjualan dan distribusi | `beban_penjualan` |
| Beban umum dan administrasi | `beban_umum_administrasi` |
| Beban keuangan; Beban bunga | `beban_bunga` |
| Laba (rugi) selisih kurs, pendapatan bunga, laba penjualan aset tetap, lain-lain neto | `pendapatan_beban_lain` (jumlahkan, bertanda) |
| Laba tahun berjalan; Laba neto | `laba_bersih` |
| Arus kas neto diperoleh dari (digunakan untuk) aktivitas operasi | `arus_kas_operasi` |
| Perolehan aset tetap | `belanja_modal` (positif) |
| Kas dan setara kas akhir tahun | `kas_akhir` |

## Hal yang sering salah

- Mengambil "Jumlah liabilitas dan ekuitas" sebagai `total_liabilitas` → neraca otomatis tidak seimbang.
- Lupa bagian lancar utang jangka panjang → utang bank terlihat lebih kecil.
- Memakai laba yang dapat diatribusikan ke pemilik entitas induk padahal ekuitas termasuk nonpengendali. Konsistenlah:
  pakai **laba tahun berjalan** (total) bersama **total ekuitas**.
- Kolom tahun tertukar → semua perubahan berbalik arah. Selalu cek: apakah total aset terbaru = angka di kolom
  tahun berjalan pada LK?
