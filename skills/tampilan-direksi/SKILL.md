---
name: tampilan-direksi
description: Menanyakan dan menyimpan preferensi tampilan pengguna (untuk siapa laporannya, narasi singkat/detail/checklist, grafik atau penjelasan grafik, fokus, tingkat istilah, panjang, format) ke preferensi.json, serta memberi aturan tampilan yang ramah direksi dan top management. Gunakan di awal sesi analisis laporan keuangan, saat pengguna berkata "buat lebih ringkas/lebih detail/pakai checklist/pakai grafik", atau sebelum menjalankan skill baca-laporan-keuangan, red-flag-operasional, board-brief, laporan-analisa, dan data-emiten.
---

# Tampilan Direksi & Preferensi Pengguna

Direksi tidak membaca laporan — mereka **memindai** lalu memutuskan. Skill ini memastikan setiap keluaran
mengikuti selera pembacanya, dan menyimpannya agar tidak perlu ditanya ulang.

## Kapan dijalankan

- **Awal sesi**, sebelum skill analisis lain dijalankan — kecuali `preferensi.json` sudah ada (tampilkan ringkasannya
  dan tanya "masih sama?" dalam satu kalimat).
- Kapan pun pengguna meminta perubahan gaya ("lebih singkat", "pakai checklist", "tanpa grafik", "jelaskan grafiknya").

## Langkah kerja

1. **Tanya 4 pertanyaan inti sekaligus** (teks dari skrip agar konsisten):
   `python scripts/preferensi.py --pertanyaan`
   Sajikan sebagai pilihan bernomor; minta jawaban singkat seperti `1A, 2C, 3B, 4A`. Jangan menanyakan pertanyaan
   lanjutan kecuali pengguna tertarik — pakai bawaan.
   - Jika pengguna tidak mau menjawab / "terserah": pakai preset `direksi`.
   - Jika pengguna menyebut perannya ("saya komisaris", "untuk bank"), tawarkan preset yang sesuai:
     `direksi`, `komisaris`, `keuangan`, `bank`.
2. **Simpan:** `python scripts/preferensi.py --jawaban 1A,2C,3B,4A --out preferensi.json`
   (atau `--preset komisaris --set visual=grafik --out preferensi.json`).
3. **Konfirmasi** dalam 2–4 baris ringkasan (keluaran skrip), lalu lanjutkan ke tugas utama.
4. **Terapkan** pada skill lain — semua skrip menerima `--preferensi preferensi.json`:

| Preferensi | baca-laporan-keuangan | visualisasi | board-brief | laporan-analisa | data-emiten |
|---|---|---|---|---|---|
| `gaya_narasi` | `--gaya ringkas/detail/checklist` | – | `--gaya` | tombol Narasi/Checklist | gaya tabel |
| `visual` | – | `--mode grafik/penjelasan/keduanya` | – | – | – |
| `istilah` | penjelasan istilah | `--istilah` | – | – | – |
| `mode_laporan` | – | – | – | `--mode direksi/lengkap` | – |
| `metode_rasio` | `--metode akhir/rata-rata` | – | – | – | – |

5. **Ubah kapan saja.** Jika pengguna berkata "lebih singkat", ubah satu kunci:
   `python scripts/preferensi.py --tampilkan preferensi.json` lalu simpan ulang dengan `--set gaya_narasi=ringkas`.

## Aturan tampilan ramah direksi (wajib untuk semua jawaban di chat)

Lihat `references/prinsip-tampilan-direksi.md`. Ringkasnya:

1. **Kesimpulan dulu**, angka pendukung kemudian. Kalimat pertama = jawaban.
2. **Maksimal 3 pesan utama** per jawaban; sisanya ke lampiran/berkas.
3. **Angka dibulatkan & bersatuan jelas**: Rp203,7 M; 24,2%; 92 hari. Jangan tampilkan 203.741.000.000.
4. **Setiap angka punya pembanding** (tahun lalu, target, atau ambang) dan **arah** (naik/turun, baik/buruk).
5. **Status konsisten**: ✅ aman · ⚠️ perhatian · ❌ kritis.
6. **Judul grafik = kesimpulan** ("Laba naik 18%, kas turun"), bukan nama grafik ("Grafik laba").
7. **Istilah teknis dijelaskan** satu frasa saat pertama muncul (kecuali `istilah = teknis`).
8. **Selalu akhiri dengan tindakan**: pertanyaan untuk tim minggu ini atau keputusan yang perlu diambil.
9. **Jangan menjual.** Rekomendasi berupa kategori solusi; tanpa nama produk/vendor/konsultan.
