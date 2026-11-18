---
name: tampilan-direksi
description: Menanyakan dan menyimpan preferensi tampilan pengguna (untuk siapa laporannya, narasi singkat/detail/checklist, grafik atau penjelasan grafik, fokus, tingkat istilah, panjang, format) ke preferensi.json, serta memberi aturan tampilan yang ramah direksi dan top management. Gunakan di awal sesi analisis laporan keuangan, saat pengguna berkata "buat lebih ringkas/lebih detail/pakai checklist/pakai grafik", atau sebelum menjalankan skill baca-laporan-keuangan, red-flag-operasional, board-brief, laporan-analisa, dan data-emiten.
---

# Tampilan Direksi & Preferensi Pengguna

Direksi tidak membaca laporan, mereka **memindai** lalu memutuskan. Skill ini memastikan setiap keluaran
mengikuti selera pembacanya, dan menyimpannya agar tidak perlu ditanya ulang.

## Kapan dijalankan

- **Awal sesi**, sebelum skill analisis lain dijalankan, kecuali `preferensi.json` sudah ada (tampilkan ringkasannya
  dan tanya "masih sama?" dalam satu kalimat).
- Kapan pun pengguna meminta perubahan gaya ("lebih singkat", "pakai checklist", "tanpa grafik", "jelaskan grafiknya").

## Langkah kerja

1. **Tanya 4 pertanyaan inti sekaligus, lalu tunggu jawabannya** sebelum menjalankan skill lain, juga bila
   pengguna meminta preferensi dan analisis dalam satu pesan. Teks dari skrip agar konsisten:
   `python scripts/preferensi.py --pertanyaan`
   Bila skrip tidak bisa dijalankan, pakai teks yang sama di bawah ini (dijaga sama oleh tes):

```text
**1. Laporan ini untuk siapa?**
   A. Direksi / pemilik, keputusan cepat  ← bawaan
   B. Dewan komisaris, pengawasan & risiko
   C. Manajer keuangan / CFO, rinci & teknis
   D. Bank / investor, kelayakan & utang

**2. Bentuk narasi yang diinginkan?**
   A. Singkat, rasio kunci + 3 hal yang perlu perhatian  ← bawaan
   B. Detail, semua rasio, perhitungan, dan penjelasan
   C. Checklist, setiap indikator sebagai kotak centang aman/perlu perhatian

**3. Bentuk visualisasi?**
   A. Grafik saja, dengan judul berupa kesimpulan
   B. Penjelasan detail tiap grafik (teks), tanpa gambar
   C. Grafik + penjelasan detail di bawahnya  ← bawaan
   D. Tanpa visual, tabel & teks saja

**4. Fokus utama?**
   A. Semua aspek  ← bawaan
   B. Kas & modal kerja
   C. Margin & laba
   D. Utang & kemampuan bayar
   E. Efisiensi & produktivitas
```

   Minta jawaban singkat seperti `1A, 2C, 3B, 4A`. Jangan menanyakan pertanyaan lanjutan kecuali pengguna tertarik,
   pakai bawaan.
   - Jika pengguna tidak mau menjawab / "terserah": pakai preset `direksi`.
   - Jika pengguna menyebut perannya ("saya komisaris", "untuk bank"), tawarkan preset yang sesuai:
     `direksi`, `komisaris`, `keuangan`, `bank`.
2. **Simpan:** `python scripts/preferensi.py --jawaban 1A,2C,3B,4A --out preferensi.json`
   (atau `--preset komisaris --set visual=grafik --out preferensi.json`).
3. **Konfirmasi** dalam 2-4 baris ringkasan (keluaran skrip), lalu lanjutkan ke tugas utama.
4. **Terapkan** pada skill lain, semua skrip menerima `--preferensi preferensi.json`:

| Preferensi | baca-laporan-keuangan | visualisasi | board-brief | laporan-analisa | data-emiten |
|---|---|---|---|---|---|
| `gaya_narasi` | `--gaya ringkas/detail/checklist` | - | `--gaya` | tombol Narasi/Checklist | gaya tabel |
| `visual` | - | `--mode grafik/penjelasan/keduanya` | - | - | - |
| `istilah` | penjelasan istilah | `--istilah` | - | - | - |
| `mode_laporan` | - | - | - | `--mode direksi/lengkap` | - |
| `metode_rasio` | `--metode akhir/rata-rata` | - | - | - | - |

   Bila skrip tidak bisa dijalankan, cukup ingat pilihan pengguna selama percakapan dan terapkan pada jawaban
   berikutnya. Jangan pernah menulis bahwa skrip sudah dijalankan atau berkas sudah dibuat bila itu tidak terjadi
   (termasuk `preferensi.json`).

5. **Ubah kapan saja.** Jika pengguna berkata "lebih singkat", ubah satu kunci:
   `python scripts/preferensi.py --tampilkan preferensi.json` lalu simpan ulang dengan `--set gaya_narasi=ringkas`.

## Aturan tampilan ramah direksi (wajib untuk semua jawaban di chat)

Lihat `references/prinsip-tampilan-direksi.md`. Ringkasnya:

1. **Kesimpulan dulu**, angka pendukung kemudian. Kalimat pertama = jawaban.
2. **Maksimal 3 pesan utama** per jawaban; sisanya ke lampiran/berkas.
3. **Angka dibulatkan & bersatuan jelas**: Rp203,7 M; 24,2%; 92 hari. Jangan tampilkan 203.741.000.000.
4. **Setiap angka punya pembanding** (tahun lalu, target, atau ambang) dan **arah** (naik/turun, baik/buruk).
5. **Status konsisten**: aman, perlu perhatian, kritis. Pakai kata, bukan emoji.
6. **Judul grafik = kesimpulan** ("Laba naik 18%, kas turun"), bukan nama grafik ("Grafik laba").
7. **Istilah teknis dijelaskan** satu frasa saat pertama muncul (kecuali `istilah = teknis`).
8. **Selalu akhiri dengan tindakan**: pertanyaan untuk tim minggu ini atau keputusan yang perlu diambil.
9. **Jangan menjual.** Rekomendasi berupa kategori solusi; tanpa nama produk/vendor/konsultan.
