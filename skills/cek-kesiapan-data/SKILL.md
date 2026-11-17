---
name: cek-kesiapan-data
description: Kuesioner singkat 8 pertanyaan non-teknis (tutup buku, HPP per order, posisi stok, pencatatan reject, jumlah file Excel, integrasi produksi–gudang–keuangan, konsistensi angka, KPI produksi harian) yang menghasilkan skor kesiapan data dan sistem perusahaan Level 1–4 beserta 2–3 area terlemah. Gunakan saat pengguna ingin tahu seberapa siap data perusahaannya untuk menjawab pertanyaan di balik laporan keuangan, setelah skill red-flag-operasional, atau saat pengguna meminta "cek kesiapan data".
---

# Cek Kesiapan Data & Sistem

Delapan pertanyaan, ±3 menit, untuk melihat apakah data perusahaan cukup siap menjawab pertanyaan
"**kenapa**" di balik angka laporan keuangan.

## Langkah kerja

1. Tampilkan kuesioner. Ambil teksnya dari skrip agar selalu sama:
   `python scripts/skor_kesiapan.py --pertanyaan`
   (Jika tidak bisa menjalankan Python, pakai teks persis dari `references/pertanyaan.json`.)
   - Ajukan **semua 8 pertanyaan sekaligus** dan minta pengguna menjawab dengan huruf, mis. `A,B,B,C,A,B,A,C`.
   - Tekankan: jawab sesuai kondisi **saat ini**, bukan rencana. Jika ragu di antara dua pilihan, pilih yang lebih rendah.
   - Jangan menebak jawaban yang tidak diberikan; tanyakan ulang nomor yang kosong.
2. Hitung skor:
   `python scripts/skor_kesiapan.py --jawaban <8 huruf> --out-json kesiapan.json --out-md kesiapan.md`
3. Sajikan isi `kesiapan.md`: level, penjelasan, tabel jawaban, 2–3 area terlemah, dan keempat level.
   Level dan skor **tidak boleh diubah**.
4. Hubungkan dengan hasil **red-flag-operasional** bila ada: untuk setiap area terlemah, sebutkan gejala keuangan
   mana yang paling sulit dibuktikan karena kelemahan itu (mis. visibilitas stok lemah → kenaikan hari persediaan
   tidak bisa ditelusuri ke produk/lini).
5. Tawarkan skill **board-brief** untuk merangkum semuanya dalam 1 halaman untuk direksi.

## Gaya

- Netral dan tidak menghakimi. Level 1–2 adalah kondisi yang umum, bukan kegagalan.
- "Arah solusi" berupa kategori, **jangan** menyebut merek, produk, vendor, atau konsultan.
- `kode_ringkas` (mis. `L2-1.5.7`) hanya dibagikan jika pengguna mau, misalnya untuk polling anonim saat sesi.
- Tutup dengan:
  > Versi singkat dengan skoring sederhana tanpa bobot; gambaran awal, bukan hasil asesmen lengkap.
  >
  > Disusun dengan TQ Board Insight · totalquality.co.id

## Aturan skoring (transparan)

A = 1, B = 2, C = 3, D = 4. Rata-rata 8 skor, tanpa bobot:
Level 1 < 1,75 · Level 2 < 2,50 · Level 3 < 3,25 · Level 4 ≥ 3,25.
Area prioritas = skor ≤ 2 terendah (maks. 3; seri → nomor pertanyaan lebih kecil). Jika tidak ada skor ≤ 2,
ditampilkan 2 area terendah sebagai "area untuk peningkatan berikutnya".
