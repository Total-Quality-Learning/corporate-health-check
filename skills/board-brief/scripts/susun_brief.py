#!/usr/bin/env python3
"""Susun board brief 1 halaman dari keluaran skill lain.

Pemakaian:
    python scripts/susun_brief.py --rasio rasio.json [--gejala gejala.json] [--kesiapan kesiapan.json] \
        --out-md brief.md [--out-html brief.html] [--kondisi "teks 3 kalimat"]

- rasio.json    : keluaran baca-laporan-keuangan/scripts/hitung_rasio.py (wajib)
- gejala.json   : keluaran red-flag-operasional/scripts/deteksi_gejala.py (opsional)
- kesiapan.json : keluaran cek-kesiapan-data/scripts/skor_kesiapan.py (opsional)
- --kondisi     : ganti paragraf "Kondisi singkat" (mis. hasil tulisan ulang AI). Angka di dalamnya
                  harus berasal dari brief/rasio; skrip tidak memeriksa isi teks ini.

Hanya pustaka standar Python.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

VERSI = "1.0.0"
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "brief.md"
DISCLAIMER = ("Alat bantu analisis, bukan nasihat investasi atau hasil audit. Penyebab yang disebut bersifat hipotesis "
              "dan perlu dibuktikan dengan data operasional.")
IKON = {"hijau": "🟢", "kuning": "🟡", "merah": "🔴", None: "–"}


def fmt(x, d=0):
    if x is None:
        return "-"
    s = f"{abs(x):,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return ("-" if x < 0 else "") + s


def fmt_uang(x):
    if x is None:
        return "-"
    s = fmt(abs(x))
    return f"({s})" if x < 0 else s


def muat(path):
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise SystemExit(f"Tidak bisa membaca {path}: {e}")


def tumbuh(a, b):
    if a is None or b is None or a <= 0:
        return None
    return (b - a) / a * 100


def status_naik_hari(a, b):
    if a is None or b is None:
        return None
    sel = b - a
    pct = tumbuh(a, b)
    if sel >= 20 or (pct is not None and pct >= 30):
        return "merah"
    if sel >= 10 or (pct is not None and pct >= 15):
        return "kuning"
    return "hijau"


def indikator(r: dict) -> list[dict]:
    per = r["meta"]["periode"]
    b = per[-1]
    a = per[-2] if len(per) > 1 else None
    R = lambda k, p: (r["rasio"].get(k, {}).get("nilai", {}).get(p) if p else None)       # noqa: E731
    P = lambda k, p: (r["pos_utama"].get(k, {}).get("nilai", {}).get(p) if p else None)   # noqa: E731
    out = []

    def add(nama, va, vb, satuan, status):
        out.append({"nama": nama, "a": va, "b": vb, "satuan": satuan, "status": status})

    gp = tumbuh(P("pendapatan", a), P("pendapatan", b))
    add("Pendapatan", P("pendapatan", a), P("pendapatan", b), "uang",
        None if gp is None else ("hijau" if gp >= 0 else ("kuning" if gp >= -5 else "merah")))
    nia, nib = P("laba_bersih", a), P("laba_bersih", b)
    gl = tumbuh(nia, nib)
    st = None
    if nib is not None:
        st = "merah" if nib <= 0 else (None if gl is None else ("hijau" if gl >= 0 else ("kuning" if gl >= -10 else "merah")))
    add("Laba bersih", nia, nib, "uang", st)
    cfo_b = P("arus_kas_operasi", b)
    add("Arus kas operasi", P("arus_kas_operasi", a), cfo_b, "uang",
        None if cfo_b is None else ("merah" if cfo_b < 0 else "hijau"))
    q = R("cfo_to_ni", b)
    add("Kas operasi / laba bersih", R("cfo_to_ni", a), q, "kali",
        None if q is None else ("hijau" if q >= 1 else ("kuning" if q >= 0.5 else "merah")))
    ga, gb = R("gross_margin", a), R("gross_margin", b)
    st = None
    if ga is not None and gb is not None:
        st = "merah" if gb - ga <= -2 else ("kuning" if gb - ga <= -1 else "hijau")
    add("Margin laba kotor", ga, gb, "persen", st)
    add("Hari persediaan (DIO)", R("dio", a), R("dio", b), "hari", status_naik_hari(R("dio", a), R("dio", b)))
    add("Hari piutang (DSO)", R("dso", a), R("dso", b), "hari", status_naik_hari(R("dso", a), R("dso", b)))
    cr = R("current_ratio", b)
    add("Current ratio", R("current_ratio", a), cr, "kali",
        None if cr is None else ("hijau" if cr >= 1.5 else ("kuning" if cr >= 1 else "merah")))
    ic = R("interest_coverage", b)
    if ic is not None:
        add("Interest coverage", R("interest_coverage", a), ic, "kali",
            "hijau" if ic >= 3 else ("kuning" if ic >= 1.5 else "merah"))
    der = R("der", b)
    add("DER (liabilitas / ekuitas)", R("der", a), der, "kali",
        None if der is None else ("hijau" if der <= 1 else ("kuning" if der <= 2 else "merah")))
    return out


def fmt_ind(v, satuan):
    if v is None:
        return "-"
    if satuan == "uang":
        return fmt_uang(v)
    if satuan == "persen":
        return fmt(v, 1) + "%"
    if satuan == "hari":
        return fmt(v) + " hari"
    return fmt(v, 2) + "x"


def kondisi_default(r, gejala) -> str:
    per = r["meta"]["periode"]
    b = per[-1]
    P = lambda k, p: r["pos_utama"].get(k, {}).get("nilai", {}).get(p)  # noqa: E731
    if len(per) < 2:
        return (f"Pendapatan periode {b} sebesar {fmt_uang(P('pendapatan', b))} dengan laba bersih "
                f"{fmt_uang(P('laba_bersih', b))}. Arus kas operasi {fmt_uang(P('arus_kas_operasi', b))}. "
                "Perbandingan tren membutuhkan minimal dua periode.")
    a = per[-2]
    gp, gl = tumbuh(P("pendapatan", a), P("pendapatan", b)), tumbuh(P("laba_bersih", a), P("laba_bersih", b))
    arah = lambda g: "naik" if g >= 0 else "turun"  # noqa: E731
    s1 = "Pendapatan"
    s1 += f" {arah(gp)} {fmt(abs(gp), 1)}%" if gp is not None else f" menjadi {fmt_uang(P('pendapatan', b))}"
    s1 += f" dan laba bersih {arah(gl)} {fmt(abs(gl), 1)}%" if gl is not None else \
        f" dengan laba bersih {fmt_uang(P('laba_bersih', b))}"
    s1 += f" dibanding {a}."
    ca, cb = P("arus_kas_operasi", a), P("arus_kas_operasi", b)
    if ca is not None and cb is not None:
        if cb < 0 <= ca:
            s2 = f"Namun arus kas dari operasi berbalik negatif, dari {fmt_uang(ca)} menjadi {fmt_uang(cb)}."
        elif cb < ca:
            s2 = f"Namun arus kas dari operasi turun dari {fmt_uang(ca)} menjadi {fmt_uang(cb)}."
        else:
            s2 = f"Arus kas dari operasi bergerak dari {fmt_uang(ca)} menjadi {fmt_uang(cb)}."
    else:
        s2 = ""
    if gejala and gejala.get("temuan"):
        t = gejala["temuan"]
        merah = sum(1 for x in t if x["tingkat"] == "merah")
        s3 = f"Terdeteksi {len(t)} gejala yang perlu ditelusuri ({merah} berstatus merah)."
        mk = gejala.get("ringkasan", {}).get("tambahan_modal_kerja")
        if mk and mk.get("nilai") and mk["nilai"] > 0:
            s3 = s3[:-1] + f", dengan tambahan dana tertahan di modal kerja sekitar {fmt_uang(mk['nilai'])} {mk['satuan']}."
    elif gejala:
        s3 = "Tidak ada gejala yang melewati ambang deteksi, namun laporan tahunan dapat menutupi masalah per bulan atau per lini."
    else:
        s3 = "Jalankan skill red-flag-operasional untuk memetakan gejala ke kemungkinan penyebab operasional."
    return " ".join(x for x in (s1, s2, s3) if x)


def susun_temuan(r, gejala, ind) -> list[str]:
    if gejala and gejala.get("temuan"):
        hasil = []
        for t in gejala["temuan"][:3]:
            teks = f"{IKON[t['tingkat']]} **{t['judul']}.** {t['ringkas']}"
            if t.get("dampak_kas") and t["dampak_kas"].get("nilai"):
                d = t["dampak_kas"]
                teks += f" {d['keterangan']}: ±{fmt_uang(d['nilai'])} {d['satuan']}."
            teks += f" Penyebab belum bisa dipastikan dari laporan keuangan; butuh data seperti: {t['data_pembukti'][0]}."
            hasil.append(teks)
        return hasil
    buruk = [i for i in ind if i["status"] in ("merah", "kuning")]
    buruk.sort(key=lambda i: 0 if i["status"] == "merah" else 1)
    if not buruk:
        return ["Tidak ada indikator utama yang berstatus kuning atau merah."]
    return [f"{IKON[i['status']]} **{i['nama']}**: {fmt_ind(i['a'], i['satuan'])} → {fmt_ind(i['b'], i['satuan'])}."
            for i in buruk[:3]]


def susun_pertanyaan(gejala) -> list[str]:
    qs = []
    if gejala and gejala.get("temuan"):
        for t in gejala["temuan"]:
            qs.append(t["pertanyaan_minggu_ini"][0])
        for t in gejala["temuan"]:
            for q in t["pertanyaan_minggu_ini"][1:]:
                qs.append(q)
    umum = [
        "Berapa hari yang dibutuhkan untuk menutup buku bulan lalu, dan apa penghambat terbesarnya?",
        "Angka mana yang paling sering berbeda antara gudang, produksi, dan akuntansi?",
        "Jika direksi meminta posisi stok dan piutang hari ini, kapan angka itu bisa tersedia?",
        "Produk atau pelanggan mana yang paling banyak menyerap modal kerja?",
        "Keputusan apa yang bulan lalu tertunda karena data belum tersedia?",
    ]
    for q in umum:
        if len(qs) >= 5:
            break
        qs.append(q)
    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:5]


def susun_kesiapan(k) -> str:
    if not k:
        return ""
    area = "; ".join(x["area"] for x in k["area_prioritas"])
    return (f"## 5. Kesiapan data & sistem\n\n**Level {k['level']} dari 4 – {k['nama_level']}.** "
            f"{k['deskripsi_level']} Area terlemah: {area}.\n")


def render_md(r, gejala, kes, kondisi, gaya="ringkas") -> tuple[str, dict]:
    per = r["meta"]["periode"]
    ind = indikator(r)
    sat = r["meta"].get("satuan", "")
    sat_label = "unit samaran" if "samaran" in sat else f"{sat} {'Rupiah' if r['meta'].get('mata_uang', 'IDR') == 'IDR' else r['meta'].get('mata_uang')}".strip()
    data = {
        "perusahaan": r["meta"]["perusahaan"],
        "periode": " → ".join(per[-2:]),
        "periode_a": per[-2] if len(per) > 1 else "-",
        "periode_b": per[-1],
        "satuan": sat_label,
        "kondisi_singkat": kondisi or kondisi_default(r, gejala),
        "tabel_indikator": "\n".join(
            f"| {i['nama']} | {fmt_ind(i['a'], i['satuan'])} | {fmt_ind(i['b'], i['satuan'])} | {IKON[i['status']]} |"
            for i in ind),
        "temuan": "\n".join((f"- [ ] {t}" if gaya == "checklist" else f"{n}. {t}")
                             for n, t in enumerate(susun_temuan(r, gejala, ind), 1)),
        "pertanyaan": "\n".join((f"- [ ] {q}" if gaya == "checklist" else f"{n}. {q}")
                                 for n, q in enumerate(susun_pertanyaan(gejala), 1)),
        "kesiapan": susun_kesiapan(kes),
        "disclaimer": DISCLAIMER,
    }
    teks = TEMPLATE.read_text(encoding="utf-8")
    for k, v in data.items():
        teks = teks.replace("{{" + k + "}}", str(v))
    while "\n\n\n" in teks:
        teks = teks.replace("\n\n\n", "\n\n")
    data["_indikator"] = ind
    data["_temuan"] = susun_temuan(r, gejala, ind)
    data["_pertanyaan"] = susun_pertanyaan(gejala)
    return teks, data


def md_inline(s: str) -> str:
    s = html.escape(s)
    parts = s.split("**")
    return "".join(f"<strong>{p}</strong>" if i % 2 else p for i, p in enumerate(parts))


def render_html(data: dict, kes) -> str:
    warna = {"hijau": "#1a7f37", "kuning": "#b58100", "merah": "#c62828", None: "#999"}
    label = {"hijau": "Aman", "kuning": "Perhatian", "merah": "Tindakan", None: "–"}
    baris = "".join(
        f"<tr><td>{html.escape(i['nama'])}</td><td class=n>{fmt_ind(i['a'], i['satuan'])}</td>"
        f"<td class=n>{fmt_ind(i['b'], i['satuan'])}</td>"
        f"<td><span class=dot style='background:{warna[i['status']]}'></span>{label[i['status']]}</td></tr>"
        for i in data["_indikator"])
    temuan = "".join(f"<li>{md_inline(t)}</li>" for t in data["_temuan"])
    tanya = "".join(f"<li>{html.escape(q)}</li>" for q in data["_pertanyaan"])
    kes_html = ""
    if kes:
        area = "; ".join(x["area"] for x in kes["area_prioritas"])
        kes_html = (f"<h2>5. Kesiapan data &amp; sistem</h2><p><strong>Level {kes['level']} dari 4 – "
                    f"{html.escape(kes['nama_level'])}.</strong> {html.escape(kes['deskripsi_level'])} "
                    f"Area terlemah: {html.escape(area)}.</p>")
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Board Brief</title>
<style>
@page {{ size: A4; margin: 14mm; }}
body {{ font: 13px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color:#1d1d1f; background:#fff;
       max-width: 800px; margin: 24px auto; padding: 0 16px; }}
h1 {{ font-size: 21px; margin: 0 0 2px; }} h2 {{ font-size: 14px; margin: 18px 0 6px; text-transform: uppercase;
      letter-spacing: .04em; color:#444; border-bottom:1px solid #ddd; padding-bottom:3px; }}
.meta {{ color:#666; margin-bottom: 10px; }}
table {{ width:100%; border-collapse: collapse; }} td, th {{ padding: 4px 6px; border-bottom:1px solid #eee; text-align:left; }}
th {{ font-weight:600; color:#555; }} .n {{ text-align:right; font-variant-numeric: tabular-nums; }}
.dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:middle; }}
ol {{ padding-left: 20px; margin: 4px 0; }} li {{ margin: 3px 0; }}
.note {{ color:#777; font-size: 11px; }} footer {{ margin-top: 18px; color:#666; font-size: 11px; border-top:1px solid #ddd; padding-top:6px; }}
</style></head><body>
<h1>Board Brief: {html.escape(data['perusahaan'])}</h1>
<div class=meta>Periode {html.escape(data['periode'])} · Satuan {html.escape(data['satuan'])}</div>
<h2>1. Kondisi singkat</h2><p>{md_inline(data['kondisi_singkat'])}</p>
<h2>2. Indikator utama</h2>
<table><tr><th>Indikator</th><th class=n>{html.escape(data['periode_a'])}</th><th class=n>{html.escape(data['periode_b'])}</th><th>Status</th></tr>{baris}</table>
<p class=note>Status berdasarkan ambang umum, bukan benchmark industri.</p>
<h2>3. Tiga temuan terpenting</h2><ol>{temuan}</ol>
<h2>4. Pertanyaan untuk CFO / tim minggu ini</h2><ol>{tanya}</ol>
{kes_html}
<footer><em>{html.escape(DISCLAIMER)}</em><br>Disusun dengan TQ Board Insight · totalquality.co.id</footer>
</body></html>
"""


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Susun board brief 1 halaman")
    ap.add_argument("--rasio", required=True)
    ap.add_argument("--gejala")
    ap.add_argument("--kesiapan")
    ap.add_argument("--kondisi", help="Paragraf kondisi singkat pengganti (maks. 3 kalimat)")
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--out-html", type=Path)
    ap.add_argument("--gaya", choices=["ringkas", "checklist"], help="checklist: temuan & pertanyaan sebagai kotak centang")
    ap.add_argument("--preferensi", type=Path)
    ap.add_argument("--diam", action="store_true")
    a = ap.parse_args(argv)
    pref = json.loads(a.preferensi.read_text(encoding="utf-8-sig")) if a.preferensi and a.preferensi.exists() else {}
    gaya = a.gaya or ("checklist" if pref.get("gaya_narasi") == "checklist" else "ringkas")
    r = muat(a.rasio)
    if not r or "rasio" not in r:
        print("--rasio harus keluaran hitung_rasio.py.", file=sys.stderr)
        return 1
    gejala, kes = muat(a.gejala), muat(a.kesiapan)
    md, data = render_md(r, gejala, kes, a.kondisi, gaya)
    if a.out_md:
        a.out_md.write_text(md, encoding="utf-8")
    if a.out_html:
        a.out_html.write_text(render_html(data, kes), encoding="utf-8")
    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
