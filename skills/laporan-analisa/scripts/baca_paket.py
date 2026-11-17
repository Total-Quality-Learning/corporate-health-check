#!/usr/bin/env python3
"""Baca paket data bulanan (Excel template-paket-data.xlsx atau JSON) menjadi dict.

Pemakaian mandiri (cek isi paket):
    python scripts/baca_paket.py Data-Keuangan-Bulanan.xlsx            # ringkasan
    python scripts/baca_paket.py Data-Keuangan-Bulanan.xlsx --json out.json

Sheet wajib  : Info, LabaRugi, Neraca, ArusKas
Sheet opsional: Target, Ambang_KPI, Piutang_Pelanggan, Penjualan_Produk, Pemasok,
                Persediaan_Rincian, Operasional, Produksi_Lini
Dependensi: openpyxl (untuk Excel).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

POLA_BULAN = re.compile(r"^\d{4}-\d{2}$")
TABEL_OPS = {
    "Piutang_Pelanggan": "piutang_pelanggan",
    "Penjualan_Produk": "penjualan_produk",
    "Pemasok": "pemasok",
    "Persediaan_Rincian": "persediaan_rincian",
    "Produksi_Lini": "produksi_lini",
}


class PaketError(Exception):
    pass


def label_bulan(v) -> str | None:
    if v is None:
        return None
    if hasattr(v, "year") and hasattr(v, "month"):
        return f"{v.year:04d}-{v.month:02d}"
    s = str(v).strip()
    if POLA_BULAN.match(s):
        return s
    m = re.match(r"^(\d{4})-(\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    return None


def angka(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if s in ("", "-"):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


def _bulanan(rows, nama, kolom_mulai=2):
    if not rows:
        raise PaketError(f"Sheet {nama} kosong.")
    head = rows[0]
    if str(head[0]).strip().lower() != "kode":
        raise PaketError(f"Sheet {nama}: sel A1 harus 'kode'.")
    kolom = [(i, label_bulan(h)) for i, h in enumerate(head) if i >= kolom_mulai and label_bulan(h)]
    out = {}
    meta = {}
    for r in rows[1:]:
        if not r or r[0] in (None, ""):
            continue
        kode = str(r[0]).strip()
        nilai = {}
        for i, b in kolom:
            v = angka(r[i]) if i < len(r) else None
            if v is not None:
                nilai[b] = v
        out[kode] = nilai
        meta[kode] = [r[j] if j < len(r) else None for j in range(1, kolom_mulai)]
    return out, meta


def baca_excel(path: Path) -> dict:
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise PaketError("openpyxl belum terpasang: pip install openpyxl")
    wb = load_workbook(path, data_only=True, read_only=True)
    nama = set(wb.sheetnames)
    for wajib in ("Info", "LabaRugi", "Neraca", "ArusKas"):
        if wajib not in nama:
            raise PaketError(f"Sheet wajib '{wajib}' tidak ada. Gunakan templates/template-paket-data.xlsx.")
    rows = lambda s: list(wb[s].iter_rows(values_only=True))  # noqa: E731
    info = {}
    for r in rows("Info")[1:]:
        if r and r[0] and r[1] not in (None, ""):
            info[str(r[0]).strip()] = str(r[1]).strip() if not hasattr(r[1], "year") else label_bulan(r[1])
    paket = {"info": info}
    paket["laba_rugi"], _ = _bulanan(rows("LabaRugi"), "LabaRugi")
    paket["neraca"], _ = _bulanan(rows("Neraca"), "Neraca")
    paket["arus_kas"], _ = _bulanan(rows("ArusKas"), "ArusKas")
    paket["target"] = _bulanan(rows("Target"), "Target")[0] if "Target" in nama else None
    if paket["target"] is not None and not any(paket["target"].values()):
        paket["target"] = None
    if "Ambang_KPI" in nama:
        amb = []
        for r in rows("Ambang_KPI")[1:]:
            if r and r[0]:
                amb.append({"kpi": str(r[0]).strip(), "nama": r[1], "waspada": angka(r[2]), "kritis": angka(r[3]),
                            "arah": (str(r[4]).strip().lower() if len(r) > 4 and r[4] else "")})
        paket["ambang_kpi"] = amb or None
    for sheet, kunci in TABEL_OPS.items():
        if sheet not in nama:
            continue
        rr = rows(sheet)
        if len(rr) < 3:
            continue
        kolom = [str(k).strip() if k else "" for k in rr[0]]
        data = []
        for r in rr[2:]:  # baris 2 = judul tampilan
            if not r or all(v in (None, "") for v in r):
                continue
            row = {}
            for k, v in zip(kolom, r):
                if not k:
                    continue
                if k in ("periode",):
                    row[k] = label_bulan(v)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    row[k] = float(v)
                else:
                    row[k] = v if v is None else str(v).strip()
                    if row[k] is not None and k not in ("pelanggan", "wilayah", "terafiliasi", "catatan", "produk",
                                                         "satuan", "pemasok", "kategori", "item", "jenis", "lini"):
                        x = angka(row[k])
                        row[k] = x if x is not None else row[k]
            data.append(row)
        if data:
            paket[kunci] = data
    if "Operasional" in nama:
        rr = rows("Operasional")
        head = rr[0]
        kolom = [(i, label_bulan(h)) for i, h in enumerate(head) if i >= 4 and label_bulan(h)]
        ops = {}
        for r in rr[1:]:
            if not r or not r[0]:
                continue
            ops[str(r[0]).strip()] = {"uraian": r[1] or r[0], "satuan": r[2] or "", "arah": (r[3] or "").strip().lower(),
                                      "nilai": {b: angka(r[i]) for i, b in kolom if i < len(r) and angka(r[i]) is not None}}
        if ops:
            paket["operasional"] = ops
    return paket


def baca(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise PaketError(f"File tidak ditemukan: {path}")
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        return baca_excel(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    for k in ("info", "laba_rugi", "neraca", "arus_kas"):
        if k not in data:
            raise PaketError(f"JSON paket tidak memiliki kunci '{k}'.")
    for bagian in ("laba_rugi", "neraca", "arus_kas", "target"):
        if data.get(bagian):
            data[bagian] = {k: {b: angka(v) for b, v in d.items() if angka(v) is not None}
                            for k, d in data[bagian].items()}
    return data


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Baca & ringkas paket data bulanan")
    ap.add_argument("paket", type=Path)
    ap.add_argument("--json", type=Path, help="Simpan hasil baca sebagai JSON")
    a = ap.parse_args(argv)
    try:
        p = baca(a.paket)
    except PaketError as e:
        print("GAGAL:", e, file=sys.stderr)
        return 1
    bl = sorted({b for v in p["laba_rugi"].values() for b in v})
    print(f"Perusahaan : {p['info'].get('perusahaan', '-')}")
    print(f"Bulan L/R  : {bl[0] if bl else '-'} s.d. {bl[-1] if bl else '-'} ({len(bl)} bulan)")
    print(f"Target     : {'ada' if p.get('target') else 'tidak ada'}")
    ops = [k for k in ("piutang_pelanggan", "penjualan_produk", "pemasok", "persediaan_rincian", "operasional",
                       "produksi_lini") if p.get(k)]
    print(f"Data operasional: {', '.join(ops) if ops else 'tidak ada (bagian terkait akan ditandai PERLU DATA)'}")
    if a.json:
        a.json.write_text(json.dumps(p, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print("JSON ditulis:", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
