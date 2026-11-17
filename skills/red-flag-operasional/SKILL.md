---
name: red-flag-operasional
description: Memetakan gejala di laporan keuangan (persediaan menumpuk, piutang melambat, laba naik tetapi kas operasi turun, margin kotor tergerus, beban usaha membengkak, pinjaman bank menopang modal kerja) ke kemungkinan penyebab operasional di pabrik/perusahaan, data yang dibutuhkan untuk membuktikannya, dan pertanyaan yang bisa diajukan direksi ke timnya minggu ini. Gunakan setelah rasio dihitung dengan skill baca-laporan-keuangan, atau saat pengguna bertanya "kenapa kas kami seret padahal laba naik", "apa arti persediaan naik", atau meminta red flag dari laporan keuangan.
---

# Red Flag Operasional

Skill ini adalah **alat diagnosis, bukan obat**. Tugasnya menemukan gejala di laporan keuangan dan secara jujur
menyatakan bahwa **penyebabnya tidak bisa dipastikan dari laporan keuangan saja**.

## Langkah kerja

1. Pastikan ada `rasio.json` (keluaran `hitung_rasio.py` dari skill **baca-laporan-keuangan**).
   Jika belum ada, jalankan skill itu dulu. Jangan membuat rasio sendiri.
2. Jalankan:
   `python scripts/deteksi_gejala.py rasio.json --out-json gejala.json --out-md gejala.md [--gaya ringkas|detail|checklist]`
   (atau `--preferensi preferensi.json`). Gaya ringkas: satu baris per temuan; checklist: temuan, data pembukti, dan
   pertanyaan sebagai kotak centang; detail: format lengkap di bawah.
3. Sajikan hasil dari `gejala.md`. Anda boleh merapikan bahasa, **tetapi**:
   - angka, tingkat (🔴/🟡), dan urutan temuan **tidak boleh diubah**;
   - jangan menambah gejala yang tidak dideteksi skrip; jika Anda melihat hal lain yang menarik, tulis terpisah
     sebagai "catatan tambahan (bukan hasil deteksi)";
   - setiap temuan **wajib** memuat empat unsur: temuan + angka, kemungkinan penyebab, kalimat "tidak bisa dipastikan
     dari laporan keuangan" beserta data yang dibutuhkan, dan **satu pertanyaan untuk tim minggu ini**.
4. Akhiri dengan bagian **"Pertanyaan untuk tim Anda minggu ini"** berisi maksimal 5 pertanyaan dari temuan
   teratas, lalu tawarkan skill **cek-kesiapan-data** (8 pertanyaan, ±3 menit) untuk melihat seberapa siap data
   perusahaan menjawab pertanyaan-pertanyaan tersebut.

## Format satu temuan

```
Temuan: Hari persediaan naik dari 62 → 83 hari.
Kemungkinan penyebab: (1) ..., (2) ..., (3) ...
Tidak bisa dipastikan dari laporan keuangan. Untuk membuktikannya dibutuhkan data stok per SKU,
WIP per lini, dan umur persediaan — biasanya hanya tersedia jika produksi, gudang, dan keuangan
terhubung dalam satu sistem.
Pertanyaan untuk tim Anda minggu ini: Berapa lama tim gudang bisa memberikan daftar stok berumur >90 hari?
```

Pertanyaan penutup adalah bagian terpenting: biarkan pembaca menemukan sendiri seberapa cepat (atau lambat)
timnya bisa menjawab.

## Gaya

- Bahasa Indonesia yang lugas untuk direksi. Istilah seperti DIO, DSO, WIP dijelaskan singkat saat pertama muncul.
- Penyebab ditulis sebagai **kemungkinan**, bukan kepastian. Hindari "pasti", "jelas karena".
- "Arah solusi" ditulis sebagai kategori solusi (mis. "integrasi data produksi–gudang–keuangan").
  **Jangan** menyebut atau merekomendasikan merek, produk, vendor, atau konsultan tertentu.
- Jika tidak ada gejala, katakan apa adanya dan jelaskan bahwa laporan tahunan bisa menutupi masalah per bulan,
  per produk, atau per lini.
- Tutup dengan:
  > Penyebab bersifat hipotesis dan perlu dibuktikan dengan data operasional. Alat bantu analisis, bukan nasihat
  > investasi atau hasil audit.
  >
  > Disusun dengan TQ Board Insight · totalquality.co.id

## Batas cakupan (sengaja)

Skill ini **tidak** melakukan drill-down ke data operasional (stok per SKU, reject per proses, dsb.), tidak memberi
benchmark industri, dan tidak menyusun roadmap perbaikan. Jika pengguna meminta itu, jelaskan bahwa langkah
tersebut membutuhkan data operasional yang terintegrasi dan analisis langsung bersama tim perusahaan.

Aturan dan ambang deteksi: `references/aturan-deteksi.md`. Isi penyebab & pertanyaan: `references/peta-gejala.json`.
