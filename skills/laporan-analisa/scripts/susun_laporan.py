#!/usr/bin/env python3
"""Susun laporan analisa lengkap (paket rapat direksi, HTML interaktif) dari paket data bulanan.

Pemakaian:
    python scripts/susun_laporan.py Data-Keuangan-Bulanan.xlsx --out laporan.html
    python scripts/susun_laporan.py paket.xlsx --out laporan.html --json laporan.json --narasi narasi.json

--mode direksi|lengkap, --gaya-cerita narasi|checklist, --preferensi preferensi.json : tampilan awal (bisa diganti
           lewat tombol di laporan).
--narasi : JSON opsional {"surat_direksi": "...", "catatan_analis": "..."} hasil tulisan direksi/AI.
           Angka di dalamnya harus berasal dari laporan; skrip tidak memeriksa teks ini.
Exit code: 0 sukses · 1 input tidak terbaca · 2 validasi gagal (neraca tidak seimbang / periode tidak lengkap).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analisa import Analisa, AnalisaError  # noqa: E402
from baca_paket import PaketError, baca  # noqa: E402

TEMPLATE = HERE.parent / "templates" / "laporan.html"


def ringkas(vm: dict) -> str:
    m = vm["meta"]
    L = [f"Laporan: {m['perusahaan']} · {vm['periode']['month']['label']} · data: {m['tingkat_data']}",
         f"Skor kesehatan (bulanan vs tahun lalu): {vm['skor']['month']['grade']} ({vm['skor']['month']['nilai']}/100)",
         "Putusan: " + vm["putusan"]["month"]["teks"], "", "Cerita utama:"]
    for c in vm["cerita"]:
        L.append(f"  [{c['sev'].upper()}] {c['judul']} — {c['kind']}")
        L.append(f"      Fakta: {c['fakta']}")
        L.append(f"      Penyebab: {c['penyebab']}")
    L.append("")
    L.append("Gerbang validasi: " + ", ".join(f"{g['kode']} {g['status']}" for g in vm["gerbang"]))
    perlu = [k["bagian"] for k in vm["kelengkapan"] if not k["ada"]]
    if perlu:
        L.append("PERLU DATA: " + "; ".join(perlu))
    return "\n".join(L)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Susun laporan analisa (HTML) dari paket data bulanan")
    ap.add_argument("paket", type=Path, help="Excel template-paket-data.xlsx atau JSON")
    ap.add_argument("--out", type=Path, default=Path("laporan-analisa.html"))
    ap.add_argument("--json", type=Path, help="Simpan view model (semua angka) sebagai JSON")
    ap.add_argument("--narasi", type=Path, help="JSON surat_direksi / catatan_analis (opsional)")
    ap.add_argument("--mode", choices=["direksi", "lengkap"], help="Tampilan awal laporan (bawaan: preferensi atau direksi)")
    ap.add_argument("--gaya-cerita", choices=["narasi", "checklist"], help="Bentuk cerita utama (bawaan: preferensi)")
    ap.add_argument("--preferensi", type=Path, help="preferensi.json dari skill tampilan-direksi")
    ap.add_argument("--diam", action="store_true", help="Jangan cetak ringkasan")
    a = ap.parse_args(argv)
    try:
        paket = baca(a.paket)
    except (PaketError, json.JSONDecodeError) as e:
        print(f"GAGAL membaca paket: {e}", file=sys.stderr)
        return 1
    narasi = None
    if a.narasi:
        narasi = json.loads(a.narasi.read_text(encoding="utf-8-sig"))
    try:
        vm = Analisa(paket, narasi).rakit()
    except AnalisaError as e:
        print(str(e), file=sys.stderr)
        print("Laporan TIDAK disusun. Perbaiki data input; jangan menyesuaikan angka agar lolos.", file=sys.stderr)
        return 2
    pref = {}
    if a.preferensi and a.preferensi.exists():
        pref = json.loads(a.preferensi.read_text(encoding="utf-8-sig"))
    vm["tampilan"] = {"mode": a.mode or pref.get("mode_laporan") or "direksi",
                      "cerita": a.gaya_cerita or ("checklist" if pref.get("gaya_narasi") == "checklist" else "narasi")}
    data = json.dumps(vm, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", data)
    a.out.write_text(html, encoding="utf-8")
    if a.json:
        a.json.write_text(json.dumps(vm, indent=1, ensure_ascii=False), encoding="utf-8")
    if not a.diam:
        print(ringkas(vm))
        print(f"\nLaporan ditulis: {a.out}  (buka di browser; tombol 'Cetak / PDF' untuk versi kertas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
