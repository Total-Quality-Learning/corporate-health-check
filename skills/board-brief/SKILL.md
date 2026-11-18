---
name: board-brief
description: Menyusun ringkasan 1 halaman untuk direksi (board brief) dari hasil analisis laporan keuangan, red flag operasional, dan cek kesiapan data, berisi kondisi singkat, indikator utama berstatus hijau/kuning/merah, tiga temuan terpenting, lima pertanyaan untuk CFO/tim minggu ini, serta tingkat kesiapan data. Gunakan saat pengguna meminta ringkasan untuk direksi, bahan rapat direksi, executive summary, atau "board brief" dari laporan keuangan.
---

# Board Brief

Ringkasan **satu halaman** yang bisa dibaca direksi dalam 2 menit.

## Langkah kerja

1. Pastikan bahan tersedia (jalankan skill terkait jika belum):
   - `rasio.json` dari **baca-laporan-keuangan**, wajib
   - `gejala.json` dari **red-flag-operasional**, sangat disarankan
   - `kesiapan.json` dari **cek-kesiapan-data**, opsional
2. Susun draf:
   `python scripts/susun_brief.py --rasio rasio.json --gejala gejala.json --kesiapan kesiapan.json --out-md brief.md --out-html brief.html`
   - Gaya checklist (temuan & pertanyaan sebagai kotak centang): tambah `--gaya checklist`, atau `--preferensi preferensi.json`
     dari skill **tampilan-direksi**.
3. **Kondisi singkat** (bagian 1) boleh Anda tulis ulang agar lebih mengalir, maksimal 3 kalimat, **hanya memakai
   angka yang sudah ada di brief**. Lalu jalankan ulang dengan `--kondisi "teks baru"` agar file `.md` dan `.html`
   ikut diperbarui. Bagian lain tidak diubah.
4. Sajikan `brief.md` ke pengguna dan sebutkan bahwa `brief.html` bisa dibuka di browser lalu dicetak/disimpan
   sebagai PDF (Ctrl+P).

## Struktur (lihat `templates/brief.md`)

1. Kondisi singkat (3 kalimat)
2. Indikator utama dengan status Aman / Perhatian / Kritis
3. Tiga temuan terpenting
4. Lima pertanyaan untuk CFO / tim minggu ini
5. Kesiapan data & sistem, **hanya bila** `kesiapan.json` atau hasil skill cek-kesiapan-data tersedia. Jika tidak
   ada, hilangkan bagian ini; jangan menilai kesiapan data sendiri.
6. Disclaimer + footer

## Ambang status indikator (ambang umum, bukan benchmark industri)

| Indikator | Aman | Perhatian | Kritis |
|---|---|---|---|
| Pendapatan (pertumbuhan) | ≥ 0% | -5% s.d. 0% | < -5% |
| Laba bersih (pertumbuhan) | ≥ 0% | -10% s.d. 0% | < -10% atau rugi |
| Arus kas operasi | ≥ 0 | - | < 0 |
| Kas operasi / laba bersih | ≥ 1,0x | 0,5-1,0x | < 0,5x |
| Margin laba kotor (perubahan) | > -1 poin | -1 s.d. -2 poin | ≤ -2 poin |
| DIO, DSO (kenaikan) | < +10 hari dan < +15% | ≥ +10 hari atau ≥ +15% | ≥ +20 hari atau ≥ +30% |
| Current ratio | ≥ 1,5x | 1,0-1,5x | < 1,0x |
| Interest coverage | ≥ 3x | 1,5-3x | < 1,5x |
| DER | ≤ 1x | 1-2x | > 2x |

## Jika skrip tidak bisa dijalankan

1. Sampaikan satu kalimat bahwa brief disusun manual oleh AI dan belum diverifikasi skrip.
2. Pakai hanya angka yang ada di `rasio.json` / `gejala.json` / hasil skill sebelumnya di percakapan. Status
   indikator ditentukan dengan tabel ambang di atas, tanpa pengecualian.
3. Struktur tetap enam bagian di atas, termasuk aturan bagian 5. Jangan pernah menulis bahwa skrip sudah dijalankan atau berkas sudah dibuat bila itu tidak terjadi.

## Aturan

- Jangan menambah angka, temuan, atau rekomendasi yang tidak ada di bahan.
- **Penyebab selalu hipotesis.** Untuk setiap temuan tulis "penyebab belum bisa dipastikan dari laporan keuangan;
  butuh data seperti ...". Jangan memakai kata "akibat", "disebabkan oleh", atau "karena" untuk penyebab
  operasional yang belum dibuktikan.
- Jangan membesar-besarkan kondisi (mis. "krisis likuiditas") bila indikatornya tidak menunjukkan itu. Pakai istilah
  status yang sama: aman, perhatian, kritis.
- Bagian 6 memakai teks berikut, disalin persis:
  > Alat bantu analisis, bukan nasihat investasi atau hasil audit. Penyebab yang disebut bersifat hipotesis dan perlu
  > dibuktikan dengan data operasional.
  >
  > Disusun dengan TQ Board Insight | totalquality.co.id
- Bahasa lugas, kalimat pendek, tanpa jargon yang tidak dijelaskan.
- Jangan menyebut merek, produk, vendor, atau konsultan tertentu. Footer standar sudah cukup.
- Jika data input berlabel "disamarkan", sebut satuannya "unit samaran" dan jangan menafsirkan nilai absolutnya.
