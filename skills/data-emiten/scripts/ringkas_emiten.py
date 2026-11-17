#!/usr/bin/env python3
"""Ringkas data emiten (hasil tv_emiten.mjs ambil) menjadi tabel pembanding, opsional dibandingkan dengan
perusahaan pengguna (hasil hitung_rasio.py).

Pemakaian:
    python scripts/ringkas_emiten.py emiten.json
    python scripts/ringkas_emiten.py emiten.json --rasio rasio.json --out-md pembanding.md
    python scripts/ringkas_emiten.py emiten.json --gaya checklist --rasio rasio.json
    python scripts/ringkas_emiten.py emiten.json --out-json pembanding.json

Hanya pustaka standar Python. Angka emiten berasal dari TradingView (tidak resmi), lihat references/sumber-data.md.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

# (kunci, label, satuan, arah_lebih_baik, kunci_rasio_pengguna)
METRIK = [
    ("pertumbuhan", "Pertumbuhan pendapatan (thn terakhir)", "persen", "tinggi", None),
    ("cagr3", "Pertumbuhan pendapatan rata-rata 3 thn (CAGR)", "persen", "tinggi", None),
    ("gm", "Margin laba kotor", "persen", "tinggi", "gross_margin"),
    ("om", "Margin laba usaha", "persen", "tinggi", "operating_margin"),
    ("ebitda_m", "Margin EBITDA", "persen", "tinggi", "ebitda_margin"),
    ("nm", "Margin laba bersih", "persen", "tinggi", "net_margin"),
    ("roe", "ROE", "persen", "tinggi", "roe"),
    ("roa", "ROA", "persen", "tinggi", "roa"),
    ("cr", "Rasio lancar", "kali", "tinggi", "current_ratio"),
    ("der", "DER (liabilitas / ekuitas)", "kali", "rendah", "der"),
    ("de", "Utang berbunga / ekuitas", "kali", "rendah", "der_berbunga"),
    ("nde", "Utang bersih / EBITDA", "kali", "rendah", "net_debt_ebitda"),
    ("at", "Perputaran aset", "kali", "tinggi", "asset_turnover"),
    ("dso", "Hari piutang (perkiraan)", "hari", "rendah", "dso"),
    ("fcf_m", "Margin arus kas bebas", "persen", "tinggi", "fcf_margin"),
]
RINGKAS = ["pertumbuhan", "gm", "nm", "roe", "der", "dso"]


def idn(x, d=1):
    return f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def fmt(v, sat):
    if v is None:
        return "-"
    t = "-" if v < 0 else ""
    a = abs(v)
    return {"persen": f"{t}{idn(a, 1)}%", "kali": f"{t}{idn(a, 2)}x", "hari": f"{t}{idn(a, 0)} hari"}.get(sat, idn(v))


def rp(v):
    if v is None:
        return "-"
    a = abs(v)
    s = f"{idn(a / 1e12, 2)} T" if a >= 1e12 else f"{idn(a / 1e9, 1)} M"
    return ("-" if v < 0 else "") + "Rp" + s


def bagi(a, b, k=1.0):
    if a is None or b in (None, 0):
        return None
    return a / b * k


def h(e, k, i=0):
    arr = e.get(k) or []
    return arr[i] if len(arr) > i else None


def hitung(e: dict) -> dict:
    rev, rev1, rev3 = h(e, "total_revenue_fy_h"), h(e, "total_revenue_fy_h", 1), h(e, "total_revenue_fy_h", 3)
    eb = h(e, "ebitda_fy_h")
    m = {
        "pendapatan": rev, "laba_bersih": h(e, "net_income_fy_h"), "aset": h(e, "total_assets_fy_h"),
        "pertumbuhan": (rev / rev1 - 1) * 100 if rev and rev1 else None,
        "cagr3": ((rev / rev3) ** (1 / 3) - 1) * 100 if rev and rev3 and rev3 > 0 else None,
        "gm": e.get("gross_margin_fy"), "om": e.get("operating_margin_fy"), "nm": e.get("net_margin_fy"),
        "ebitda_m": bagi(eb, rev, 100), "roe": e.get("return_on_equity_fy"), "roa": e.get("return_on_assets_fy"),
        "cr": e.get("current_ratio_fy") or bagi(e.get("total_current_assets_fy"), e.get("total_current_liabilities_fy")),
        "der": bagi(e.get("total_liabilities_fy"), e.get("total_equity_fy")),
        "de": e.get("debt_to_equity_fy"),
        "nde": bagi(e.get("net_debt_fy"), eb) if eb and eb > 0 else None,
        "at": e.get("asset_turnover_fy"),
        "dso": bagi(365, e.get("receivables_turnover_fy")),
        "fcf_m": bagi(h(e, "free_cash_flow_fy_h"), rev, 100),
    }
    return m


def pengguna(path: Path) -> tuple[str, dict]:
    r = json.loads(path.read_text(encoding="utf-8-sig"))
    p = r["meta"]["periode"][-1]
    nilai = {k: r["rasio"].get(kr, {}).get("nilai", {}).get(p) for k, _, _, _, kr in METRIK if kr}
    pend = r["pos_utama"].get("pendapatan", {}).get("nilai", {})
    per = r["meta"]["periode"]
    if len(per) > 1 and pend.get(per[-2]):
        nilai["pertumbuhan"] = (pend[per[-1]] / pend[per[-2]] - 1) * 100
    return f"{r['meta']['perusahaan']} ({p})", nilai


def posisi(v, med, arah):
    if v is None or med is None:
        return None
    if abs(v - med) <= abs(med) * 0.05:
        return "setara"
    lebih = v > med
    return "lebih baik" if (lebih == (arah == "tinggi")) else "lebih lemah"


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Tabel pembanding emiten IDX")
    ap.add_argument("emiten", type=Path, help="Keluaran tv_emiten.mjs ambil")
    ap.add_argument("--rasio", type=Path, help="rasio.json perusahaan Anda (hitung_rasio.py)")
    ap.add_argument("--gaya", choices=["ringkas", "detail", "checklist"])
    ap.add_argument("--preferensi", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--diam", action="store_true")
    a = ap.parse_args(argv)
    pref = json.loads(a.preferensi.read_text(encoding="utf-8-sig")) if a.preferensi and a.preferensi.exists() else {}
    gaya = a.gaya or pref.get("gaya_narasi") or "detail"
    try:
        d = json.loads(a.emiten.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Tidak bisa membaca {a.emiten}: {e}", file=sys.stderr)
        return 1
    em = d.get("emiten") or {}
    if not em:
        print("Tidak ada data emiten di file.", file=sys.stderr)
        return 1
    hasil = {k: {"nama": v.get("description"), "industri": v.get("industry"), "kap": v.get("market_cap_basic"),
                 **hitung(v)} for k, v in em.items()}
    kode = list(hasil)
    median = {}
    for k, *_ in METRIK:
        vals = [hasil[t][k] for t in kode if hasil[t][k] is not None]
        median[k] = statistics.median(vals) if vals else None
    user_nama, user = pengguna(a.rasio) if a.rasio else (None, None)

    metrik = [m for m in METRIK if gaya != "ringkas" or m[0] in RINGKAS]
    L = [f"# Pembanding emiten IDX: {', '.join(kode)}", "",
         f"Data tahun buku terakhir yang tersedia di TradingView (diambil {d.get('diambil', '-')[:10]}).", ""]
    L += ["| Kode | Nama | Industri | Kapitalisasi | Pendapatan | Laba bersih |", "|---|---|---|---:|---:|---:|"]
    for t in kode:
        x = hasil[t]
        L.append(f"| {t} | {x['nama']} | {x['industri'] or '-'} | {rp(x['kap'])} | {rp(x['pendapatan'])} | {rp(x['laba_bersih'])} |")
    if gaya == "checklist" and user:
        L += ["", f"## Checklist: {user_nama} vs median {len(kode)} emiten", ""]
        for k, lab, sat, arah, kr in METRIK:
            pos = posisi(user.get(k), median[k], arah)
            if pos is None:
                continue
            L.append(f"- [{'x' if pos != 'lebih lemah' else ' '}] **{lab}**: {fmt(user.get(k), sat)} vs median "
                     f"{fmt(median[k], sat)}, {pos}")
    else:
        head = "| Metrik | " + " | ".join(kode) + " | Median |" + (" Perusahaan Anda | Posisi |" if user else "")
        sep = "|---|" + "---:|" * (len(kode) + 1) + ("---:|---|" if user else "")
        L += ["", "## Rasio", "", head, sep]
        for k, lab, sat, arah, kr in metrik:
            baris = f"| {lab} | " + " | ".join(fmt(hasil[t][k], sat) for t in kode) + f" | **{fmt(median[k], sat)}** |"
            if user:
                pos = posisi(user.get(k), median[k], arah)
                baris += f" {fmt(user.get(k), sat)} | {pos or '-'} |"
            L.append(baris)
    L += ["", "**Catatan sumber & definisi**", "",
          "- Data dari TradingView melalui pustaka TradingView-API (tidak resmi). Uji akurasi internal: pendapatan, laba bersih,",
          "  total aset, dan utang sama dengan sumber pembanding; **laba kotor bisa berbeda hingga sekitar 4%** karena klasifikasi.",
          "- ROE/ROA/margin memakai definisi TradingView; hari piutang diperkirakan dari perputaran piutang (365 ÷ perputaran).",
          "- Persediaan, utang usaha, dan beban bunga tidak tersedia, sehingga DIO/DPO/interest coverage emiten tidak ditampilkan.",
          "- Emiten adalah perusahaan besar & terbuka; pembanding ini konteks, bukan target. Verifikasi angka penting ke LK resmi"
          " (idx.co.id / situs emiten).", "",
          "_Alat bantu analisis, bukan nasihat investasi._", "", "Disusun dengan TQ Board Insight | totalquality.co.id"]
    md = "\n".join(L)
    if a.out_md:
        a.out_md.write_text(md, encoding="utf-8")
    if a.out_json:
        a.out_json.write_text(json.dumps({"emiten": hasil, "median": median, "pengguna": user, "pengguna_nama": user_nama},
                                         indent=1, ensure_ascii=False), encoding="utf-8")
    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
