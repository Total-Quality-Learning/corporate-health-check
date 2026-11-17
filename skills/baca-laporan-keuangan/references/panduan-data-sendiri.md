# Memakai Laporan Keuangan Perusahaan Anda Sendiri

Data contoh PT Contoh Garmen (fiktif) cocok untuk belajar. Setelah paham alurnya, Anda bisa memakai LK perusahaan
sendiri. Panduan ini memastikan hasilnya akurat **dan** data Anda tetap terlindungi.

## 1. Pilih tingkat kerahasiaan

| Jalur | Yang dilihat AI | Cocok untuk |
|---|---|---|
| **A. Data samaran** (disarankan) | Rasio identik, tetapi nilai absolut, nama perusahaan, dan tahun disamarkan | LK yang belum dipublikasikan / internal |
| **B. Data asli** | Seluruh angka asli | LK yang sudah publik, atau jika kebijakan perusahaan dan paket AI Anda mengizinkan |

Sebelum memilih jalur B, cek kebijakan internal perusahaan tentang penggunaan AI dan pengaturan privasi layanan AI
yang Anda pakai (mis. apakah percakapan dipakai untuk melatih model, dan paket apa yang dipakai: pribadi/bisnis).

## 2. Siapkan data (pilih salah satu)

**Cara 1, Isi template Excel (paling akurat)**
1. Salin `templates/template-lk.xlsx`.
2. Isi sheet `Info`, `Neraca`, `LabaRugi`, `ArusKas`. Kolom `kode` jangan diubah. Baris bertanda `*` wajib.
3. Minimal 2 periode, urut dari terlama. Beban diisi angka positif. Satu satuan untuk semua angka.
4. Ubah ke JSON: `python scripts/baca_excel.py LK-saya.xlsx --out lk.json`

**Cara 2, Dari PDF LK**
Minta AI mengekstrak dengan skill ini. AI akan menampilkan tabel hasil ekstraksi; **periksa** terutama total aset,
laba bersih, dan arus kas operasi sebelum lanjut. Catatan: dengan cara ini AI membaca angka asli (jalur B), kecuali
Anda menyamarkan PDF lebih dulu, yang sulit dilakukan. Untuk data rahasia, gunakan Cara 1 + jalur A.

## 3. Samarkan (jalur A): dijalankan sendiri, TANPA AI

**Dengan Python (staf IT/finance):**
```
python scripts/samarkan_lk.py lk.json --out lk-samaran.json --samarkan-periode
```
Script mengalikan **semua** angka dengan satu faktor acak dan mengganti nama perusahaan serta label tahun
(menjadi T-1, T). Faktor hanya tampil di layar Anda; catat sendiri jika ingin mengembalikan angka asli.
Bagikan **hanya** `lk-samaran.json` ke AI.

**Tanpa Python (langsung di Excel):**
1. Ketik satu angka acak di sel kosong, mis. `0,37`, lalu Copy sel tersebut.
2. Blok semua angka di sheet `Neraca`, `LabaRugi`, `ArusKas` (bukan kolom kode/uraian dan bukan baris `hari_periode`).
3. Paste Special → Multiply → OK. Hapus sel faktor.
4. Ganti nama perusahaan di sheet `Info` dan judul kolom tahun (mis. `T-1`, `T`).
5. Simpan sebagai file baru, lalu unggah file baru itu.

Mengapa aman untuk analisis? Semua rasio (margin, DIO, DSO, current ratio, DER, dll.) adalah perbandingan dua angka.
Jika semua angka dikali faktor yang sama, hasil baginya tidak berubah.

Yang **tidak** ikut tersamarkan: pola dan rasio itu sendiri. Untuk perusahaan yang sangat mudah dikenali, rasio pun
bisa menjadi petunjuk; pertimbangkan sebelum membagikan hasilnya ke pihak lain.

## 4. Jalankan analisis

Di asisten AI yang sudah memasang skill ini, cukup minta:
> "Analisis laporan keuangan di lk-samaran.json dengan skill baca-laporan-keuangan, lalu cek red flag operasionalnya."

Atau langsung dengan Python:
```
python scripts/hitung_rasio.py lk-samaran.json --out-json rasio.json --out-md rasio.md
```

## 5. Data bulanan untuk laporan rapat direksi (skill laporan-analisa)

Jika perusahaan punya laba rugi, neraca, dan arus kas **bulanan**, isi
`skills/laporan-analisa/templates/template-paket-data.xlsx` (minimal 13 bulan). Samarkan dulu bila rahasia:
```
python skills/laporan-analisa/scripts/samarkan_paket.py Data-Bulanan.xlsx --out Data-Bulanan-samaran.xlsx
```
Semua angka uang dikali satu faktor; nama perusahaan, pelanggan, dan pemasok diganti kode. Rasio, hari modal kerja,
dan status KPI tetap sama. Sheet data operasional (piutang per pelanggan, produk, pemasok, stok, KPI pabrik) boleh
dikosongkan, laporan akan menandai bagian itu "PERLU DATA".

## 6. Jika validasi gagal

`VALIDASI GAGAL` biasanya berarti salah ketik, kolom tahun tertukar, atau subtotal yang salah ambil (lihat
`pemetaan-akun.md`). Perbaiki file input; jangan mengubah angka sekadar agar seimbang.
