---
name: uji-ketahanan-kas
description: Uji ketahanan kas (cash stress test) dari data keuangan bulanan. Menghitung berapa lama kas perusahaan bertahan bila penjualan turun, harga bahan naik, penagihan piutang molor, pemasok minta bayar lebih cepat, suku bunga naik, atau gabungannya; kapan kas jatuh di bawah batas minimum; apakah kovenan bank (DSCR, interest coverage) masih terpenuhi; dan seberapa besar guncangan sampai kas habis (uji balik). Gunakan saat pengguna bertanya "kas kami tahan berapa bulan", "bagaimana jika penjualan turun 20%", "stress test kas", "uji ketahanan kas", atau menyiapkan rapat direksi/bank tentang likuiditas.
---

# Uji Ketahanan Kas

Skill ini menjawab satu pertanyaan direksi: **"Kalau keadaan memburuk, kas kita tahan sampai kapan?"**
Semua angka dihitung skrip Python yang deterministik. AI hanya menanyakan skenario dan menulis narasi.

## Syarat mutlak: skrip harus benar-benar dijalankan

Skrip dianggap tersedia **hanya jika** berkas `scripts/uji_ketahanan_kas.py` benar-benar ada di lingkungan Anda dan Anda menjalankannya. Menulis kode sendiri untuk meniru skrip **tidak dihitung**, begitu juga membaca Excel lalu menghitung sendiri.

Jika skrip tidak bisa dijalankan, **jangan membuat model kas sendiri**: tanpa perkiraan kas habis, kas minimum,
DSCR, status, atau rekomendasi. Jangan pernah menulis bahwa skrip sudah dijalankan atau berkas sudah dibuat bila itu tidak terjadi. Lakukan ini saja:

1. Katakan: "Uji ketahanan kas belum bisa dihitung di sini karena skrip uji_ketahanan_kas.py tidak bisa dijalankan
   di lingkungan ini. Angkanya hanya boleh dari skrip agar bisa dipertanggungjawabkan."
2. Ajukan pertanyaan skenario di langkah 2, lalu tuliskan jawabannya sebagai isi `skenario.json` dan perintah
   yang bisa dijalankan pengguna di komputernya sendiri.

## Langkah kerja

1. **Data.** Butuh paket data bulanan yang sama dengan skill **laporan-analisa** (Excel
   `template-paket-data.xlsx`: LabaRugi, Neraca, ArusKas; minimal 3 bulan terakhir lengkap, 15 bulan agar
   DSCR/ICR memakai data 12 bulan terakhir). Untuk mencoba, pakai `sample-data/<case>/Data-Keuangan-Bulanan.xlsx`.
2. **Tanyakan skenario** dengan pertanyaan bernomor (pengguna boleh menjawab "pakai bawaan"):
   1. Horizon berapa bulan? (bawaan 3; maksimal 24)
   2. Guncangan apa yang ingin diuji, dan seberapa besar? (lihat daftar kunci di
      [references/skema-skenario.md](references/skema-skenario.md))
   3. Berapa sisa plafon kredit yang masih bisa ditarik? (bawaan 0)
   4. Ada batas kovenan bank? (mis. DSCR minimal 1,25x; interest coverage minimal 2x)
   5. Kas minimum yang dianggap aman? (bawaan 1 bulan biaya tetap tunai)

   Tulis jawaban ke `skenario.json`. Jangan mengarang besaran guncangan yang tidak disebut pengguna; bila
   pengguna tidak menentukan, pakai skenario bawaan.
3. **Jalankan:**
   ```
   python scripts/uji_ketahanan_kas.py <paket.xlsx> [--skenario skenario.json] [--horizon 6] \
       [--plafon 2500] [--batas-dscr 1.25] [--batas-icr 2] [--kas-minimum 3000] \
       --out-md uji-kas.md --out-json uji-kas.json
   ```
   Argumen baris perintah mengalahkan isi `skenario.json`.
   - Exit 1: file tidak terbaca. Exit 2: neraca tidak seimbang, data 3 bulan terakhir kurang, atau skenario
     tidak sah. **Jangan menghitung sendiri bila skrip gagal**; sampaikan pesan galatnya dan apa yang perlu
     diperbaiki.
4. **Sajikan** dari `uji-kas.md`:
   - Mulai dengan satu kalimat putusan: skenario terburuk, bulan kas pertama di bawah minimum, dan apakah plafon
     kredit cukup menolong.
   - Angka, status (AMAN/WASPADA/KRITIS), dan urutan skenario **tidak boleh diubah atau dibulatkan ulang**.
   - Sebut hasil **uji balik** (mis. "kas menyentuh batas minimum bila penjualan turun 18%").
   - Bila ada kovenan yang dilanggar, tulis jelas skenario mana dan nilainya.
   - Tutup dengan 3 tindakan pencegahan yang terkait langsung dengan guncangan terberat (mis. percepat penagihan
     pelanggan terbesar, negosiasi tempo pemasok, tunda belanja modal), ditandai sebagai **saran, bukan hasil
     hitung**.
   - Sertakan bagian Asumsi dari skrip.
5. Jika arus kas dasar sudah negatif tanpa guncangan, katakan terus terang: masalahnya bukan skenario, tetapi pola
   kas saat ini. Tawarkan skill **red-flag-operasional** atau **laporan-analisa** untuk mencari penyebabnya.

## Batasan

- Rata-rata 3 bulan terakhir diteruskan; musiman, kontrak besar, dan jadwal pembayaran aktual tidak terlihat.
  Untuk keputusan pendanaan, minta tim keuangan menyusun proyeksi kas mingguan dari jadwal penagihan dan
  pembayaran yang sebenarnya.
- Akhiri jawaban dengan teks berikut, disalin persis:
  > Alat bantu analisis, bukan proyeksi resmi, hasil audit, atau nasihat keuangan.
  >
  > Disusun dengan TQ Board Insight | totalquality.co.id
