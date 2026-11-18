---
name: kondisi-ekonomi-daerah
description: Mengambil data makro ekonomi (World Bank API tanpa key, opsional BPS WebAPI atau CSV/JSON daerah) lalu menilai risiko 5 dimensi ekonomi daerah (permintaan PDRB, inflasi, kenaikan UMP/UMK, suku bunga, dan kurs), memetakan paparan risikonya langsung ke rasio keuangan perusahaan (rasio.json atau laporan.json), serta menurunkan skenario siap pakai untuk stress test kas (uji-ketahanan-kas). Gunakan saat pengguna menanyakan forecast risiko ekonomi daerah, dampak inflasi/UMP/suku bunga/kurs ke keuangan, atau ingin menyusun skenario risiko makro sebelum rapat direksi.
---

# Kondisi Ekonomi Daerah & Forecast Risiko Keuangan

Skill ini menghubungkan **kondisi ekonomi daerah** (PDRB, inflasi, UMP/UMK, suku bunga, kurs) dengan **struktur keuangan perusahaan** untuk memetakan risiko dan menurunkan skenario stress test kas.
Semua skor risiko, paparan, dan skenario dihitung skrip Python deterministik.

## Syarat mutlak: skrip harus benar-benar dijalankan

Skrip dianggap tersedia **hanya jika** berkas `scripts/ambil_makro.py` dan `scripts/analisa_risiko_ekonomi.py` benar-benar ada di lingkungan Anda dan Anda menjalankannya. Menulis kode sendiri untuk meniru skrip **tidak dihitung**, begitu juga mengarang angka makro atau membuat perkiraan risiko sendiri tanpa skrip.

Jika skrip tidak bisa dijalankan, **berhenti** dan jangan menampilkan skor risiko, angka inflasi/PDRB, atau simulasi skenario sendiri. Jangan pernah menulis bahwa skrip sudah dijalankan atau berkas sudah dibuat bila itu tidak terjadi. Lakukan ini saja:

1. Katakan: "Analisis risiko ekonomi daerah belum bisa dijalankan di sini karena skrip kondisi-ekonomi-daerah tidak bisa dijalankan di lingkungan ini. Angkanya hanya boleh dari skrip agar bisa dipertanggungjawabkan."
2. Minta pengguna melengkapi `templates/template-ekonomi-daerah.csv` (dengan angka resmi BPS/BI/Pemda) dan berikan perintah CLI yang dapat dijalankan di komputernya sendiri.

## Langkah kerja (interaktif)

1. **Tanya konteks wilayah & risiko** sebelum menarik/menghitung:
   - Provinsi / kabupaten / kota mana yang menjadi basis operasional, produksi, dan pasar utama perusahaan?
   - Apakah perusahaan memiliki eksposur bahan impor (kurs USD), tenaga kerja padat karya (UMP/UMK), atau utang berbunga mengambang?
   - Apakah pengguna sudah memiliki angka daerah terbaru (PDRB, inflasi daerah, kenaikan UMP/UMK dari BPS/Pemda)? Jika belum, jelaskan bahwa data nasional World Bank API akan dipakai sebagai **proksi awal** dan pos daerah yang kosong ditandai **PERLU DATA**.
2. **Kumpulkan data ekonomi (`ekonomi.json`):**
   - Tarik proksi makro nasional (tanpa API key) + nama daerah:
     `python scripts/ambil_makro.py --daerah "Jawa Barat" --out ekonomi.json`
   - Jika pengguna mengisi `templates/template-ekonomi-daerah.csv` atau memberi angka resmi:
     `python scripts/ambil_makro.py --input daerah.csv --out ekonomi.json` (atau lewat `--pdrb-pct`, `--inflasi-daerah-pct`, `--kenaikan-ump-pct`, `--suku-bunga-pct`).
   - Jika lingkungan tanpa internet dan data hanya dari berkas lokal: tambah `--offline`.
   - Opsional jika pengguna memiliki API key BPS: tambah `--bps-key <key> --bps-domain <kode_domain>`.
3. **Analisa risiko & hubungkan ke keuangan perusahaan:**
   `python scripts/analisa_risiko_ekonomi.py ekonomi.json [--rasio rasio.json|laporan.json] [--preferensi preferensi.json] --out-md risiko-ekonomi.md --out-json risiko-ekonomi.json --out-skenario skenario-makro.json`
4. **Sajikan hasil dengan kecerdasan konsultatif:**
   - Mulai dari **putusan ringkas** kondisi 5 dimensi ekonomi daerah dan saluran paparan terbesar terhadap keuangan perusahaan (dari `risiko-ekonomi.md` / `risiko-ekonomi.json`).
   - Jelaskan **mengapa** risiko tersebut relevan bagi perusahaan (mis. mengaitkan inflasi/kurs ke margin kotor, perlambatan PDRB ke DSO piutang, kenaikan UMP ke beban usaha, atau suku bunga ke DER & interest coverage).
   - Sebutkan secara jujur bagian yang masih berstatus **PERLU DATA** atau memakai **proksi nasional** (bukan angka spesifik daerah).
   - Tawarkan **langkah lanjutan**: konfirmasikan `skenario-makro.json` dengan pengguna, lalu jalankan skill **uji-ketahanan-kas** (`python ../uji-ketahanan-kas/scripts/uji_ketahanan_kas.py <paket.xlsx> --skenario skenario-makro.json`) untuk melihat dampak langsung ke saldo kas dan kovenan bank.
5. Tutup dengan catatan cakupan dan footer:

> Alat bantu analisis, bukan proyeksi resmi otoritas atau nasihat investasi.
>
> Disusun dengan TQ Board Insight | totalquality.co.id
