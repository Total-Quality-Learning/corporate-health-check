---
name: efisiensi-sdm-departemen
description: Menanyakan struktur organisasi dan jumlah karyawan (total maupun per departemen), menghitung rasio produktivitas dan beban dalam Rp per karyawan (pendapatan, laba kotor, laba bersih, beban usaha, dan biaya SDM per orang) dari rasio.json atau laporan.json, serta menyusun rekomendasi KPI prioritas dan arah budgeting per departemen sesuai gejala keuangan perusahaan. Gunakan saat menganalisis efisiensi organisasi, menyusun RKAP/budget tahun depan, atau menetapkan KPI tiap departemen.
---

# Efisiensi SDM, Rasio Rp per Karyawan, & KPI Budgeting Departemen

Skill ini menghubungkan **struktur organisasi & jumlah karyawan** dengan **kinerja laporan keuangan** untuk menghitung produktivitas Rp per karyawan dan merumuskan KPI serta arah budgeting tiap departemen.
Semua rasio Rp per karyawan dan porsi departemen dihitung oleh skrip Python deterministik.

## Syarat mutlak: skrip harus benar-benar dijalankan

Skrip dianggap tersedia **hanya jika** berkas `scripts/analisa_sdm_budget.py` benar-benar ada di lingkungan Anda dan Anda menjalankannya. Menulis kode sendiri untuk meniru skrip **tidak dihitung**, begitu juga menghitung Rp per karyawan sendiri atau mengarang angka jumlah karyawan.

Jika skrip tidak bisa dijalankan, **berhenti** dan jangan menampilkan angka Rp per karyawan sendiri. Jangan pernah menulis bahwa skrip sudah dijalankan atau berkas sudah dibuat bila itu tidak terjadi. Lakukan ini saja:

1. Katakan: "Analisis efisiensi SDM dan KPI budgeting belum bisa dihitung di sini karena skrip analisa_sdm_budget.py tidak bisa dijalankan di lingkungan ini. Angkanya hanya boleh dari skrip agar bisa dipertanggungjawabkan."
2. Ajukan pertanyaan struktur organisasi dan jumlah karyawan di bawah, lalu berikan `templates/template-sdm-departemen.csv` beserta perintah CLI yang bisa dijalankan pengguna di komputernya sendiri.

## Langkah kerja (interaktif, wajib tanya dulu)

1. **Tanya struktur organisasi & jumlah karyawan** (kecuali pengguna sudah memberikannya):
   - Apa saja **departemen utama** di struktur organisasi perusahaan (mis. Produksi/QC, Penjualan/Marketing, Gudang/Logistik, Keuangan/Akuntansi, HR/Umum/IT)?
   - Berapa **jumlah karyawan** periode berjalan dan tahun lalu (total perusahaan atau rincian per departemen)?
   - Apakah tersedia **total biaya SDM (gaji, tunjangan, lembur)** per departemen atau usulan anggaran tahun depan? (Jika belum ada, jelaskan bahwa pos ini akan ditandai **PERLU DATA**.)
   - Apa prioritas manajemen tahun depan (ekspansi penjualan, efisiensi biaya tetap, perbaikan penagihan kas, atau kontrol persediaan)?
2. **Siapkan bahan input:**
   - Pastikan `rasio.json` (dari **baca-laporan-keuangan**) atau `laporan.json` (dari **laporan-analisa**) sudah tersedia.
   - Jika pengguna mengisi rincian per departemen, simpan sebagai CSV mengikuti `templates/template-sdm-departemen.csv` (lihat `references/skema-sdm-budget.md`), atau gunakan argumen ringkas `--karyawan` dan `--departemen`.
3. **Jalankan skrip:**
   ```
   python scripts/analisa_sdm_budget.py --rasio <rasio.json|laporan.json> \
       [--input sdm-departemen.csv | --karyawan 120 --karyawan-lalu 112 --departemen "Produksi:70,Penjualan:20,Gudang:15,Keuangan & Umum:15"] \
       [--preferensi preferensi.json] --out-md sdm-budget.md --out-json sdm-budget.json
   ```
4. **Sajikan hasil dengan analisis strategis:**
   - Mulai dengan **putusan 10 detik**: tren **Pendapatan & Laba Bersih per karyawan** (naik atau turun dibanding tahun lalu, dalam satuan `JT`, `.000`, atau `M` per orang).
   - Jelaskan benang merah antara **struktur headcount** dan **gejala keuangan** (mis. apakah penambahan karyawan lebih cepat dari pertumbuhan laba kotor, atau departemen mana yang perlu menahan rekrutmen sampai utilisasi dan DSO/DIO membaik).
   - Sajikan tabel/daftar **KPI prioritas dan arah budgeting per departemen** untuk bahan penyusunan RKAP/anggaran direksi, serta tandai bagian biaya SDM yang kosong sebagai **PERLU DATA**.
5. Tutup dengan catatan cakupan dan footer:

> Alat bantu perencanaan manajemen; angka target dan pagu final ditetapkan oleh direksi.
>
> Disusun dengan TQ Board Insight | totalquality.co.id
