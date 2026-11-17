#!/usr/bin/env python3
"""Skor kesiapan data & sistem (Level 1-4) dari 8 jawaban A-D.

Pemakaian:
    python scripts/skor_kesiapan.py --pertanyaan                 # tampilkan kuesioner
    python scripts/skor_kesiapan.py --jawaban A,B,B,C,A,B,A,C     # urut pertanyaan 1-8
    python scripts/skor_kesiapan.py --file jawaban.json --out-json kesiapan.json --out-md kesiapan.md

Format jawaban.json: {"jawaban": {"1": "A", "2": "B", ...}} atau {"jawaban": ["A", "B", ...]}

Skoring sederhana & transparan: A=1, B=2, C=3, D=4; level dari rata-rata tanpa bobot.
Hanya pustaka standar Python.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERSI = "1.0.0"
REF = Path(__file__).resolve().parents[1] / "references" / "pertanyaan.json"
SKOR = {"A": 1, "B": 2, "C": 3, "D": 4}


def level_dari(rata: float) -> int:
    if rata < 1.75:
        return 1
    if rata < 2.5:
        return 2
    if rata < 3.25:
        return 3
    return 4


def baca_jawaban(a, n: int) -> list[str]:
    if a.jawaban:
        daftar = [x.strip().upper() for x in a.jawaban.replace(";", ",").split(",") if x.strip()]
        if len(daftar) == 1 and len(daftar[0]) == n:  # "ABBCABAC"
            daftar = list(daftar[0])
    else:
        d = json.loads(Path(a.file).read_text(encoding="utf-8-sig"))
        j = d.get("jawaban", d)
        if isinstance(j, dict):
            daftar = [str(j.get(str(i), j.get(i, ""))).strip().upper() for i in range(1, n + 1)]
        else:
            daftar = [str(x).strip().upper() for x in j]
    if len(daftar) != n:
        raise SystemExit(f"Dibutuhkan {n} jawaban, diterima {len(daftar)}.")
    salah = [f"no. {i}: {x!r}" for i, x in enumerate(daftar, 1) if x not in SKOR]
    if salah:
        raise SystemExit("Jawaban harus A, B, C, atau D. Periksa " + ", ".join(salah))
    return daftar


def kuesioner(ref: dict) -> str:
    L = ["# Cek Kesiapan Data & Sistem (8 pertanyaan, ±3 menit)", "",
         "Pilih satu jawaban yang paling menggambarkan kondisi **saat ini** (bukan rencana).", ""]
    for q in ref["pertanyaan"]:
        L.append(f"**{q['no']}. {q['teks']}**")
        L += [f"   - {k}. {v}" for k, v in q["pilihan"].items()]
        L.append("")
    return "\n".join(L)


def nilai(ref: dict, jawaban: list[str]) -> dict:
    qs = ref["pertanyaan"]
    rinci = []
    for q, j in zip(qs, jawaban):
        rinci.append({"no": q["no"], "area": q["area"], "jawaban": j, "jawaban_teks": q["pilihan"][j],
                      "skor": SKOR[j], "mengapa_penting": q["mengapa_penting"], "kategori_solusi": q["kategori_solusi"]})
    rata = sum(r["skor"] for r in rinci) / len(rinci)
    lv = level_dari(rata)
    urut = sorted(rinci, key=lambda r: (r["skor"], r["no"]))
    lemah = [r for r in urut if r["skor"] <= 2][:3]
    jenis = "terlemah"
    if not lemah:
        lemah, jenis = urut[:2], "peningkatan_berikutnya"
    info = next(x for x in ref["level"] if x["level"] == lv)
    return {
        "skrip": f"skor_kesiapan.py v{VERSI}",
        "skor_rata_rata": round(rata, 2),
        "level": lv,
        "nama_level": info["nama"],
        "deskripsi_level": info["deskripsi"],
        "semua_level": ref["level"],
        "rincian": rinci,
        "area_prioritas": lemah,
        "jenis_area_prioritas": jenis,
        "kode_ringkas": f"L{lv}-" + ".".join(str(r["no"]) for r in lemah),
    }


def ke_markdown(h: dict) -> str:
    bar = lambda s: "■" * s + "□" * (4 - s)  # noqa: E731
    L = ["# Hasil Cek Kesiapan Data & Sistem", "",
         f"## Level {h['level']} dari 4: {h['nama_level']}", "",
         h["deskripsi_level"], "",
         f"Skor rata-rata: **{str(h['skor_rata_rata']).replace('.', ',')}** dari 4", "",
         "| No | Area | Jawaban | Skor |", "|---|---|---|---|"]
    for r in h["rincian"]:
        L.append(f"| {r['no']} | {r['area']} | {r['jawaban']}. {r['jawaban_teks']} | {bar(r['skor'])} {r['skor']} |")
    judul = "Area paling lemah" if h["jenis_area_prioritas"] == "terlemah" else "Area untuk peningkatan berikutnya"
    L += ["", f"## {judul}", ""]
    for r in h["area_prioritas"]:
        L += [f"**{r['area']}** (pertanyaan {r['no']}, skor {r['skor']})", "",
              f"- Mengapa penting: {r['mengapa_penting']}",
              f"- Arah solusi: {r['kategori_solusi']}", ""]
    L += ["## Empat level kesiapan", ""]
    for x in h["semua_level"]:
        tanda = " ← posisi Anda" if x["level"] == h["level"] else ""
        L.append(f"- **Level {x['level']} – {x['nama']}**{tanda}: {x['deskripsi']}")
    L += ["", f"Kode ringkas (opsional, untuk dibagikan saat sesi): `{h['kode_ringkas']}`", "",
          "_Versi singkat dengan skoring sederhana tanpa bobot; gambaran awal, bukan hasil asesmen lengkap._", "",
          "Disusun dengan TQ Board Insight · totalquality.co.id", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Skor kesiapan data & sistem")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pertanyaan", action="store_true", help="Cetak kuesioner")
    g.add_argument("--jawaban", help="8 jawaban dipisah koma, mis. A,B,B,C,A,B,A,C")
    g.add_argument("--file", help="File JSON berisi jawaban")
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--diam", action="store_true")
    a = ap.parse_args(argv)
    ref = json.loads(REF.read_text(encoding="utf-8"))
    if a.pertanyaan:
        print(kuesioner(ref))
        return 0
    h = nilai(ref, baca_jawaban(a, len(ref["pertanyaan"])))
    md = ke_markdown(h)
    if a.out_json:
        a.out_json.write_text(json.dumps(h, indent=2, ensure_ascii=False), encoding="utf-8")
    if a.out_md:
        a.out_md.write_text(md, encoding="utf-8")
    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
