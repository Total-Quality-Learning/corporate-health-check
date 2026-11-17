#!/usr/bin/env python3
"""Jalankan seluruh alur sekaligus: LK -> rasio -> red flag -> (kesiapan) -> board brief.

Untuk staf IT/finance yang ingin memakai data sendiri tanpa asisten AI, atau untuk gladi demo.

Pemakaian (dari root repo):
    python tools/analisis_lengkap.py sample-data/01-manufaktur-garmen/lk-tahunan.json
    python tools/analisis_lengkap.py LK-saya.xlsx --kesiapan A,B,B,C,A,B,A,C --out hasil-saya
    python tools/analisis_lengkap.py LK-saya.xlsx --samarkan --out hasil-saya

Input boleh JSON format standar atau Excel format template.
--samarkan : samarkan angka dulu (rasio tetap sama) sebelum dianalisis.
Keluaran   : folder --out (default: hasil/) berisi lk.json, rasio.*, gejala.*, kesiapan.*, brief.md, brief.html
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"


def jalan(*args) -> None:
    r = subprocess.run([sys.executable, *map(str, args)])
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Analisis lengkap TQ Board Insight")
    ap.add_argument("input", type=Path, help="lk.json (format standar) atau .xlsx (format template)")
    ap.add_argument("--kesiapan", help="8 jawaban cek kesiapan, mis. A,B,B,C,A,B,A,C")
    ap.add_argument("--samarkan", action="store_true", help="Samarkan nilai absolut sebelum analisis")
    ap.add_argument("--out", type=Path, default=Path("hasil"))
    ap.add_argument("--gaya", choices=["ringkas", "detail", "checklist"], default="ringkas")
    a = ap.parse_args()
    out = a.out
    out.mkdir(parents=True, exist_ok=True)

    lk = out / "lk.json"
    if a.input.suffix.lower() in (".xlsx", ".xlsm"):
        jalan(SK / "baca-laporan-keuangan/scripts/baca_excel.py", a.input, "--out", lk)
    else:
        lk.write_bytes(a.input.read_bytes())
    if a.samarkan:
        samar = out / "lk-samaran.json"
        jalan(SK / "baca-laporan-keuangan/scripts/samarkan_lk.py", lk, "--out", samar, "--samarkan-periode")
        lk.unlink()  # jangan tinggalkan angka asli di folder hasil
        lk = samar
    jalan(SK / "baca-laporan-keuangan/scripts/hitung_rasio.py", lk,
          "--out-json", out / "rasio.json", "--out-md", out / "rasio.md", "--gaya", a.gaya, "--diam")
    jalan(SK / "baca-laporan-keuangan/scripts/visualisasi.py", out / "rasio.json", "--out", out / "visual.html")
    jalan(SK / "red-flag-operasional/scripts/deteksi_gejala.py", out / "rasio.json",
          "--out-json", out / "gejala.json", "--out-md", out / "gejala.md", "--diam")
    brief = [SK / "board-brief/scripts/susun_brief.py", "--rasio", out / "rasio.json", "--gejala", out / "gejala.json",
             "--out-md", out / "brief.md", "--out-html", out / "brief.html", "--diam"]
    if a.kesiapan:
        jalan(SK / "cek-kesiapan-data/scripts/skor_kesiapan.py", "--jawaban", a.kesiapan,
              "--out-json", out / "kesiapan.json", "--out-md", out / "kesiapan.md", "--diam")
        brief += ["--kesiapan", out / "kesiapan.json"]
    jalan(*brief)
    print(f"\nSelesai. Buka {out / 'brief.html'} dan {out / 'visual.html'} di browser (Ctrl+P untuk simpan PDF).")
    print(f"Rincian: {out / 'rasio.md'}, {out / 'gejala.md'}" + (f", {out / 'kesiapan.md'}" if a.kesiapan else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
