---
name: baca-laporan-keuangan
description: Membaca laporan keuangan (neraca, laba rugi, arus kas) dari PDF, Excel, atau JSON, memvalidasinya (neraca harus seimbang), lalu menghitung sekitar 28 rasio (likuiditas, profitabilitas & DuPont, leverage, efisiensi DIO/DSO/DPO/cash conversion cycle, kualitas laba & arus kas, skor Altman Z'') lengkap dengan perhitungannya secara deterministik dengan skrip Python, dan menyajikannya sebagai narasi singkat, detail, atau checklist serta grafik atau penjelasan grafik sesuai keinginan pengguna. Gunakan saat pengguna meminta analisis, ringkasan, atau rasio dari laporan keuangan perusahaan, termasuk laporan keuangan milik pengguna sendiri. Menjadi dasar untuk skill red-flag-operasional dan board-brief.
---

# Baca Laporan Keuangan

Skill ini mengubah laporan keuangan (LK) menjadi **format standar** lalu menghitung rasio dengan skrip.
**Angka selalu dari skrip; Anda hanya menulis narasi.** Jangan pernah menghitung rasio sendiri di kepala.

## Langkah kerja

0. **Tanya preferensi tampilan** (sekali per sesi; lewati bila `preferensi.json` sudah ada atau pengguna sudah
   menyebutnya). Ajukan dua pertanyaan bernomor dalam satu pesan:
   - **Visualisasi:** (A) grafik | (B) penjelasan detail tiap grafik (teks) | (C) grafik + penjelasan | (D) tanpa visual
   - **Narasi:** (A) singkat | (B) detail dengan perhitungan | (C) checklist
   Simpan dengan skill **tampilan-direksi** (`preferensi.py --set visual=... gaya_narasi=...`) bila tersedia; jika tidak,
   cukup ingat pilihan pengguna selama sesi. "Terserah" → visual C, narasi A.

1. **Kenali input.**
   - **Excel format template** (sheet `Info`, `Neraca`, `LabaRugi`, `ArusKas` dengan kolom `kode`):
     `python scripts/baca_excel.py <file.xlsx> --out lk.json`
   - **JSON format standar**: langsung ke langkah 3.
   - **PDF atau Excel bebas** (format perusahaan masing-masing): lakukan langkah 2.
   - Tidak ada file / pengguna hanya ingin mencoba: pakai data contoh fiktif di `sample-data/<case>/`, pilihan:
     `01-manufaktur-garmen`, `02-distribusi-fmcg`, `03-makanan-minuman`, `04-komponen-logam`
     (`lk-tahunan.json`, `LK-Tahunan.xlsx`, atau PDF `LK-2025-*.pdf` untuk latihan ekstraksi). Sebutkan bahwa datanya fiktif.
   - Pengguna punya data **bulanan** dan ingin laporan rapat direksi lengkap: arahkan ke skill **laporan-analisa**.

2. **Ekstraksi ke format standar** (hanya untuk PDF / Excel bebas).
   - Jika Anda tidak bisa membaca PDF langsung: `python scripts/ekstrak_teks_pdf.py <file.pdf> --out lk.txt`.
   - Petakan setiap akun ke kunci di `references/skema-input.md` dengan panduan `references/pemetaan-akun.md`.
   - Pakai **minimal 2 periode** dan **satu satuan** (mis. jutaan Rupiah). Beban ditulis **positif**.
   - Tulis `lk.json`, lalu **tampilkan tabel hasil ekstraksi ke pengguna** (akun asli → kunci → angka) sebelum lanjut.
     Tandai akun yang Anda gabungkan atau ragukan.

3. **Hitung & validasi:**
   `python scripts/hitung_rasio.py lk.json --out-json rasio.json --out-md rasio.md --gaya <ringkas|detail|checklist>`
   - Tambahkan `--preferensi preferensi.json` bila ada (gaya & metode diambil dari sana).
   - `--metode rata-rata` bila pengguna ingin membandingkan dengan angka yang dipublikasikan emiten/penyedia data
     (mereka umumnya memakai rata-rata saldo awal & akhir untuk ROE, ROA, dan perputaran).
   - **Exit code 2 = validasi gagal** (mis. neraca tidak seimbang). **Berhenti.** Tampilkan pesan error, tunjukkan
     angka yang dicurigai, dan minta pengguna mengonfirmasi/memperbaiki. **Jangan menebak atau "menyesuaikan" angka
     agar seimbang.**
   - Peringatan (bukan error) tetap disampaikan ke pengguna di bagian awal jawaban.

4. **Visualisasi** (sesuai preferensi; lewati bila "tanpa visual"):
   `python scripts/visualisasi.py rasio.json --out visual.html --mode <grafik|penjelasan|keduanya>`
   - `--mode penjelasan` dengan `--out visual.md` menghasilkan penjelasan grafik dalam Markdown untuk ditampilkan di chat.
   - Judul setiap grafik adalah kesimpulannya; sampaikan judul-judul itu sebagai poin utama.

5. **Sajikan hasil** dengan format di bawah. Simpan `rasio.json`: dipakai skill `red-flag-operasional`, `board-brief`,
   dan `data-emiten`.

## Format jawaban (ikuti gaya pilihan pengguna; angka tidak boleh diubah)

| Gaya | Isi jawaban |
|---|---|
| **Singkat** | 1 kalimat kesimpulan, tabel 8 rasio kunci (`rasio.md` gaya ringkas), 3 hal yang perlu perhatian, 1 pertanyaan untuk tim |
| **Detail** | Paragraf kondisi (≤ 4 kalimat), semua kelompok rasio **dengan kolom perhitungan**, DuPont, skor Altman Z'', 3-5 pengamatan |
| **Checklist** | Daftar `- [x]` / `- [ ]` per indikator dengan ambang (`rasio.md` gaya checklist), urut dari yang kritis, tindak lanjut sebagai checklist |

Untuk semua gaya:
1. Kalimat pertama = kesimpulan (aturan `tampilan-direksi`: angka dibulatkan, bersatuan, ada pembanding).
2. Bila pengguna bertanya "dari mana angka ini", tampilkan baris **perhitungan** dari `rasio.json`
   (mis. `5.280.548 ÷ 11.830.201 = 0,45x`).
3. 3-5 poin pengamatan (gaya detail). Setiap poin merujuk angka dari skrip. Jelaskan istilah teknis singkat saat pertama muncul,
   mis. "DIO (rata-rata hari barang tersimpan sebelum terjual)". Definisi: `references/definisi-rasio.md`.
4. Jika ada gejala (persediaan/piutang membengkak, kas operasi turun padahal laba naik, margin tergerus), tawarkan
   menjalankan skill **red-flag-operasional** untuk memetakan kemungkinan penyebab operasionalnya.
5. Tutup dengan disclaimer dan footer:
   > Alat bantu analisis, bukan nasihat investasi atau hasil audit. Angka bergantung pada kebenaran data input.
   >
   > Disusun dengan TQ Board Insight | totalquality.co.id

## Data milik pengguna sendiri

Pengguna boleh memakai LK perusahaannya sendiri. Ikuti `references/panduan-data-sendiri.md`, terutama:
- **Sebelum** pengguna mengunggah LK asli, ingatkan sekali secara singkat bahwa data akan diproses oleh layanan AI
  yang mereka pakai, dan tawarkan **mode samaran**: pengguna menjalankan sendiri
  `python scripts/samarkan_lk.py lk.json --out lk-samaran.json --samarkan-periode` di komputernya **tanpa AI**,
  lalu hanya membagikan `lk-samaran.json`. Semua rasio tetap sama persis; hanya nilai absolut, nama, dan tahun
  yang tersembunyi.
- Jika input berlabel "disamarkan", **jangan** mencoba menebak angka asli atau identitas perusahaan, dan jangan
  menyebut nilai absolut sebagai angka nyata (sebut "dalam unit samaran").
- Jangan menyimpan atau mengulang data pengguna di luar keperluan analisis ini.

## Batasan

- Bawaan: saldo neraca **akhir periode**. Dengan `--metode rata-rata`, ROA/ROE/perputaran/DIO/DSO/DPO memakai
  rata-rata saldo awal & akhir (periode pertama tetap saldo akhir). Uji akurasi pada 7 emiten IDX: perhitungan identik
  dengan hitung ulang independen; perbedaan dengan angka publikasi berasal dari definisi (lihat `definisi-rasio.md`).
- Skor Altman Z'' butuh `saldo_laba`; ini sinyal awal, bukan vonis kebangkrutan.
- Skill ini **tidak** memberi benchmark industri, rekomendasi investasi, atau opini audit.
- Laporan konsolidasi dengan kepentingan nonpengendali: masukkan seluruh ekuitas (termasuk nonpengendali) ke
  `total_ekuitas` agar neraca seimbang.
- Bank, asuransi, dan lembaga keuangan memakai struktur LK berbeda; rasio di skill ini tidak cocok untuk mereka.
