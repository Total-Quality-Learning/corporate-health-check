#!/usr/bin/env python3
"""Samarkan LK sebelum dibaca AI: semua angka dikalikan satu faktor rahasia.

Semua rasio (margin, DIO, DSO, current ratio, DER, dll.) adalah perbandingan
dua angka, sehingga TIDAK berubah ketika semua pos dikalikan faktor yang sama.
Yang tersembunyi: nilai absolut (omzet, laba, utang), nama perusahaan, dan
(opsional) tahun.

JALANKAN SCRIPT INI SENDIRI DI KOMPUTER ANDA, TANPA AI, sebelum file
diunggah / dibuka di asisten AI mana pun.

Pemakaian:
    python scripts/samarkan_lk.py lk.json --out lk-samaran.json
    python scripts/samarkan_lk.py lk.json --out lk-samaran.json --samarkan-periode
    python scripts/samarkan_lk.py lk.json --out lk-samaran.json --faktor 0.37

Faktor acak (antara 0,2 dan 5) dipakai jika --faktor tidak diisi. Faktor
hanya ditampilkan di layar dan TIDAK disimpan di file keluaran.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

BAGIAN = ("neraca", "laba_rugi", "arus_kas")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Samarkan nilai absolut LK; rasio tidak berubah.")
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--faktor", type=float, help="Faktor pengali (default: acak 0,2-5)")
    ap.add_argument("--nama", default="Perusahaan Peserta (disamarkan)", help="Nama pengganti")
    ap.add_argument("--samarkan-periode", action="store_true",
                    help="Ganti label periode menjadi T-2, T-1, T (urutan tetap)")
    a = ap.parse_args(argv)

    data = json.loads(a.input.read_text(encoding="utf-8-sig"))
    faktor = a.faktor
    if faktor is None:
        rng = random.SystemRandom()
        faktor = rng.choice([rng.uniform(0.2, 0.9), rng.uniform(1.1, 5.0)])
    if faktor <= 0:
        print("Faktor harus positif.", file=sys.stderr)
        return 1

    periode = [str(p) for p in data["periode"]]
    peta = {p: p for p in periode}
    if a.samarkan_periode:
        n = len(periode)
        peta = {p: ("T" if i == n - 1 else f"T-{n - 1 - i}") for i, p in enumerate(periode)}

    out = {
        "perusahaan": a.nama,
        "mata_uang": data.get("mata_uang", "IDR"),
        "satuan": "unit samaran (nilai absolut disamarkan; rasio tetap)",
        "periode": [peta[p] for p in periode],
        "sumber": "Disamarkan dengan samarkan_lk.py. Nilai absolut tidak mencerminkan angka asli.",
    }
    if isinstance(data.get("hari_periode"), dict):
        out["hari_periode"] = {peta[p]: v for p, v in data["hari_periode"].items() if p in peta}

    for b in BAGIAN:
        out[b] = {}
        for kunci, nilai in (data.get(b) or {}).items():
            baris = {}
            for p in periode:
                v = nilai.get(p)
                if v is None or v == "":
                    baris[peta[p]] = None
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    baris[peta[p]] = round(v * faktor, 2)
                else:
                    print(f"{b}.{kunci}[{p}] bukan angka ({v!r}). Rapikan dulu (jalankan hitung_rasio.py "
                          "untuk mengecek).", file=sys.stderr)
                    return 1
            out[b][kunci] = baris

    a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"File samaran ditulis: {a.out}")
    print(f"Faktor penyamaran: {faktor:.6f}  <- simpan sendiri jika ingin mengembalikan angka asli "
          "(nilai asli = nilai samaran / faktor). Jangan dibagikan ke AI.")
    if a.samarkan_periode:
        print("Label periode: " + ", ".join(f"{p} -> {q}" for p, q in peta.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
