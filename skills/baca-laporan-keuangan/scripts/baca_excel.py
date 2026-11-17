#!/usr/bin/env python3
"""Ubah Excel format template (templates/template-lk.xlsx) menjadi JSON format standar.

Pemakaian:
    python scripts/baca_excel.py LK-saya.xlsx --out lk.json

Struktur yang dibaca:
- Sheet "Info"     : kunci/nilai (perusahaan, mata_uang, satuan, sumber)
- Sheet "Neraca", "LabaRugi", "ArusKas":
    kolom A = kode (kunci format standar), kolom B = uraian, kolom C dst. = periode.
    Baris 1 = judul; judul kolom C dst. = label periode (urut dari terlama).
- Baris "hari_periode" di sheet LabaRugi (opsional) untuk periode < 1 tahun.

Dependensi: openpyxl.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SHEET = {"neraca": "Neraca", "laba_rugi": "LabaRugi", "arus_kas": "ArusKas"}


def label_periode(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Excel template LK -> JSON format standar")
    ap.add_argument("excel", type=Path)
    ap.add_argument("--out", type=Path, help="File JSON keluaran (default: cetak ke layar)")
    a = ap.parse_args(argv)

    try:
        from openpyxl import load_workbook
    except ImportError:
        print("openpyxl belum terpasang. Jalankan: pip install openpyxl", file=sys.stderr)
        return 1
    if not a.excel.exists():
        print(f"File tidak ditemukan: {a.excel}", file=sys.stderr)
        return 1

    wb = load_workbook(a.excel, data_only=True, read_only=True)
    hasil: dict = {"perusahaan": "", "mata_uang": "IDR", "satuan": "", "periode": []}
    peringatan = []

    if "Info" in wb.sheetnames:
        for row in wb["Info"].iter_rows(min_row=2, max_col=2, values_only=True):
            k, v = row[0], row[1]
            if k in ("perusahaan", "mata_uang", "satuan", "sumber") and v not in (None, ""):
                hasil[k] = str(v).strip()

    periode_ref = None
    hari = {}
    for bagian, nama in SHEET.items():
        if nama not in wb.sheetnames:
            print(f"Sheet '{nama}' tidak ada. Pakai templates/template-lk.xlsx.", file=sys.stderr)
            return 1
        rows = list(wb[nama].iter_rows(values_only=True))
        if not rows:
            print(f"Sheet '{nama}' kosong.", file=sys.stderr)
            return 1
        head = rows[0]
        if str(head[0]).strip().lower() != "kode":
            print(f"Sheet '{nama}': sel A1 harus 'kode'. Jangan ubah struktur template.", file=sys.stderr)
            return 1
        kolom = [(i, label_periode(h)) for i, h in enumerate(head) if i >= 2 and h not in (None, "")]
        periode = [p for _, p in kolom]
        if not periode:
            print(f"Sheet '{nama}': judul periode (C1, D1, ...) kosong.", file=sys.stderr)
            return 1
        if periode_ref is None:
            periode_ref = periode
        elif periode != periode_ref:
            print(f"Label periode di sheet '{nama}' ({periode}) berbeda dengan sheet lain ({periode_ref}).",
                  file=sys.stderr)
            return 1
        isi = {}
        for r in rows[1:]:
            if not r or r[0] in (None, ""):
                continue
            kode = str(r[0]).strip()
            nilai = {}
            for i, p in kolom:
                v = r[i] if i < len(r) else None
                if isinstance(v, str):
                    v = v.strip() or None
                nilai[p] = v
            if kode == "hari_periode":
                hari = {p: v for p, v in nilai.items() if v not in (None, "")}
                continue
            if all(v is None for v in nilai.values()):
                continue
            isi[kode] = nilai
        hasil[bagian] = isi
    hasil["periode"] = periode_ref
    if hari:
        hasil["hari_periode"] = hari
    if not any(hasil[b] for b in SHEET):
        peringatan.append("Semua sheet kosong. Jika angka berupa rumus, buka & simpan file di Excel dulu "
                          "agar nilai hasil rumus tersimpan.")

    teks = json.dumps(hasil, indent=2, ensure_ascii=False)
    if a.out:
        a.out.write_text(teks, encoding="utf-8")
        print(f"JSON ditulis ke {a.out} (periode: {', '.join(periode_ref)}).")
    else:
        print(teks)
    for w in peringatan:
        print("PERINGATAN:", w, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
