---
name: data-emiten
description: Mencari dan menarik data fundamental perusahaan terbuka (Tbk) di Bursa Efek Indonesia dari TradingView melalui pustaka TradingView-API, lalu menyusun tabel pembanding (pertumbuhan, margin, ROE, ROA, likuiditas, utang, perputaran) dan membandingkannya dengan perusahaan pengguna. Gunakan saat pengguna ingin melihat data emiten/saham IDX tertentu, memilih emiten per sektor atau industri, atau membandingkan kinerja perusahaannya dengan perusahaan Tbk sejenis.
---

# Data Emiten IDX (TradingView)

Peserta cukup memilih perusahaan Tbk; skrip menarik datanya. **Sumber tidak resmi**, selalu sampaikan batasannya.

## Prasyarat

- Node.js ≥ 20 dan akses internet. Sekali saja: `cd scripts && npm install`.
- Lingkungan AI tanpa akses internet (mis. sebagian sandbox eksekusi kode) tidak bisa memakai skill ini; sampaikan
  ke pengguna dan sarankan menjalankannya di komputer sendiri.

## Langkah kerja (interaktif)

1. **Tanya tujuan** dalam satu pertanyaan bernomor: (1) melihat emiten tertentu, (2) memilih emiten per sektor/industri,
   (3) membandingkan perusahaan sendiri dengan emiten sejenis.
2. **Bantu memilih emiten:**
   - Sektor: `node scripts/tv_emiten.mjs sektor` → tampilkan daftar sektor.
   - Per sektor: `node scripts/tv_emiten.mjs daftar --sektor "Consumer Non-Durables" --limit 15`
   - Kata kunci (boleh bahasa Indonesia: tekstil, garmen, makanan, farmasi, semen, otomotif, logam, kimia, kertas,
     distribusi, ritel, ...): `node scripts/tv_emiten.mjs daftar --cari tekstil --limit 15`
   - Tampilkan tabel (kode, nama, industri, kapitalisasi) dan minta pengguna memilih **3-10 kode**.
3. **Ambil data:** `node scripts/tv_emiten.mjs ambil UNVR ICBP MYOR --out emiten.json`
   (gagal jaringan → skrip mencoba ulang 3 kali; jika tetap gagal, sampaikan apa adanya dan jangan mengarang angka).
4. **Ringkas:** `python scripts/ringkas_emiten.py emiten.json [--rasio rasio.json] [--gaya ringkas|detail|checklist]`
   - Dengan `--rasio` (keluaran `hitung_rasio.py` dari skill **baca-laporan-keuangan**), tabel menambah kolom
     "Perusahaan Anda" dan posisi terhadap median emiten.
   - Gaya mengikuti `preferensi.json` (skill **tampilan-direksi**) bila ada: `--preferensi preferensi.json`.
5. **Sajikan** gaya direksi: 1 kalimat kesimpulan → 3 perbedaan terbesar terhadap median → catatan sumber.

## Wajib disampaikan (singkat, sekali per sesi)

> Data emiten diambil dari TradingView melalui pustaka tidak resmi. Angka bisa tertunda atau berbeda dengan laporan
> keuangan resmi (laba kotor bisa selisih hingga sekitar 4%). Verifikasi angka penting ke idx.co.id / situs emiten sebelum
> dipakai mengambil keputusan.

## Batasan data (lihat `references/sumber-data.md`)

- Tersedia: profil & kapitalisasi pasar; riwayat tahunan pendapatan, laba kotor, laba bersih, total aset, utang,
  EBITDA, arus kas bebas; posisi tahun terakhir aset/liabilitas lancar, total liabilitas, ekuitas, kas; rasio jadi
  (margin, ROE, ROA, rasio lancar/cepat, DER, perputaran aset & piutang).
- **Tidak tersedia:** persediaan, utang usaha, beban bunga, rincian neraca tahun-tahun sebelumnya → DIO, DPO,
  interest coverage emiten tidak ditampilkan; hari piutang hanya perkiraan.
- Emiten adalah perusahaan besar dan terbuka. Pembanding ini memberi **konteks**, bukan target bagi perusahaan
  tertutup. Jangan menyebutnya "benchmark industri".
- Jangan menyimpan kredensial TradingView; skill ini hanya memakai akses anonim.

Disusun dengan TQ Board Insight | totalquality.co.id
