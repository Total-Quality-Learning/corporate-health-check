# Panduan Kontribusi

Terima kasih ingin berkontribusi ke **Corporate Health Check**.

## Prinsip utama

1. **Angka dihitung skrip Python yang deterministik; AI hanya menulis narasi.** Jangan memindahkan perhitungan ke prompt/SKILL.md.
2. Jika neraca tidak seimbang, skrip harus berhenti. Jangan melonggarkan validasi ini.
3. Data yang tidak tersedia ditandai **PERLU DATA**, tidak ditebak.
4. Semua data di `sample-data/` harus **fiktif**. Jangan pernah meng-commit laporan keuangan perusahaan nyata yang bukan data publik.
5. Bahasa dokumentasi dan output: Bahasa Indonesia.

## Setup

```
git clone https://github.com/Total-Quality-Learning/corporate-health-check.git
cd corporate-health-check
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-optional.txt   # opsional, untuk input PDF
```

Python 3.9+ didukung.

## Menjalankan test

```
python -m unittest discover -s tests -v
```

Semua test harus lulus sebelum PR dibuka. CI menjalankan perintah yang sama di setiap PR.

## Alur kerja

1. Ambil atau buat issue terlebih dulu, lalu tulis komentar bahwa Anda mengerjakannya.
2. Buat branch dari `main`: `feat/<ringkas>`, `fix/<ringkas>`, `docs/<ringkas>`, atau `chore/<ringkas>`.
3. Satu PR untuk satu perubahan. Sertakan test untuk fitur baru atau perbaikan bug.
4. Pesan commit singkat dan jelas, mis. `fix: rasio lancar salah bila utang lancar nol`.
5. Buka PR ke `main`, isi template, dan tunggu review minimal satu maintainer.

## Struktur

| Folder | Isi |
|---|---|
| `skills/<nama>/SKILL.md` | Instruksi skill untuk AI |
| `skills/<nama>/scripts/` | Skrip perhitungan deterministik |
| `tools/` | Utilitas (analisis lengkap, format data, build zip) |
| `sample-data/` | Data contoh fiktif per industri |
| `tests/` | Uji regresi |
| `dist/` | Zip skill, dibuat ulang dengan `python tools/buat_zip.py` |

## Menambah atau mengubah skill

- Perbarui `SKILL.md` dan skrip terkait bersamaan.
- Tambahkan baris di tabel README bila menambah skill.
- Jalankan `python tools/buat_zip.py` hanya bila maintainer meminta pembaruan `dist/` (untuk mengurangi konflik).

## Melaporkan bug

Gunakan template *Laporan bug*. Sertakan perintah yang dijalankan, output/error, dan (jika bisa) data contoh fiktif yang memicu bug.
