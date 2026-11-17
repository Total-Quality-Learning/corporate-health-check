#!/usr/bin/env python3
"""Samarkan paket data bulanan sebelum dibaca AI. Jalankan sendiri, TANPA AI.

Semua angka UANG dikalikan satu faktor rahasia -> semua rasio, margin, hari (DSO/DIO/DPO), dan
status KPI tetap sama. Nama perusahaan, nama pelanggan, dan nama pemasok diganti kode.
Angka non-uang (persen, hari, unit produksi, jumlah karyawan) TIDAK diubah.

Pemakaian:
    python scripts/samarkan_paket.py Data-Bulanan.xlsx --out Data-Bulanan-samaran.xlsx
    python scripts/samarkan_paket.py Data-Bulanan.xlsx --out samaran.xlsx --faktor 0.37

Dependensi: openpyxl. Faktor hanya ditampilkan di layar, tidak disimpan di file.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

UANG_BULANAN = ("LabaRugi", "Neraca", "ArusKas", "Target")
UANG_KOLOM = {
    "Piutang_Pelanggan": ["batas_kredit", "penjualan_ytd", "umur_0_30", "umur_31_60", "umur_61_90", "umur_90_plus"],
    "Penjualan_Produk": ["pendapatan", "hpp"],
    "Pemasok": ["pembelian_ytd"],
    "Persediaan_Rincian": ["nilai", "umur_0_30", "umur_31_90", "umur_91_180", "umur_180_plus"],
}
NAMA_KOLOM = {"Piutang_Pelanggan": ("pelanggan", "Pelanggan"), "Pemasok": ("pemasok", "Pemasok")}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Samarkan paket data bulanan")
    ap.add_argument("paket", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--faktor", type=float)
    ap.add_argument("--nama", default="Perusahaan Peserta (disamarkan)")
    a = ap.parse_args(argv)
    from openpyxl import load_workbook

    if a.paket.resolve() == a.out.resolve():
        print("File keluaran harus berbeda dari file asli.", file=sys.stderr)
        return 1
    wb = load_workbook(a.paket, data_only=True)
    rng = random.SystemRandom()
    f = a.faktor if a.faktor else rng.choice([rng.uniform(0.2, 0.9), rng.uniform(1.1, 5.0)])

    def kali(c):
        if isinstance(c.value, (int, float)) and not isinstance(c.value, bool):
            c.value = round(c.value * f, 2)

    info = wb["Info"]
    for row in info.iter_rows(min_row=2):
        k = row[0].value
        if k == "perusahaan":
            row[1].value = a.nama
        elif k == "satuan":
            row[1].value = "unit samaran (nilai absolut disamarkan; rasio tetap)"
        elif k == "sumber":
            row[1].value = "Disamarkan dengan samarkan_paket.py"
    for nama in UANG_BULANAN:
        if nama in wb.sheetnames:
            for row in wb[nama].iter_rows(min_row=2, min_col=3):
                for c in row:
                    kali(c)
    if "Operasional" in wb.sheetnames:
        ws = wb["Operasional"]
        for row in ws.iter_rows(min_row=2):
            satuan = str(row[2].value or "").lower()
            if "rp" in satuan:
                for c in row[4:]:
                    kali(c)
    for nama, kolom in UANG_KOLOM.items():
        if nama not in wb.sheetnames:
            continue
        ws = wb[nama]
        head = [c.value for c in ws[1]]
        idx = [i for i, h in enumerate(head) if h in kolom]
        nk = NAMA_KOLOM.get(nama)
        ni = head.index(nk[0]) if nk and nk[0] in head else None
        for n, row in enumerate(ws.iter_rows(min_row=3), start=1):
            for i in idx:
                kali(row[i])
            if ni is not None and row[ni].value:
                row[ni].value = f"{nk[1]} {n:02d}"
            for c in row:
                if head[c.column - 1] == "catatan":
                    c.value = None
    wb.save(a.out)
    print(f"File samaran ditulis: {a.out}")
    print(f"Faktor penyamaran: {f:.6f}  <- simpan sendiri (nilai asli = nilai samaran / faktor). Jangan dibagikan ke AI.")
    print("Catatan: label bulan tidak diubah; nama pelanggan & pemasok diganti kode; kolom catatan dikosongkan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
