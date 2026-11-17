#!/usr/bin/env python3
"""Paketkan tiap skill menjadi .zip untuk diunggah ke aplikasi AI (mis. Claude.ai: Settings > Capabilities > Skills).

Pemakaian (dari root repo):
    python tools/buat_zip.py            # -> dist/<nama-skill>.zip
    python tools/buat_zip.py --out DIR  # -> DIR/<nama-skill>.zip
Setiap zip berisi satu folder skill (SKILL.md di dalam folder itu).
Skill baca-laporan-keuangan membawa LK tahunan fiktif 4 case; laporan-analisa membawa data bulanan fiktif 4 case.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
# Skrip bersama yang ikut disalin ke zip skill lain (skill harus mandiri setelah diunggah).
BAWA = {"uji-ketahanan-kas": ("laporan-analisa/scripts/analisa.py", "laporan-analisa/scripts/baca_paket.py")}
ABAIKAN = {"__pycache__", ".DS_Store", "node_modules", "package-lock.json"}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dist = Path(argv[argv.index("--out") + 1]) if "--out" in argv else DIST
    dist.mkdir(parents=True, exist_ok=True)
    for skill in sorted((ROOT / "skills").iterdir()):
        if not (skill / "SKILL.md").exists():
            continue
        tujuan = dist / f"{skill.name}.zip"
        with zipfile.ZipFile(tujuan, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(skill.rglob("*")):
                if f.is_file() and not (set(f.parts) & ABAIKAN) and f.name not in ABAIKAN and f.suffix != ".pyc":
                    z.write(f, Path(skill.name) / f.relative_to(skill))
            for f in BAWA.get(skill.name, ()):
                z.write(ROOT / "skills" / f, Path(skill.name) / "scripts" / Path(f).name)
            pilih = {"baca-laporan-keuangan": ("lk-tahunan.json", "LK-Tahunan.xlsx", "LK-2025-*.pdf", "README.md"),
                     "laporan-analisa": ("Data-Keuangan-Bulanan.xlsx",),
                     "uji-ketahanan-kas": ("Data-Keuangan-Bulanan.xlsx",),
                     "cek-kesiapan-data": ("jawaban-cek-kesiapan.json",)}.get(skill.name, ())
            for case in sorted((ROOT / "sample-data").iterdir()):
                for pola in pilih:
                    for f in sorted(case.glob(pola)):
                        z.write(f, Path(skill.name) / "sample-data" / case.name / f.name)
        print(f"{tujuan}  ({tujuan.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
