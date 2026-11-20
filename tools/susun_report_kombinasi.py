#!/usr/bin/env python3
"""Generator Report Kombinasi Lintas-Skill (HTML siap cetak PDF + Markdown).

Menggabungkan keluaran JSON deterministik dari berbagai skill Corporate Health Check
menjadi satu paket laporan direksi terpadu:
- --rasio     : rasio.json (tahunan/interim, hitung_rasio.py)
- --laporan   : laporan.json (bulanan, susun_laporan.py)
- --gejala    : gejala.json (red-flag-operasional)
- --kesiapan  : kesiapan.json (cek-kesiapan-data)
- --emiten    : pembanding.json (ringkas_emiten.py --out-json)
- --ekonomi   : risiko-ekonomi.json (analisa_risiko_ekonomi.py --out-json)
- --sdm       : sdm-budget.json (analisa_sdm_budget.py --out-json)
- --uji-kas   : uji-kas.json (uji_ketahanan_kas.py --out-json)

Pemakaian (dari root repo):
    python tools/susun_report_kombinasi.py --rasio rasio.json --gejala gejala.json --emiten pembanding.json --out paket-direksi.html --out-md paket-direksi.md
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html as _html
import json
import re
import sys
from pathlib import Path
from typing import Any


def _esc(v: Any) -> str:
    return _html.escape("" if v is None else str(v))


def _idn(x: float | None, d: int = 1) -> str:
    if x is None:
        return "-"
    s = f"{abs(x):,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return f"-{s}" if x < 0 else s


def _skala_ke_juta(satuan: str) -> float:
    s = (satuan or "").lower()
    if "samaran" in s:
        return 1.0
    if s.startswith("ribu"):
        return 0.001
    if s.startswith("miliar"):
        return 1_000.0
    if "juta" in s:
        return 1.0
    return 1e-6


def _parse_angka(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    if not s or s in ("-", "--", "n/a"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        x = float(s)
        return -x if neg else x
    except ValueError:
        return None


def _parse_uang_fmt(teks: str | None) -> float | None:
    if not teks or teks == "-":
        return None
    s = teks.strip()
    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.lstrip("+-").strip("()").strip()
    s = re.sub(r"^rp\.?\s*", "", s, flags=re.IGNORECASE)
    faktor = 1.0
    if s.endswith(" T"):
        faktor, s = 1_000_000.0, s[:-2].strip()
    elif s.endswith(" M"):
        faktor, s = 1_000.0, s[:-2].strip()
    elif s.endswith(" JT"):
        faktor, s = 1.0, s[:-3].strip()
    elif s.endswith(" u"):
        faktor, s = 1.0, s[:-2].strip()
    v = _parse_angka(s)
    return ((-v if neg else v) * faktor) if v is not None else None


def fmt_uang(val_juta: float | None, samaran: bool = False) -> str:
    if val_juta is None:
        return "-"
    t = "-" if val_juta < 0 else ""
    a = abs(val_juta)
    if samaran:
        return f"{t}{_idn(a, 1)} u"
    if a >= 1_000_000:
        return f"{t}Rp{_idn(a / 1_000_000, 2)} T"
    if a >= 1_000:
        return f"{t}Rp{_idn(a / 1_000, 2)} M"
    if a >= 1:
        return f"{t}Rp{_idn(a, 1)} JT"
    ribu = round(a * 1_000)
    return f"{t}Rp{_idn(ribu, 0)}.000" if ribu > 0 else "Rp0"


def _status_badge(status: str) -> str:
    low = (status or "").lower()
    if any(k in low for k in ("kritis", "merah", "tinggi", "lebih lemah", "defisit")):
        cls, sym = "st-red", "&#9632;"
    elif any(k in low for k in ("perhatian", "waspada", "kuning", "sedang")):
        cls, sym = "st-amber", "&#9650;"
    elif any(k in low for k in ("perlu data", "data")):
        cls, sym = "st-blue", "?"
    else:
        cls, sym = "st-green", "&#9679;"
    return f'<span class="badge {cls}">{sym} {_esc(status)}</span>'


def _muat_json(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Berkas tidak ditemukan: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ekstrak_ringkasan_keuangan(rasio: dict[str, Any] | None, laporan: dict[str, Any] | None) -> dict[str, Any]:
    """Satukan ringkasan angka inti dari rasio.json (tahunan) dan/atau laporan.json (bulanan)."""
    out: dict[str, Any] = {
        "perusahaan": "Perusahaan",
        "periode": "-",
        "periode_lalu": "-",
        "samaran": False,
        "fiktif": False,
        "pos": [],
        "skor": None,
        "putusan_teks": "",
    }
    if rasio:
        meta = rasio.get("meta", {})
        per = meta.get("periode", [])
        p = per[-1] if per else "-"
        p0 = per[-2] if len(per) > 1 else None
        sat = meta.get("satuan", "juta")
        samaran = "samaran" in sat.lower()
        skala = _skala_ke_juta(sat)
        pu = rasio.get("pos_utama", {})
        out["perusahaan"] = meta.get("perusahaan", out["perusahaan"])
        out["periode"] = p
        out["periode_lalu"] = p0 or "-"
        out["samaran"] = samaran
        out["fiktif"] = "FIKTIF" in out["perusahaan"].upper()

        pos_list = []
        for k, label in (
            ("pendapatan", "Pendapatan"),
            ("laba_kotor", "Laba kotor"),
            ("laba_usaha", "Laba usaha"),
            ("laba_bersih", "Laba bersih"),
            ("arus_kas_operasi", "Arus kas operasi"),
            ("arus_kas_bebas", "Arus kas bebas"),
        ):
            nilai_map = pu.get(k, {}).get("nilai", {})
            vk = (nilai_map.get(p) * skala) if nilai_map.get(p) is not None else None
            vl = (nilai_map.get(p0) * skala) if (p0 and nilai_map.get(p0) is not None) else None
            chg = ((vk / vl) - 1.0) * 100.0 if (vk is not None and vl and vl != 0) else None
            pos_list.append({"kunci": k, "label": label, "kini": vk, "lalu": vl, "chg_pct": chg})
        out["pos"] = pos_list

    if laporan:
        meta = laporan.get("meta", {})
        pid = "ytd" if "ytd" in laporan.get("kpi", {}) else "month"
        out["perusahaan"] = meta.get("perusahaan", out["perusahaan"])
        out["samaran"] = out["samaran"] or bool(meta.get("samaran"))
        out["fiktif"] = out["fiktif"] or ("FIKTIF" in out["perusahaan"].upper())
        out["skor"] = laporan.get("skor", {}).get(pid)
        out["putusan_teks"] = laporan.get("putusan", {}).get(pid, {}).get("teks", "")
        if not rasio:
            out["periode"] = laporan.get("periode", {}).get(pid, {}).get("short") or meta.get("bulan_aktif", "-")
            out["periode_lalu"] = "Tahun lalu"
            lr_rows = {row["nama"]: row for row in laporan.get("pos", {}).get(pid, {}).get("yoy", {}).get("lr", [])}
            ak_rows = {row["nama"]: row for row in laporan.get("pos", {}).get(pid, {}).get("yoy", {}).get("ak", [])}
            pos_list = []
            for nama, label, src in (
                ("Pendapatan neto", "Pendapatan", lr_rows),
                ("Laba kotor", "Laba kotor", lr_rows),
                ("Laba usaha (EBIT)", "Laba usaha", lr_rows),
                ("Laba bersih", "Laba bersih", lr_rows),
                ("Arus kas operasi", "Arus kas operasi", ak_rows),
                ("Arus kas bebas", "Arus kas bebas", ak_rows),
            ):
                row = src.get(nama) or {}
                vk = _parse_uang_fmt(row.get("cur"))
                vl = _parse_uang_fmt(row.get("comp"))
                chg = ((vk / vl) - 1.0) * 100.0 if (vk is not None and vl and vl != 0) else None
                pos_list.append({"kunci": label.lower().replace(" ", "_"), "label": label, "kini": vk, "lalu": vl, "chg_pct": chg})
            out["pos"] = pos_list
    return out


def _svg_waterfall_kas(pos_list: list[dict[str, Any]], samaran: bool) -> str:
    """Gambar diagram batang/jembatan sederhana dari Pendapatan -> Laba -> Arus Kas."""
    items = [(p["label"], p["kini"]) for p in pos_list if p["kini"] is not None]
    if not items:
        return ""
    w, h = 680, 220
    pad_l, pad_r, pad_t, pad_b = 45, 20, 24, 52
    plot_w, plot_h = w - pad_l - pad_r, h - pad_t - pad_b
    max_v = max([abs(v) for _, v in items] + [1.0])
    min_v = min([v for _, v in items] + [0.0])
    span = max(max_v - min_v, 1.0)
    zero_y = pad_t + (max_v / span) * plot_h
    bw = plot_w / len(items) * 0.56
    step = plot_w / len(items)

    bars = [f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{w - pad_r}" y2="{zero_y:.1f}" stroke="#94a3b8" stroke-dasharray="3,3"/>']
    for i, (lbl, val) in enumerate(items):
        cx = pad_l + step * i + step / 2
        bh = max(2.0, abs(val) / span * plot_h)
        y = (zero_y - bh) if val >= 0 else zero_y
        color = "#0f766e" if val >= 0 else "#b91c1c"
        if "Pendapatan" in lbl:
            color = "#1d4ed8"
        val_y = (y - 6) if val >= 0 else (y + bh + 12)
        bars.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" fill="{color}"/>')
        bars.append(f'<text x="{cx:.1f}" y="{val_y:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="#1e293b">{_esc(fmt_uang(val, samaran))}</text>')
        bars.append(f'<text x="{cx:.1f}" y="{h - 14}" text-anchor="middle" font-size="11" fill="#475569">{_esc(lbl)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart-svg" role="img" aria-label="Jembatan Pendapatan ke Arus Kas">{"".join(bars)}</svg>'


def _svg_bar_emiten(emiten: dict[str, Any]) -> str:
    """Grafik perbandingan 5 rasio kunci: Perusahaan Anda vs Median Emiten Tbk."""
    med = emiten.get("median") or {}
    usr = emiten.get("pengguna") or {}
    if not usr:
        return ""
    pairs = [
        ("Margin kotor (%)", usr.get("gm"), med.get("gm")),
        ("Margin bersih (%)", usr.get("nm"), med.get("nm")),
        ("ROE (%)", usr.get("roe"), med.get("roe")),
        ("ROA (%)", usr.get("roa"), med.get("roa")),
        ("Pertumbuhan (%)", usr.get("pertumbuhan"), med.get("pertumbuhan")),
    ]
    pairs = [(l, u, m) for l, u, m in pairs if u is not None and m is not None]
    if not pairs:
        return ""
    w, h = 680, 220
    pad_l, pad_r, pad_t, pad_b = 35, 20, 28, 48
    plot_w, plot_h = w - pad_l - pad_r, h - pad_t - pad_b
    max_v = max([max(abs(u), abs(m)) for _, u, m in pairs] + [10.0])
    step = plot_w / len(pairs)
    bw = step * 0.28
    base_y = pad_t + plot_h
    els = [
        f'<line x1="{pad_l}" y1="{base_y:.1f}" x2="{w - pad_r}" y2="{base_y:.1f}" stroke="#cbd5e1"/>',
        '<rect x="440" y="6" width="10" height="10" rx="2" fill="#1d4ed8"/><text x="455" y="15" font-size="11" fill="#334155">Perusahaan Anda</text>',
        '<rect x="560" y="6" width="10" height="10" rx="2" fill="#94a3b8"/><text x="575" y="15" font-size="11" fill="#334155">Median Emiten</text>',
    ]
    for i, (lbl, u, m) in enumerate(pairs):
        cx = pad_l + step * i + step / 2
        hu = max(2.0, min(plot_h, abs(u) / max_v * plot_h))
        hm = max(2.0, min(plot_h, abs(m) / max_v * plot_h))
        els.append(f'<rect x="{cx - bw - 2:.1f}" y="{base_y - hu:.1f}" width="{bw:.1f}" height="{hu:.1f}" rx="3" fill="#1d4ed8"/>')
        els.append(f'<text x="{cx - bw / 2 - 2:.1f}" y="{base_y - hu - 4:.1f}" text-anchor="middle" font-size="10" font-weight="600" fill="#1e293b">{_idn(u, 1)}%</text>')
        els.append(f'<rect x="{cx + 2:.1f}" y="{base_y - hm:.1f}" width="{bw:.1f}" height="{hm:.1f}" rx="3" fill="#94a3b8"/>')
        els.append(f'<text x="{cx + bw / 2 + 2:.1f}" y="{base_y - hm - 4:.1f}" text-anchor="middle" font-size="10" fill="#475569">{_idn(m, 1)}%</text>')
        els.append(f'<text x="{cx:.1f}" y="{h - 14}" text-anchor="middle" font-size="11" fill="#334155">{_esc(lbl)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart-svg" role="img" aria-label="Perbandingan Perusahaan vs Median Emiten">{"".join(els)}</svg>'


def _svg_uji_kas(uji: dict[str, Any], samaran: bool) -> str:
    """Grafik batang horizontal kas akhir tiap skenario terhadap batas kas minimum."""
    skens = uji.get("skenario") or []
    if not skens:
        return ""
    kas_min = uji.get("kas_minimum") or 0.0
    vals = [s.get("kas_akhir", 0.0) for s in skens] + [kas_min]
    max_v = max([v for v in vals] + [1.0])
    min_v = min([v for v in vals] + [0.0])
    span = max(max_v - min_v, 1.0)
    w, row_h = 680, 32
    pad_l, pad_r, pad_t, pad_b = 260, 95, 22, 24
    h = pad_t + pad_b + row_h * len(skens)
    plot_w = w - pad_l - pad_r
    x_zero = pad_l + (-min_v / span) * plot_w
    x_min = pad_l + ((kas_min - min_v) / span) * plot_w
    els = [
        f'<line x1="{x_zero:.1f}" y1="{pad_t}" x2="{x_zero:.1f}" y2="{h - pad_b}" stroke="#cbd5e1"/>',
        f'<line x1="{x_min:.1f}" y1="{pad_t - 4}" x2="{x_min:.1f}" y2="{h - pad_b}" stroke="#b91c1c" stroke-dasharray="4,3"/>',
        f'<text x="{x_min:.1f}" y="14" text-anchor="middle" font-size="10" fill="#b91c1c">Kas min: {_esc(fmt_uang(kas_min, samaran))}</text>',
    ]
    for i, s in enumerate(skens):
        y = pad_t + i * row_h + 6
        v = s.get("kas_akhir", 0.0)
        x_val = pad_l + ((v - min_v) / span) * plot_w
        bx = min(x_zero, x_val)
        bw = max(2.0, abs(x_val - x_zero))
        st = (s.get("status") or "").lower()
        color = "#b91c1c" if st == "kritis" else ("#d97706" if st == "waspada" else "#0f766e")
        nama = s.get("nama", "")[:34]
        els.append(f'<text x="{pad_l - 8}" y="{y + 13}" text-anchor="end" font-size="11" fill="#334155">{_esc(nama)}</text>')
        els.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="18" rx="3" fill="{color}"/>')
        els.append(f'<text x="{max(x_val, x_zero) + 6:.1f}" y="{y + 13}" font-size="11" font-weight="600" fill="#1e293b">{_esc(fmt_uang(v, samaran))}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart-svg" role="img" aria-label="Ketahanan Kas per Skenario">{"".join(els)}</svg>'


def susun_markdown(bahan: dict[str, Any], ringkas: dict[str, Any], judul: str, catatan: str) -> str:
    sam = ringkas["samaran"]
    L = [
        f"# {judul}: {ringkas['perusahaan']} ({ringkas['periode']})",
        "",
        catatan or ringkas["putusan_teks"] or "Ringkasan terpadu kinerja keuangan, risiko operasional, dan proyeksi manajemen.",
        "",
        "## 1. Ringkasan Kinerja Keuangan",
        "",
        f"| Pos Utama | {ringkas['periode']} | {ringkas['periode_lalu']} | Perubahan |",
        "|---|---:|---:|---:|",
    ]
    for p in ringkas["pos"]:
        chg = f"{'+' if p['chg_pct'] > 0 else ''}{_idn(p['chg_pct'], 1)}%" if p["chg_pct"] is not None else "-"
        L.append(f"| {p['label']} | {fmt_uang(p['kini'], sam)} | {fmt_uang(p['lalu'], sam)} | {chg} |")

    if bahan.get("gejala"):
        tem = bahan["gejala"].get("temuan", [])
        L += ["", "## 2. Temuan Red Flag Operasional", ""]
        for t in tem[:5]:
            L.append(f"- **{t['judul']}** ({t['tingkat']}): {t['ringkas']} | *Pertanyaan:* {t['pertanyaan_minggu_ini'][0]}")

    if bahan.get("emiten"):
        em = bahan["emiten"]
        pos = em.get("posisi") or {}
        L += ["", f"## 3. Posisi vs Median Emiten IDX ({', '.join(em.get('emiten', {}).keys())})", ""]
        for k, st in pos.items():
            if st:
                L.append(f"- `{k}`: **{st}** (Perusahaan: {_idn((em.get('pengguna') or {}).get(k), 2)} vs Median: {_idn((em.get('median') or {}).get(k), 2)})")

    if bahan.get("ekonomi"):
        ek = bahan["ekonomi"]
        L += ["", f"## 4. Forecast Risiko Ekonomi Daerah ({ek.get('daerah', '-')})", ""]
        for d in ek.get("dimensi", []):
            L.append(f"- **{d['nama']}**: {d['status']} ({_idn(d['nilai'], 1)}{d['unit'] if d['nilai'] is not None else ' PERLU DATA'})")

    if bahan.get("sdm"):
        sdm = bahan["sdm"]
        L += ["", "## 5. Efisiensi SDM & KPI Budgeting Departemen", ""]
        for m in sdm.get("produktivitas", {}).get("metrik", []):
            L.append(f"- **{m['label']}**: {fmt_uang(m['kini'], sam)}/orang")
        for r in sdm.get("rekomendasi_departemen", []):
            L.append(f"- **{r['departemen']}**: {r['rekomendasi_budget']}")

    if bahan.get("uji_kas"):
        uk = bahan["uji_kas"]
        L += ["", f"## 6. Uji Ketahanan Kas ({uk.get('horizon', 3)} bulan)", ""]
        for s in uk.get("skenario", []):
            L.append(f"- **{s['nama']}**: kas akhir {fmt_uang(s['kas_akhir'], sam)} ({s['status'].upper()})")

    if bahan.get("kesiapan"):
        ks = bahan["kesiapan"]
        L += ["", "## 7. Kesiapan Data & Sistem", "", f"Level **{ks['level']} dari 4** ({ks['nama_level']}) - skor {_idn(ks['skor_rata_rata'], 2)}."]

    L += ["", "---", "", "Disusun dengan TQ Board Insight | totalquality.co.id"]
    return "\n".join(L)


def susun_html(bahan: dict[str, Any], ringkas: dict[str, Any], judul: str, catatan: str) -> str:
    sam = ringkas["samaran"]
    label_data = "DATA DISAMARKAN" if sam else ("DATA FIKTIF | PELATIHAN" if ringkas["fiktif"] else "RAHASIA | INTERNAL DIREKSI")
    pos_map = {p["kunci"]: p for p in ringkas["pos"]}

    def kpi_card(lbl: str, p_item: dict[str, Any] | None) -> str:
        if not p_item:
            return ""
        chg = p_item.get("chg_pct")
        cmp_txt = f"{'+' if chg > 0 else ''}{_idn(chg, 1)}% vs {ringkas['periode_lalu']}" if chg is not None else ringkas["periode_lalu"]
        return (
            f'<div class="card"><div class="lbl">{_esc(lbl)}</div>'
            f'<div class="val">{_esc(fmt_uang(p_item["kini"], sam))}</div>'
            f'<div class="sub">{_esc(cmp_txt)}</div></div>'
        )

    cards_html = "".join([
        kpi_card("Pendapatan", pos_map.get("pendapatan")),
        kpi_card("Laba Bersih", pos_map.get("laba_bersih")),
        kpi_card("Arus Kas Operasi", pos_map.get("arus_kas_operasi")),
    ])
    if bahan.get("sdm"):
        m_pend = next((m for m in bahan["sdm"].get("produktivitas", {}).get("metrik", []) if m["kunci"] == "pendapatan"), None)
        if m_pend:
            cards_html += (
                f'<div class="card"><div class="lbl">Pendapatan / Karyawan</div>'
                f'<div class="val">{_esc(fmt_uang(m_pend["kini"], sam))}</div>'
                f'<div class="sub">{int(round(bahan["sdm"]["sdm"]["total_kini"]))} karyawan</div></div>'
            )

    sec_html: list[str] = []

    # 1. Ringkasan Kinerja & Waterfall
    rows_pos = "".join(
        f'<tr><td>{_esc(p["label"])}</td><td class="num">{_esc(fmt_uang(p["kini"], sam))}</td>'
        f'<td class="num">{_esc(fmt_uang(p["lalu"], sam))}</td>'
        f'<td class="num">{("+" if p["chg_pct"] > 0 else "") + _idn(p["chg_pct"], 1) + "%" if p["chg_pct"] is not None else "-"}</td></tr>'
        for p in ringkas["pos"]
    )
    sec_html.append(
        '<section class="panel"><h2>1. Kinerja Keuangan &amp; Jembatan Arus Kas</h2>'
        f'{_svg_waterfall_kas(ringkas["pos"], sam)}'
        f'<table><thead><tr><th>Pos Utama</th><th class="num">{_esc(ringkas["periode"])}</th>'
        f'<th class="num">{_esc(ringkas["periode_lalu"])}</th><th class="num">Perubahan</th></tr></thead>'
        f'<tbody>{rows_pos}</tbody></table></section>'
    )

    # 2. Red Flag Operasional
    if bahan.get("gejala"):
        tem = bahan["gejala"].get("temuan", [])
        items_g = "".join(
            f'<div class="finding">{_status_badge(t["tingkat"].upper())} <strong>{_esc(t["judul"])}</strong>'
            f'<p>{_esc(t["ringkas"])}</p>'
            f'<div class="muted"><strong>Pertanyaan tim:</strong> {_esc(t["pertanyaan_minggu_ini"][0])}</div></div>'
            for t in tem
        ) or "<p>Tidak ada red flag kritis yang terdeteksi dari rasio keuangan.</p>"
        sec_html.append(f'<section class="panel"><h2>2. Red Flag Operasional</h2>{items_g}</section>')

    # 3. Benchmark Emiten Tbk
    if bahan.get("emiten"):
        em = bahan["emiten"]
        em_names = ", ".join(em.get("emiten", {}).keys())
        usr = em.get("pengguna") or {}
        med = em.get("median") or {}
        pos = em.get("posisi") or {}
        label_m = {
            "pertumbuhan": "Pertumbuhan pendapatan (%)", "gm": "Margin laba kotor (%)", "om": "Margin laba usaha (%)",
            "ebitda_m": "Margin EBITDA (%)", "nm": "Margin laba bersih (%)", "roe": "ROE (%)", "roa": "ROA (%)",
            "cr": "Rasio lancar (x)", "qr": "Rasio cepat (x)", "der": "DER (x)", "nde": "Utang bersih / EBITDA (x)",
            "dso": "Hari piutang (hari)", "cfo_ni": "Kas operasi / laba bersih (x)", "fcf_m": "Margin FCF (%)",
        }
        rows_em = "".join(
            f'<tr><td>{_esc(lab)}</td><td class="num">{_idn(med.get(k), 2)}</td>'
            f'<td class="num">{_idn(usr.get(k), 2)}</td><td>{_status_badge(pos[k]) if pos.get(k) else "-"}</td></tr>'
            for k, lab in label_m.items()
            if med.get(k) is not None or usr.get(k) is not None
        )
        sec_html.append(
            f'<section class="panel"><h2>3. Posisi Perusahaan vs Median Emiten IDX ({_esc(em_names)})</h2>'
            f'{_svg_bar_emiten(em)}'
            '<table><thead><tr><th>Metrik</th><th class="num">Median Emiten</th><th class="num">Perusahaan Anda</th><th>Posisi</th></tr></thead>'
            f'<tbody>{rows_em}</tbody></table>'
            '<p class="note">Sumber emiten: TradingView (tidak resmi). Pembanding konteks skala perusahaan terbuka.</p></section>'
        )

    # 4. Forecast Risiko Ekonomi Daerah
    if bahan.get("ekonomi"):
        ek = bahan["ekonomi"]
        rows_ek = "".join(
            f'<tr><td>{_esc(d["nama"])}</td><td class="num">{_idn(d["nilai"], 1) + d["unit"] if d["nilai"] is not None else "PERLU DATA"}</td>'
            f'<td>{_status_badge(d["status"])}</td><td>{_esc(d["sumber"])}</td></tr>'
            for d in ek.get("dimensi", [])
        )
        rows_pap = "".join(
            f'<tr><td>{_esc(p["saluran"])}</td><td>{_status_badge(p["paparan"])}</td><td>{_esc(p["penjelasan"])}</td></tr>'
            for p in ek.get("paparan", [])
        )
        sec_html.append(
            f'<section class="panel"><h2>4. Forecast Risiko Ekonomi Daerah ({_esc(ek.get("daerah", "-"))})</h2>'
            '<table><thead><tr><th>Dimensi Makro/Daerah</th><th class="num">Nilai</th><th>Status</th><th>Sumber</th></tr></thead>'
            f'<tbody>{rows_ek}</tbody></table>'
            '<h3>Dampak ke Struktur Keuangan Perusahaan</h3>'
            '<table><thead><tr><th>Saluran Transmisi</th><th>Paparan</th><th>Penjelasan Operasional</th></tr></thead>'
            f'<tbody>{rows_pap}</tbody></table></section>'
        )

    # 5. Efisiensi SDM & KPI Budgeting
    if bahan.get("sdm"):
        sdm = bahan["sdm"]
        rows_m = "".join(
            f'<tr><td>{_esc(m["label"])}</td><td class="num">{_esc(fmt_uang(m["kini"], sam))}</td>'
            f'<td class="num">{_esc(fmt_uang(m["lalu"], sam)) if m["lalu"] is not None else "-"}</td></tr>'
            for m in sdm.get("produktivitas", {}).get("metrik", [])
        )
        rows_dep = "".join(
            f'<tr><td><strong>{_esc(r["departemen"])}</strong></td>'
            f'<td class="num">{int(round(r["karyawan_kini"])) if r["karyawan_kini"] is not None else "PERLU DATA"}</td>'
            f'<td>{_esc("; ".join(r["kpi_prioritas"]))}</td>'
            f'<td>{_esc(r["rekomendasi_budget"])}</td></tr>'
            for r in sdm.get("rekomendasi_departemen", [])
        )
        sec_html.append(
            '<section class="panel"><h2>5. Produktivitas Rp per Karyawan &amp; KPI Budgeting Departemen</h2>'
            '<table><thead><tr><th>Indikator per Karyawan</th><th class="num">Periode Kini</th><th class="num">Pembanding</th></tr></thead>'
            f'<tbody>{rows_m}</tbody></table>'
            '<h3>Rekomendasi KPI &amp; Arah Anggaran per Departemen</h3>'
            '<table><thead><tr><th>Departemen</th><th class="num">Karyawan</th><th>KPI Prioritas</th><th>Rekomendasi Budgeting</th></tr></thead>'
            f'<tbody>{rows_dep}</tbody></table></section>'
        )

    # 6. Uji Ketahanan Kas
    if bahan.get("uji_kas"):
        uk = bahan["uji_kas"]
        rows_uk = "".join(
            f'<tr><td>{_esc(s["nama"])}</td><td class="num">{_esc(fmt_uang(s["kas_terendah"], sam))}</td>'
            f'<td class="num">{_esc(fmt_uang(s["kas_akhir"], sam))}</td>'
            f'<td class="num">{_idn(s["dscr"], 2) + "x" if s.get("dscr") is not None else "-"}</td>'
            f'<td>{_status_badge(s["status"].upper())}</td></tr>'
            for s in uk.get("skenario", [])
        )
        sec_html.append(
            f'<section class="panel"><h2>6. Uji Ketahanan Kas (Horizon {uk.get("horizon", 3)} Bulan)</h2>'
            f'{_svg_uji_kas(uk, sam)}'
            '<table><thead><tr><th>Skenario</th><th class="num">Kas Terendah</th><th class="num">Kas Akhir</th><th class="num">DSCR</th><th>Status</th></tr></thead>'
            f'<tbody>{rows_uk}</tbody></table></section>'
        )

    # 7. Kesiapan Data
    if bahan.get("kesiapan"):
        ks = bahan["kesiapan"]
        sec_html.append(
            f'<section class="panel"><h2>7. Kesiapan Data &amp; Sistem</h2>'
            f'<p><strong>Level {ks["level"]} dari 4 ({_esc(ks["nama_level"])})</strong> - skor rata-rata {_idn(ks["skor_rata_rata"], 2)}.</p>'
            f'<p>{_esc(ks["deskripsi_level"])}</p></section>'
        )

    kelengkapan_pills = "".join(
        f'<span class="pill {"on" if bahan.get(k) else "off"}">{_esc(lbl)}: {"Tersedia" if bahan.get(k) else "Tidak disertakan"}</span>'
        for k, lbl in (
            ("keuangan", "Laporan Keuangan"), ("gejala", "Red Flag"), ("emiten", "Benchmark Tbk"),
            ("ekonomi", "Ekonomi Daerah"), ("sdm", "SDM & Budgeting"), ("uji_kas", "Uji Ketahanan Kas"),
            ("kesiapan", "Kesiapan Data"),
        )
    )

    putusan_box = _esc(catatan or ringkas["putusan_teks"] or "Paket laporan kombinasi ini merangkum seluruh modul analisis yang dijalankan untuk bahan keputusan direksi.")
    return f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(judul)} - {_esc(ringkas['perusahaan'])}</title>
<style>
  :root {{ --bg:#f8fafc; --card:#fff; --ink:#0f172a; --sub:#475569; --line:#e2e8f0; --brand:#0f766e; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg); color:var(--ink); line-height:1.5; }}
  .wrap {{ max-width:1040px; margin:0 auto; padding:24px 18px 48px; }}
  header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; border-bottom:2px solid var(--brand); padding-bottom:14px; margin-bottom:18px; }}
  h1 {{ margin:4px 0 0; font-size:22px; }}
  .tag {{ display:inline-block; font-size:11px; font-weight:700; letter-spacing:.04em; background:#0f172a; color:#fff; padding:2px 8px; border-radius:4px; }}
  .meta {{ font-size:13px; color:var(--sub); margin-top:4px; }}
  .btn {{ background:var(--brand); color:#fff; border:0; padding:8px 14px; border-radius:8px; cursor:pointer; font-weight:600; font-size:13px; }}
  .summary {{ background:#ecfdf5; border:1px solid #a7f3d0; padding:14px 16px; border-radius:10px; margin-bottom:16px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin-bottom:18px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
  .card .lbl {{ font-size:12px; color:var(--sub); }}
  .card .val {{ font-size:21px; font-weight:700; margin:4px 0; }}
  .card .sub {{ font-size:12px; color:var(--sub); }}
  .panel {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px; margin-bottom:16px; page-break-inside:avoid; }}
  .panel h2 {{ margin:0 0 12px; font-size:17px; color:#0f172a; border-left:4px solid var(--brand); padding-left:10px; }}
  .panel h3 {{ margin:14px 0 8px; font-size:14px; color:var(--sub); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin-top:10px; }}
  th, td {{ padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
  th {{ background:#f1f5f9; font-weight:600; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; white-space:nowrap; }}
  .st-green {{ background:#dcfce7; color:#166534; }}
  .st-amber {{ background:#fef3c7; color:#92400e; }}
  .st-red {{ background:#fee2e2; color:#991b1b; }}
  .st-blue {{ background:#dbeafe; color:#1e40af; }}
  .finding {{ padding:10px 12px; border:1px solid var(--line); border-radius:8px; margin-bottom:8px; }}
  .finding p {{ margin:6px 0 4px; font-size:13px; }}
  .muted, .note {{ font-size:12px; color:var(--sub); }}
  .chart-svg {{ width:100%; max-height:240px; margin:6px 0 10px; display:block; }}
  .pills {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:16px; }}
  .pill {{ font-size:11px; padding:3px 9px; border-radius:999px; border:1px solid var(--line); }}
  .pill.on {{ background:#f0fdfa; border-color:#5eead4; color:#115e59; }}
  .pill.off {{ background:#f1f5f9; color:#64748b; }}
  footer {{ text-align:center; font-size:12px; color:var(--sub); margin-top:24px; }}
  @media print {{ .no-print {{ display:none; }} body {{ background:#fff; }} .wrap {{ padding:0; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <span class="tag">{_esc(label_data)}</span>
      <h1>{_esc(judul)}: {_esc(ringkas['perusahaan'])}</h1>
      <div class="meta">Periode: {_esc(ringkas['periode'])} | Disusun: {_dt.date.today().strftime('%d-%m-%Y')}</div>
    </div>
    <button class="btn no-print" onclick="window.print()">Cetak / Simpan PDF</button>
  </header>
  <div class="pills">{kelengkapan_pills}</div>
  <div class="summary"><strong>Putusan &amp; Ringkasan Eksekutif:</strong> {putusan_box}</div>
  <div class="cards">{cards_html}</div>
  {"".join(sec_html)}
  <footer>Alat bantu analisis direksi, bukan nasihat investasi atau opini audit. | Disusun dengan TQ Board Insight | totalquality.co.id</footer>
</div>
</body>
</html>"""


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Susun report kombinasi HTML/PDF + Markdown lintas-skill")
    ap.add_argument("--rasio", type=Path, help="rasio.json (hitung_rasio.py)")
    ap.add_argument("--laporan", type=Path, help="laporan.json (susun_laporan.py)")
    ap.add_argument("--gejala", type=Path, help="gejala.json (deteksi_gejala.py)")
    ap.add_argument("--kesiapan", type=Path, help="kesiapan.json (skor_kesiapan.py)")
    ap.add_argument("--emiten", type=Path, help="pembanding.json (ringkas_emiten.py --out-json)")
    ap.add_argument("--ekonomi", type=Path, help="risiko-ekonomi.json (analisa_risiko_ekonomi.py --out-json)")
    ap.add_argument("--sdm", type=Path, help="sdm-budget.json (analisa_sdm_budget.py --out-json)")
    ap.add_argument("--uji-kas", type=Path, help="uji-kas.json (uji_ketahanan_kas.py --out-json)")
    ap.add_argument("--judul", default="Paket Laporan Kombinasi Direksi", help="Judul laporan")
    ap.add_argument("--catatan", default="", help="Ringkasan eksekutif kustom")
    ap.add_argument("--out", type=Path, required=True, help="Berkas HTML keluaran")
    ap.add_argument("--out-md", type=Path, help="Opsional berkas Markdown keluaran")
    ap.add_argument("--diam", action="store_true")
    a = ap.parse_args(argv)

    if not a.rasio and not a.laporan:
        ap.error("Berikan minimal --rasio atau --laporan sebagai basis laporan keuangan.")

    try:
        rasio = _muat_json(a.rasio)
        laporan = _muat_json(a.laporan)
        bahan = {
            "keuangan": rasio or laporan,
            "gejala": _muat_json(a.gejala),
            "kesiapan": _muat_json(a.kesiapan),
            "emiten": _muat_json(a.emiten),
            "ekonomi": _muat_json(a.ekonomi),
            "sdm": _muat_json(a.sdm),
            "uji_kas": _muat_json(a.uji_kas),
        }
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"GAGAL: {e}", file=sys.stderr)
        return 1

    ringkas = ekstrak_ringkasan_keuangan(rasio, laporan)
    html_txt = susun_html(bahan, ringkas, a.judul, a.catatan)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(html_txt, encoding="utf-8")

    if a.out_md:
        a.out_md.parent.mkdir(parents=True, exist_ok=True)
        a.out_md.write_text(susun_markdown(bahan, ringkas, a.judul, a.catatan), encoding="utf-8")

    if not a.diam:
        print(f"Report kombinasi ditulis ke {a.out}" + (f" dan {a.out_md}" if a.out_md else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
