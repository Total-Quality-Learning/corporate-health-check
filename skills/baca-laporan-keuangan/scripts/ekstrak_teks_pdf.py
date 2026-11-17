#!/usr/bin/env python3
"""Ambil teks dari PDF laporan keuangan (untuk agen yang tidak bisa membaca PDF langsung).

Pemakaian:
    python scripts/ekstrak_teks_pdf.py LK.pdf --out lk.txt
    python scripts/ekstrak_teks_pdf.py LK.pdf --halaman 3-8

Mencoba pustaka yang tersedia secara berurutan: pymupdf, pdfplumber, pypdf.
Hanya mengambil teks; pemetaan ke format standar dilakukan sesudahnya dan
WAJIB divalidasi dengan hitung_rasio.py. PDF hasil scan (gambar) tidak
memiliki teks; gunakan OCR atau minta file Excel dari tim finance.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def rentang(teks: str | None, total: int) -> list[int]:
    if not teks:
        return list(range(total))
    hasil = []
    for bag in teks.split(","):
        if "-" in bag:
            a, b = bag.split("-")
            hasil += list(range(int(a) - 1, min(int(b), total)))
        else:
            hasil.append(int(bag) - 1)
    return [h for h in hasil if 0 <= h < total]


def pakai_pymupdf(path, halaman):
    import pymupdf  # type: ignore
    doc = pymupdf.open(path)
    return [(i + 1, doc[i].get_text()) for i in rentang(halaman, doc.page_count)]


def pakai_pdfplumber(path, halaman):
    import pdfplumber  # type: ignore
    with pdfplumber.open(path) as pdf:
        return [(i + 1, pdf.pages[i].extract_text() or "") for i in rentang(halaman, len(pdf.pages))]


def pakai_pypdf(path, halaman):
    from pypdf import PdfReader  # type: ignore
    r = PdfReader(path)
    return [(i + 1, r.pages[i].extract_text() or "") for i in rentang(halaman, len(r.pages))]


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Ekstrak teks PDF per halaman")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--halaman", help="mis. 3-8 atau 2,4,6 (default: semua)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)

    hasil, dipakai = None, None
    for nama, fn in (("pymupdf", pakai_pymupdf), ("pdfplumber", pakai_pdfplumber), ("pypdf", pakai_pypdf)):
        try:
            hasil = fn(str(a.pdf), a.halaman)
            dipakai = nama
            break
        except ImportError:
            continue
    if hasil is None:
        print("Tidak ada pustaka PDF. Pasang salah satu: pip install pypdf", file=sys.stderr)
        return 1
    teks = "\n".join(f"\n===== HALAMAN {n} =====\n{t}" for n, t in hasil)
    if not teks.strip().replace("=", "").replace("HALAMAN", "").strip():
        print("PDF tidak berisi teks (kemungkinan hasil scan).", file=sys.stderr)
    if a.out:
        a.out.write_text(teks, encoding="utf-8")
        print(f"Teks {len(hasil)} halaman ditulis ke {a.out} (pustaka: {dipakai}).")
    else:
        print(teks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
