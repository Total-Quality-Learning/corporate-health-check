#!/usr/bin/env python3
"""Visualisasi rasio untuk direksi: grafik, penjelasan grafik, atau keduanya (HTML satu file, siap cetak).

Pemakaian:
    python scripts/visualisasi.py rasio.json --out visual.html                    # grafik + penjelasan
    python scripts/visualisasi.py rasio.json --out visual.html --mode grafik      # hanya grafik
    python scripts/visualisasi.py rasio.json --out visual.html --mode penjelasan  # hanya teks penjelasan
    python scripts/visualisasi.py rasio.json --out visual.md --mode penjelasan    # penjelasan dalam Markdown
    python scripts/visualisasi.py rasio.json --out visual.html --preferensi preferensi.json

Masukan: keluaran hitung_rasio.py --out-json. Grafik digambar sebagai SVG di dalam HTML (tanpa pustaka tambahan).
Judul setiap grafik = kesimpulannya (gaya direksi). Semua angka dari rasio.json.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

WARNA = {"a": "#0e7490", "b": "#15803d", "c": "#be123c", "d": "#b45309", "abu": "#94a3b8", "navy": "#12263f"}


def idn(x, d=1):
    return f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")


class Satuan:
    def __init__(self, meta):
        s = str(meta.get("satuan", "")).lower()
        self.samaran = "samaran" in s
        self.faktor = {"juta": 1e6, "ribu": 1e3, "miliar": 1e9}.get(s.split()[0] if s else "", 1) if not self.samaran else 1
        self.rp = meta.get("mata_uang", "IDR") == "IDR" and not self.samaran

    def uang(self, v):
        if v is None:
            return "–"
        if self.samaran:
            return idn(v, 0) + " u"
        rupiah = v * self.faktor
        a = abs(rupiah)
        if a >= 1e12:
            s = idn(a / 1e12, 2) + " T"
        elif a >= 1e9:
            s = idn(a / 1e9, 2) + " M"
        elif a >= 1e6:
            s = idn(a / 1e6, 0) + " JT"
        else:
            s = idn(a, 0)
        return ("−" if v < 0 else "") + ("Rp" if self.rp else "") + s


def fmt(v, sat):
    if v is None:
        return "–"
    t = "−" if v < 0 else ""
    a = abs(v)
    return {"persen": f"{t}{idn(a, 1)}%", "hari": f"{t}{idn(a, 0)} hari", "kali": f"{t}{idn(a, 2)}x",
            "skor": f"{t}{idn(a, 2)}"}.get(sat, f"{t}{idn(a, 1)}")


# ------------------------------------------------------------------ SVG ---
def bar_kelompok(kategori, seri, fmt_label, ref=None, ref_label=""):
    """kategori: label sumbu x; seri: [(nama, warna, [nilai per kategori])]."""
    W, H, L, R, T, B = 640, 260, 46, 12, 22, 40
    vals = [v for _, _, vs in seri for v in vs if v is not None] + ([ref] if ref is not None else []) + [0]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        hi = lo + 1
    pad = (hi - lo) * 0.12
    lo, hi = (lo - pad if lo < 0 else 0), hi + pad
    y = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)  # noqa: E731
    gw = (W - L - R) / len(kategori)
    bw = gw * 0.75 / max(len(seri), 1)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="grafik batang">',
         f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#94a3b8"/>']
    if ref is not None:
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{y(ref):.1f}" y2="{y(ref):.1f}" stroke="#be123c" stroke-dasharray="5 4"/>'
                 f'<text x="{W - R}" y="{y(ref) - 4:.1f}" font-size="11" text-anchor="end" fill="#be123c">{html.escape(ref_label)}</text>')
    for i, kat in enumerate(kategori):
        x0 = L + i * gw + gw * 0.125
        for j, (_, warna, vs) in enumerate(seri):
            v = vs[i]
            if v is None:
                continue
            x = x0 + j * bw
            top, bot = min(y(v), y(0)), max(y(v), y(0))
            g.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw * 0.9:.1f}" height="{max(bot - top, 1):.1f}" rx="2" fill="{warna}"/>')
            ty = top - 4 if v >= 0 else bot + 12
            g.append(f'<text x="{x + bw * 0.45:.1f}" y="{ty:.1f}" font-size="10.5" text-anchor="middle" fill="#334155">{html.escape(fmt_label(v))}</text>')
        g.append(f'<text x="{L + i * gw + gw / 2:.1f}" y="{H - 14}" font-size="12" text-anchor="middle" fill="#475569">{html.escape(kat)}</text>')
    g.append("</svg>")
    leg = "".join(f'<span><i style="background:{w}"></i>{html.escape(n)}</span>' for n, w, _ in seri)
    return "".join(g) + f'<div class="leg">{leg}</div>'


def pita_zona(nilai, zona, label_fmt):
    """Bar horizontal dengan zona warna (mis. Altman Z'')."""
    W, H = 640, 70
    lo, hi = zona[0][0], zona[-1][1]
    x = lambda v: 20 + (min(max(v, lo), hi) - lo) / (hi - lo) * (W - 40)  # noqa: E731
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="pita zona">']
    for a, b, warna, nama in zona:
        g.append(f'<rect x="{x(a):.1f}" y="18" width="{x(b) - x(a):.1f}" height="20" fill="{warna}"/>'
                 f'<text x="{(x(a) + x(b)) / 2:.1f}" y="54" font-size="11" text-anchor="middle" fill="#475569">{html.escape(nama)}</text>')
    if nilai is not None:
        g.append(f'<line x1="{x(nilai):.1f}" x2="{x(nilai):.1f}" y1="10" y2="44" stroke="#12263f" stroke-width="3"/>'
                 f'<text x="{x(nilai):.1f}" y="9" font-size="12" font-weight="700" text-anchor="middle" fill="#12263f">{html.escape(label_fmt(nilai))}</text>')
    g.append("</svg>")
    return "".join(g)


# ------------------------------------------------------------ narasi ----
def arah(a, b, naik="naik", turun="turun"):
    if a is None or b is None:
        return "tidak dapat dibandingkan"
    return naik if b > a else (turun if b < a else "tetap")


def pct_ubah(a, b):
    if a in (None, 0) or b is None:
        return None
    return (b - a) / abs(a) * 100


def bangun_bagian(r: dict, istilah: str):
    m, per = r["meta"], r["meta"]["periode"]
    S = Satuan(m)
    pos, ra = r["pos_utama"], r["rasio"]
    V = lambda k: [ra[k]["nilai"].get(p) for p in per]  # noqa: E731
    P = lambda k: [pos.get(k, {}).get("nilai", {}).get(p) for p in per]  # noqa: E731
    a, b = (per[-2], per[-1]) if len(per) > 1 else (None, per[-1])
    jelaskan = istilah != "teknis"
    bagian = []

    # 1. Laba vs kas
    pend, lb, ocf = P("pendapatan"), P("laba_bersih"), P("arus_kas_operasi")
    gl, gp = pct_ubah(lb[-2] if a else None, lb[-1]), pct_ubah(pend[-2] if a else None, pend[-1])
    judul = (f"Laba {arah(lb[-2], lb[-1]) if a else ''} {idn(abs(gl), 0) + '%' if gl is not None else ''}, "
             f"arus kas operasi {S.uang(ocf[-1])}").replace("  ", " ")
    if a and ocf[-1] is not None and ocf[-2] is not None and lb[-1] > lb[-2] and ocf[-1] < ocf[-2]:
        judul = f"Laba naik {idn(gl, 0)}%, tetapi kas dari operasi turun ke {S.uang(ocf[-1])}"
    bagian.append({
        "judul": judul,
        "grafik": bar_kelompok(per, [("Pendapatan", WARNA["a"], [x / 1 for x in pend]),
                                     ("Laba bersih", WARNA["b"], lb), ("Arus kas operasi", WARNA["c"], ocf)], S.uang)
        if None not in pend else "",
        "apa": "Pendapatan, laba bersih, dan arus kas dari operasi per periode.",
        "cara": ("Batang hijau (laba) dan merah (kas operasi) idealnya setinggi atau sejajar. Jika batang merah jauh lebih "
                 "pendek atau di bawah nol, laba belum menjadi uang tunai — biasanya tertahan di piutang atau persediaan."
                 if jelaskan else "Bandingkan laba bersih dengan arus kas operasi."),
        "fakta": [f"Pendapatan {S.uang(pend[-2]) + ' → ' if a else ''}{S.uang(pend[-1])}" + (f" ({'+' if gp >= 0 else '−'}{idn(abs(gp), 1)}%)" if gp is not None else ""),
                  f"Laba bersih {S.uang(lb[-2]) + ' → ' if a else ''}{S.uang(lb[-1])}" + (f" ({'+' if gl >= 0 else '−'}{idn(abs(gl), 1)}%)" if gl is not None else ""),
                  f"Arus kas operasi {S.uang(ocf[-2]) + ' → ' if a else ''}{S.uang(ocf[-1])}"],
        "tanya": "Ke mana selisih antara laba dan kas operasi tahun ini — piutang, persediaan, atau pembayaran pemasok?",
    })
    # 2. Margin
    gm, om, nm = V("gross_margin"), V("operating_margin"), V("net_margin")
    d_gm = (gm[-1] - gm[-2]) if (a and None not in (gm[-1], gm[-2])) else None
    bagian.append({
        "judul": (f"Margin kotor {'tergerus' if d_gm is not None and d_gm <= -1 else 'relatif terjaga' if d_gm is not None else ''} "
                  f"{fmt(gm[-1], 'persen')}" + (f" ({'+' if d_gm >= 0 else '−'}{idn(abs(d_gm), 1)} poin)" if d_gm is not None else "")).strip(),
        "grafik": bar_kelompok(per, [("Margin kotor", WARNA["navy"], gm), ("Margin usaha", WARNA["a"], om),
                                     ("Margin bersih", WARNA["b"], nm)], lambda v: fmt(v, "persen")),
        "apa": "Berapa rupiah tersisa dari setiap Rp100 penjualan pada tiap lapis: setelah HPP, setelah beban usaha, dan akhir.",
        "cara": ("Jarak antara margin kotor dan margin usaha = porsi beban usaha. Jarak margin usaha ke margin bersih = bunga, "
                 "pajak, dan pos lain. Penurunan margin kotor biasanya terkait harga bahan, pemborosan, atau harga jual."
                 if jelaskan else "Perhatikan perubahan tiap lapis margin."),
        "fakta": [f"Margin kotor {fmt(gm[-2], 'persen') + ' → ' if a else ''}{fmt(gm[-1], 'persen')}",
                  f"Margin usaha {fmt(om[-2], 'persen') + ' → ' if a else ''}{fmt(om[-1], 'persen')}",
                  f"Margin bersih {fmt(nm[-2], 'persen') + ' → ' if a else ''}{fmt(nm[-1], 'persen')}"],
        "tanya": "Produk atau pelanggan mana yang marginnya turun paling besar, dan berapa nilai reject/rework dalam rupiah?",
    })
    # 3. Modal kerja
    dso, dio, dpo, ccc = V("dso"), V("dio"), V("dpo"), V("ccc")
    d_ccc = (ccc[-1] - ccc[-2]) if (a and None not in (ccc[-1], ccc[-2])) else None
    bagian.append({
        "judul": (f"Uang tertahan {fmt(ccc[-1], 'hari')} dalam siklus operasi"
                  + (f" ({'+' if d_ccc >= 0 else '−'}{idn(abs(d_ccc), 0)} hari)" if d_ccc is not None else "")),
        "grafik": bar_kelompok(per, [("DSO (piutang)", WARNA["a"], dso), ("DIO (persediaan)", WARNA["d"], dio),
                                     ("DPO (utang usaha)", WARNA["abu"], dpo)], lambda v: fmt(v, "hari")),
        "apa": "Hari piutang (DSO), hari persediaan (DIO), dan hari pembayaran pemasok (DPO).",
        "cara": ("Siklus konversi kas = DSO + DIO − DPO: berapa hari uang perusahaan 'terkunci' dari membeli bahan sampai "
                 "dibayar pelanggan. Batang biru dan oranye yang memanjang berarti kebutuhan modal kerja naik."
                 if jelaskan else "Siklus konversi kas = DSO + DIO − DPO."),
        "fakta": [f"DSO {fmt(dso[-2], 'hari') + ' → ' if a else ''}{fmt(dso[-1], 'hari')}",
                  f"DIO {fmt(dio[-2], 'hari') + ' → ' if a else ''}{fmt(dio[-1], 'hari')}",
                  f"DPO {fmt(dpo[-2], 'hari') + ' → ' if a else ''}{fmt(dpo[-1], 'hari')}",
                  f"Siklus konversi kas {fmt(ccc[-2], 'hari') + ' → ' if a else ''}{fmt(ccc[-1], 'hari')}"],
        "tanya": "Berapa lama tim bisa memberi daftar piutang lewat 60 hari dan stok berumur lebih dari 90 hari, lengkap dengan nilainya?",
    })
    # 4. Likuiditas & utang
    cr, der, icr = V("current_ratio"), V("der"), V("interest_coverage")
    bagian.append({
        "judul": f"Rasio lancar {fmt(cr[-1], 'kali')}, DER {fmt(der[-1], 'kali')}, interest coverage {fmt(icr[-1], 'kali')}",
        "grafik": bar_kelompok(per, [("Rasio lancar", WARNA["a"], cr), ("DER", WARNA["d"], der)],
                               lambda v: fmt(v, "kali"), ref=1.5, ref_label="batas aman rasio lancar 1,5x"),
        "apa": "Kemampuan membayar kewajiban jangka pendek (rasio lancar) dan seberapa besar dibiayai utang (DER).",
        "cara": ("Rasio lancar di atas garis putus (1,5x) umumnya nyaman. DER di atas 1x berarti utang lebih besar dari modal "
                 "sendiri. Interest coverage di bawah 3x berarti laba usaha mulai sempit untuk menutup bunga."
                 if jelaskan else "Ambang umum: rasio lancar ≥ 1,5x; DER ≤ 1x; interest coverage ≥ 3x."),
        "fakta": [f"Rasio lancar {fmt(cr[-2], 'kali') + ' → ' if a else ''}{fmt(cr[-1], 'kali')}",
                  f"DER {fmt(der[-2], 'kali') + ' → ' if a else ''}{fmt(der[-1], 'kali')}",
                  f"Interest coverage {fmt(icr[-2], 'kali') + ' → ' if a else ''}{fmt(icr[-1], 'kali')}"],
        "tanya": "Jika penjualan turun 15% selama 3 bulan, berapa lama kas dan fasilitas kredit cukup?",
    })
    # 5. Altman
    z = V("altman_z")[-1]
    if z is not None:
        zona = "aman" if z > 2.6 else ("abu-abu" if z >= 1.1 else "rawan")
        bagian.append({
            "judul": f"Skor kesehatan Altman Z'' {fmt(z, 'skor')}: zona {zona}",
            "grafik": pita_zona(z, [(-1, 1.1, "#fecdd3", "rawan < 1,10"), (1.1, 2.6, "#fde68a", "abu-abu"),
                                    (2.6, 8, "#bbf7d0", "aman > 2,60")], lambda v: fmt(v, "skor")),
            "apa": "Skor statistik dari modal kerja, saldo laba, laba usaha, dan ekuitas terhadap aset/liabilitas.",
            "cara": ("Semakin ke kanan semakin sehat. Ini sinyal awal untuk perusahaan non-publik, bukan vonis; tetap lihat "
                     "arus kas dan tren." if jelaskan else "Zona: < 1,10 rawan; 1,10–2,60 abu-abu; > 2,60 aman."),
            "fakta": [f"Perhitungan: {ra['altman_z'].get('perhitungan', {}).get(b, '-')}"],
            "tanya": "Komponen mana yang paling menurunkan skor — modal kerja, laba usaha, atau struktur utang?",
        })
    return bagian


CSS = """
:root{--ink:#122033;--muted:#526075;--line:#d5dce6;--soft:#eef2f7;--navy:#12263f;--accent:#0e7490}
*{box-sizing:border-box} body{margin:0;background:#f3f5f8;color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
header{background:var(--navy);color:#fff;border-radius:10px;padding:18px 22px;margin-bottom:14px}
header h1{margin:0 0 4px;font-size:22px} header p{margin:0;opacity:.85;font-size:13px}
.kartu{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px 20px;margin:0 0 14px;break-inside:avoid}
.kartu h2{font-size:18px;margin:0 0 8px;color:var(--navy)}
svg{width:100%;height:auto;display:block} .leg{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-top:4px}
.leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
.jel{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;font-size:14px}
.jel div{background:var(--soft);border-radius:8px;padding:10px 12px} .jel b{display:block;color:var(--navy);margin-bottom:2px}
.jel .tanya{grid-column:1/-1;background:#fef3c7}
ul{margin:4px 0;padding-left:18px} footer{max-width:980px;margin:0 auto 24px;padding:0 16px;color:var(--muted);font-size:12px}
@media (max-width:700px){.jel{grid-template-columns:1fr}}
@media print{body{background:#fff} main{padding:0} .kartu{border:none;border-bottom:1px solid #ccc;border-radius:0}}
"""


def ke_html(r, bagian, mode):
    m = r["meta"]
    isi = []
    for i, s in enumerate(bagian, 1):
        jel = ""
        if mode in ("penjelasan", "keduanya"):
            jel = (f'<div class="jel"><div><b>Apa yang ditampilkan</b>{html.escape(s["apa"])}</div>'
                   f'<div><b>Cara membaca</b>{html.escape(s["cara"])}</div>'
                   f'<div><b>Yang terjadi</b><ul>{"".join(f"<li>{html.escape(x)}</li>" for x in s["fakta"])}</ul></div>'
                   f'<div><b>Catatan</b>Angka dari skrip deterministik; metode: {html.escape(m.get("metode", ""))}</div>'
                   f'<div class="tanya"><b>Pertanyaan untuk tim minggu ini</b>{html.escape(s["tanya"])}</div></div>')
        graf = s["grafik"] if mode in ("grafik", "keduanya") else ""
        isi.append(f'<section class="kartu"><h2>{i}. {html.escape(s["judul"])}</h2>{graf}{jel}</section>')
    return f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Visual Rasio</title><style>{CSS}</style></head><body><main>
<header><h1>{html.escape(m['perusahaan'])} — gambaran keuangan</h1>
<p>Periode {html.escape(' · '.join(m['periode']))} · satuan pos: {html.escape(str(m.get('mata_uang', '')))} {html.escape(str(m.get('satuan', '')))} · mode: {html.escape(mode)}</p></header>
{''.join(isi)}</main>
<footer>Alat bantu analisis, bukan nasihat investasi atau hasil audit. Ambang adalah ambang umum, bukan benchmark industri.<br>
Disusun dengan TQ Board Insight · totalquality.co.id</footer></body></html>"""


def ke_md(r, bagian):
    L = [f"# {r['meta']['perusahaan']} — penjelasan grafik", ""]
    for i, s in enumerate(bagian, 1):
        L += [f"## {i}. {s['judul']}", "", f"**Apa yang ditampilkan:** {s['apa']}", "", f"**Cara membaca:** {s['cara']}", "",
              "**Yang terjadi:**"] + [f"- {x}" for x in s["fakta"]] + ["", f"**Pertanyaan untuk tim minggu ini:** {s['tanya']}", ""]
    L += ["_Alat bantu analisis, bukan nasihat investasi atau hasil audit._", "", "Disusun dengan TQ Board Insight · totalquality.co.id"]
    return "\n".join(L)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Visualisasi rasio untuk direksi")
    ap.add_argument("rasio", type=Path, help="Keluaran hitung_rasio.py --out-json")
    ap.add_argument("--out", type=Path, required=True, help=".html (grafik/penjelasan) atau .md (penjelasan)")
    ap.add_argument("--mode", choices=["grafik", "penjelasan", "keduanya"])
    ap.add_argument("--istilah", choices=["awam", "campuran", "teknis"])
    ap.add_argument("--preferensi", type=Path)
    a = ap.parse_args(argv)
    pref = {}
    if a.preferensi and a.preferensi.exists():
        pref = json.loads(a.preferensi.read_text(encoding="utf-8-sig"))
    mode = a.mode or {"tanpa": "penjelasan"}.get(pref.get("visual"), pref.get("visual")) or "keduanya"
    if mode not in ("grafik", "penjelasan", "keduanya"):
        mode = "keduanya"
    istilah = a.istilah or pref.get("istilah") or "awam"
    try:
        r = json.loads(a.rasio.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Tidak bisa membaca {a.rasio}: {e}", file=sys.stderr)
        return 1
    if "rasio" not in r:
        print("File bukan keluaran hitung_rasio.py.", file=sys.stderr)
        return 1
    bagian = bangun_bagian(r, istilah)
    if a.out.suffix.lower() == ".md":
        a.out.write_text(ke_md(r, bagian), encoding="utf-8")
    else:
        a.out.write_text(ke_html(r, bagian, mode), encoding="utf-8")
    print(f"Visual ditulis: {a.out} (mode {mode}, {len(bagian)} bagian)")
    for s in bagian:
        print(" -", s["judul"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
