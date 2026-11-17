#!/usr/bin/env python3
"""Kelola preferensi tampilan (preferensi.json) yang dipakai semua skill TQ Board Insight.

Pemakaian:
    python scripts/preferensi.py --pertanyaan                      # cetak pertanyaan & pilihan (untuk ditanyakan AI)
    python scripts/preferensi.py --preset direksi --out preferensi.json
    python scripts/preferensi.py --preset direksi --set gaya_narasi=checklist visual=grafik --out preferensi.json
    python scripts/preferensi.py --jawaban 1A,2B,3C,4A --out preferensi.json   # dari jawaban bernomor
    python scripts/preferensi.py --tampilkan preferensi.json

Hanya pustaka standar Python.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# kunci -> (pertanyaan, {pilihan: keterangan}, bawaan)
SKEMA = {
    "audiens": ("Laporan ini untuk siapa?", {
        "direksi": "Direksi / pemilik, keputusan cepat",
        "komisaris": "Dewan komisaris, pengawasan & risiko",
        "manajer_keuangan": "Manajer keuangan / CFO, rinci & teknis",
        "bank_investor": "Bank / investor, kelayakan & utang",
    }, "direksi"),
    "gaya_narasi": ("Bentuk narasi yang diinginkan?", {
        "ringkas": "Singkat, rasio kunci + 3 hal yang perlu perhatian",
        "detail": "Detail, semua rasio, perhitungan, dan penjelasan",
        "checklist": "Checklist, setiap indikator sebagai kotak centang aman/perlu perhatian",
    }, "ringkas"),
    "visual": ("Bentuk visualisasi?", {
        "grafik": "Grafik saja, dengan judul berupa kesimpulan",
        "penjelasan": "Penjelasan detail tiap grafik (teks), tanpa gambar",
        "keduanya": "Grafik + penjelasan detail di bawahnya",
        "tanpa": "Tanpa visual, tabel & teks saja",
    }, "keduanya"),
    "fokus": ("Fokus utama?", {
        "semua": "Semua aspek",
        "kas": "Kas & modal kerja",
        "profitabilitas": "Margin & laba",
        "utang": "Utang & kemampuan bayar",
        "efisiensi": "Efisiensi & produktivitas",
    }, "semua"),
    "istilah": ("Tingkat istilah teknis?", {
        "awam": "Bahasa awam, setiap istilah dijelaskan",
        "campuran": "Campuran, istilah umum tanpa penjelasan",
        "teknis": "Teknis, istilah keuangan apa adanya",
    }, "awam"),
    "panjang": ("Panjang hasil?", {
        "1_halaman": "Maksimal 1 halaman",
        "3_halaman": "Sekitar 3 halaman",
        "lengkap": "Lengkap, tanpa batas",
    }, "1_halaman"),
    "format_keluaran": ("Bentuk keluaran?", {
        "chat": "Ringkasan di chat saja",
        "html": "Berkas HTML (bisa dicetak ke PDF)",
        "keduanya": "Ringkasan di chat + berkas HTML",
    }, "keduanya"),
    "mode_laporan": ("Tampilan laporan analisa bulanan?", {
        "direksi": "Mode direksi, putusan, cerita, KPI bermasalah, keputusan",
        "lengkap": "Mode lengkap, 11 bagian",
    }, "direksi"),
    "metode_rasio": ("Metode saldo neraca untuk rasio?", {
        "akhir": "Saldo akhir periode (cocok untuk tren internal)",
        "rata-rata": "Rata-rata awal & akhir (cocok dibandingkan dengan angka publikasi emiten)",
    }, "akhir"),
}
PERTANYAAN_INTI = ["audiens", "gaya_narasi", "visual", "fokus"]

PRESET = {
    "direksi": {},
    "komisaris": {"audiens": "komisaris", "gaya_narasi": "checklist", "fokus": "utang", "panjang": "3_halaman"},
    "keuangan": {"audiens": "manajer_keuangan", "gaya_narasi": "detail", "istilah": "teknis", "panjang": "lengkap",
                 "mode_laporan": "lengkap", "visual": "keduanya"},
    "bank": {"audiens": "bank_investor", "gaya_narasi": "detail", "fokus": "utang", "istilah": "campuran",
             "metode_rasio": "rata-rata", "mode_laporan": "lengkap"},
}


def bawaan() -> dict:
    return {k: v[2] for k, v in SKEMA.items()}


def validasi(pref: dict) -> list[str]:
    err = []
    for k, v in pref.items():
        if k in ("versi", "catatan"):
            continue
        if k not in SKEMA:
            err.append(f"Kunci tidak dikenal: {k}")
        elif v not in SKEMA[k][1]:
            err.append(f"{k}={v!r} tidak valid. Pilihan: {', '.join(SKEMA[k][1])}")
    return err


def teks_pertanyaan() -> str:
    L = ["# Preferensi tampilan (jawab singkat, mis. 1A, 2B, 3C, 4A)", ""]
    for n, k in enumerate(PERTANYAAN_INTI, 1):
        tanya, pil, dft = SKEMA[k]
        L.append(f"**{n}. {tanya}**")
        for h, (kode, ket) in zip("ABCDE", pil.items()):
            L.append(f"   {h}. {ket}{'  ← bawaan' if kode == dft else ''}")
        L.append("")
    L.append("Pertanyaan lanjutan (opsional, pakai bawaan bila tidak dijawab):")
    for k in SKEMA:
        if k not in PERTANYAAN_INTI:
            tanya, pil, dft = SKEMA[k]
            L.append(f"- {tanya} ({' / '.join(pil)}; bawaan: {dft})")
    return "\n".join(L)


def dari_jawaban(teks: str) -> dict:
    hasil = {}
    for bag in teks.replace(" ", "").split(","):
        if len(bag) < 2 or not bag[:-1].isdigit():
            raise SystemExit(f"Format jawaban salah: {bag!r}. Contoh: 1A,2B,3C,4A")
        no, huruf = int(bag[:-1]), bag[-1].upper()
        if not 1 <= no <= len(PERTANYAAN_INTI):
            raise SystemExit(f"Nomor pertanyaan {no} tidak ada.")
        k = PERTANYAAN_INTI[no - 1]
        pilihan = list(SKEMA[k][1])
        idx = "ABCDE".find(huruf)
        if idx < 0 or idx >= len(pilihan):
            raise SystemExit(f"Pilihan {huruf} tidak ada untuk pertanyaan {no}.")
        hasil[k] = pilihan[idx]
    return hasil


def ringkas(pref: dict) -> str:
    return "\n".join(f"- {SKEMA[k][0]} **{SKEMA[k][1][v]}**" for k, v in pref.items() if k in SKEMA)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Preferensi tampilan TQ Board Insight")
    ap.add_argument("--pertanyaan", action="store_true")
    ap.add_argument("--preset", choices=list(PRESET))
    ap.add_argument("--jawaban", help="mis. 1A,2B,3C,4A")
    ap.add_argument("--set", nargs="*", default=[], help="kunci=nilai")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--tampilkan", type=Path)
    a = ap.parse_args(argv)
    if a.pertanyaan:
        print(teks_pertanyaan())
        return 0
    if a.tampilkan:
        pref = json.loads(a.tampilkan.read_text(encoding="utf-8-sig"))
        err = validasi(pref)
        print(ringkas(pref))
        for e in err:
            print("PERINGATAN:", e, file=sys.stderr)
        return 1 if err else 0
    pref = bawaan()
    if a.preset:
        pref.update(PRESET[a.preset])
    if a.jawaban:
        pref.update(dari_jawaban(a.jawaban))
    for kv in a.set:
        if "=" not in kv:
            print(f"Format --set salah: {kv}", file=sys.stderr)
            return 1
        k, v = kv.split("=", 1)
        pref[k.strip()] = v.strip()
    err = validasi(pref)
    if err:
        print("\n".join(err), file=sys.stderr)
        return 1
    pref["versi"] = "1"
    if a.out:
        a.out.write_text(json.dumps(pref, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Preferensi disimpan: {a.out}")
    print(ringkas(pref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
