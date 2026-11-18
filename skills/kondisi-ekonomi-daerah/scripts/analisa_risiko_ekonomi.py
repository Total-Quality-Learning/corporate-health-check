#!/usr/bin/env python3
"""Analisa risiko kondisi ekonomi daerah & forecast dampaknya ke keuangan perusahaan.

Pemakaian:
    python scripts/analisa_risiko_ekonomi.py ekonomi.json --out-md risiko-ekonomi.md --out-json risiko-ekonomi.json
    python scripts/analisa_risiko_ekonomi.py ekonomi.json --rasio rasio.json --out-skenario skenario-makro.json --out-md risiko-ekonomi.md
    python scripts/analisa_risiko_ekonomi.py ekonomi.json --rasio laporan.json --gaya checklist

- Input  : ekonomi.json (dari ambil_makro.py) atau CSV template-ekonomi-daerah.csv,
           opsional --rasio (menerima rasio.json tahunan maupun laporan.json bulanan).
- Output : laporan risiko makro-daerah (MD + JSON) dan opsional skenario-makro.json
           yang langsung kompatibel dengan `uji_ketahanan_kas.py --skenario`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ambil_makro import baca_input_daerah, parse_angka  # noqa: E402


def _idn(x: float | None, d: int = 1) -> str:
    if x is None:
        return "-"
    s = f"{abs(x):,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return f"-{s}" if x < 0 else s


def _ambil_indikator(ek: dict[str, Any], kunci_daerah: str, kunci_nas: str | None) -> tuple[float | None, float | None, str, bool]:
    """Ambil (kini, lalu, sumber, apakah_proksi_nasional) dengan prioritas data daerah."""
    d_map = ek.get("indikator_daerah") or {}
    d_entry = d_map.get(kunci_daerah)
    if isinstance(d_entry, dict) and d_entry.get("kini") is not None:
        return parse_angka(d_entry["kini"]), parse_angka(d_entry.get("lalu")), d_entry.get("sumber") or "Data daerah", False

    if kunci_nas:
        n_entry = (ek.get("nasional") or {}).get(kunci_nas) or {}
        kini_obj = n_entry.get("kini")
        lalu_obj = n_entry.get("lalu")
        if isinstance(kini_obj, dict) and kini_obj.get("nilai") is not None:
            th_k = kini_obj.get("tahun", "")
            vk = float(kini_obj["nilai"])
            vl = float(lalu_obj["nilai"]) if isinstance(lalu_obj, dict) and lalu_obj.get("nilai") is not None else None
            return vk, vl, f"Proksi nasional World Bank ({th_k})", True

    return None, None, "PERLU DATA", False


def nilai_dimensi(ek: dict[str, Any]) -> list[dict[str, Any]]:
    """Hitung status 5 dimensi makro-daerah sesuai references/ambang-risiko.md."""
    dimensi: list[dict[str, Any]] = []

    # 1. Permintaan & daya beli (PDRB / PDB)
    pdrb, pdrb_lalu, pdrb_src, pdrb_proksi = _ambil_indikator(ek, "pdrb_pct", "pertumbuhan_pdb_pct")
    if pdrb is None:
        st_p = "Perlu data"
    elif pdrb >= 5.0:
        st_p = "Aman"
    elif pdrb >= 3.0:
        st_p = "Perlu perhatian"
    else:
        st_p = "Kritis"
    dimensi.append({
        "kunci": "permintaan", "nama": "Permintaan & daya beli daerah (PDRB)",
        "nilai": pdrb, "lalu": pdrb_lalu, "unit": "%", "status": st_p,
        "sumber": pdrb_src, "proksi": pdrb_proksi,
        "ambang": "Aman >= 5,0% | Perlu perhatian 3,0%-4,9% | Kritis < 3,0%",
    })

    # 2. Tekanan harga & bahan baku (Inflasi)
    inf, inf_lalu, inf_src, inf_proksi = _ambil_indikator(ek, "inflasi_daerah_pct", "inflasi_nasional_pct")
    if inf is None:
        st_i = "Perlu data"
    elif inf <= 3.5:
        st_i = "Aman"
    elif inf <= 5.0:
        st_i = "Perlu perhatian"
    else:
        st_i = "Kritis"
    dimensi.append({
        "kunci": "inflasi", "nama": "Tekanan harga & bahan baku (Inflasi)",
        "nilai": inf, "lalu": inf_lalu, "unit": "%", "status": st_i,
        "sumber": inf_src, "proksi": inf_proksi,
        "ambang": "Aman <= 3,5% | Perlu perhatian 3,6%-5,0% | Kritis > 5,0%",
    })

    # 3. Tekanan upah daerah (UMP / UMK)
    ump, ump_lalu, ump_src, _ = _ambil_indikator(ek, "kenaikan_ump_pct", None)
    if ump is None:
        st_u = "Perlu data"
    elif ump <= 5.0:
        st_u = "Aman"
    elif ump <= 8.5:
        st_u = "Perlu perhatian"
    else:
        st_u = "Kritis"
    dimensi.append({
        "kunci": "upah", "nama": "Tekanan biaya tenaga kerja (UMP/UMK)",
        "nilai": ump, "lalu": ump_lalu, "unit": "%", "status": st_u,
        "sumber": ump_src, "proksi": False,
        "ambang": "Aman <= 5,0% | Perlu perhatian 5,1%-8,5% | Kritis > 8,5%",
    })

    # 4. Biaya pendanaan & suku bunga
    bunga, bunga_lalu, bunga_src, bunga_proksi = _ambil_indikator(ek, "suku_bunga_pct", "suku_bunga_pinjaman_pct")
    delta_b = (bunga - bunga_lalu) if (bunga is not None and bunga_lalu is not None) else 0.0
    if bunga is None:
        st_b = "Perlu data"
    elif bunga > 10.5 or delta_b >= 1.5:
        st_b = "Kritis"
    elif bunga > 8.5 or delta_b >= 0.5:
        st_b = "Perlu perhatian"
    else:
        st_b = "Aman"
    dimensi.append({
        "kunci": "bunga", "nama": "Biaya pendanaan & suku bunga",
        "nilai": bunga, "lalu": bunga_lalu, "unit": "%", "status": st_b,
        "sumber": bunga_src, "proksi": bunga_proksi,
        "ambang": "Aman <= 8,5% (naik < 0,5 poin) | Perlu perhatian > 8,5%-10,5% | Kritis > 10,5%",
    })

    # 5. Nilai tukar & rantai pasok impor
    kurs, kurs_lalu, kurs_src, kurs_proksi = _ambil_indikator(ek, "kurs_usd", "kurs_usd")
    dep = ((kurs / kurs_lalu) - 1.0) * 100.0 if (kurs is not None and kurs_lalu and kurs_lalu > 0) else None
    if dep is None:
        st_k = "Perlu data"
    elif dep <= 3.0:
        st_k = "Aman"
    elif dep <= 7.0:
        st_k = "Perlu perhatian"
    else:
        st_k = "Kritis"
    dimensi.append({
        "kunci": "kurs", "nama": "Pelemahan nilai tukar IDR/USD YoY",
        "nilai": dep, "lalu": None, "unit": "%", "status": st_k,
        "sumber": kurs_src + (f" (IDR {_idn(kurs_lalu, 0)} -> {_idn(kurs, 0)})" if kurs and kurs_lalu else ""),
        "proksi": kurs_proksi,
        "ambang": "Aman <= 3,0% | Perlu perhatian 3,1%-7,0% | Kritis > 7,0%",
    })

    return dimensi


def baca_profil_keuangan(path: Path) -> dict[str, Any]:
    """Ekstrak metrik kerentanan dari rasio.json (tahunan) atau laporan.json (bulanan)."""
    r = json.loads(path.read_text(encoding="utf-8-sig"))
    if "kpi" in r and "rasio" not in r:
        pid = "ytd" if "ytd" in r.get("kpi", {}) else "month"
        kmap = {row["key"]: row.get("v") for row in r.get("kpi", {}).get(pid, {}).get("yoy", [])}
        # Ambil rasio tambahan dari lampiran bila perlu
        def _ang(s):
            if not s or s == "-":
                return None
            t = s.strip().replace("%", "").replace("x", "").replace("hari", "").strip()
            neg = t.startswith("(") and t.endswith(")")
            t = t.strip("()").replace(".", "").replace(",", ".")
            try:
                v = float(t)
                return -v if neg else v
            except ValueError:
                return None

        lamp = {
            row["nama"]: _ang(row.get("cur"))
            for grp in r.get("lampiran", {}).get(pid, {}).get("yoy", [])
            for row in grp.get("rows", [])
        }
        cc = kmap.get("cash_conversion")
        return {
            "perusahaan": r.get("meta", {}).get("perusahaan", "Perusahaan Anda"),
            "periode": r.get("periode", {}).get(pid, {}).get("short") or r.get("meta", {}).get("bulan_aktif", ""),
            "rev_growth": kmap.get("rev_growth"),
            "gross_margin": kmap.get("gross_margin"),
            "gross_margin_prev": None,
            "opex_ratio": lamp.get("Rasio beban usaha"),
            "dso": kmap.get("dso"),
            "current_ratio": kmap.get("current_ratio"),
            "der_berbunga": lamp.get("Utang bank ÷ ekuitas"),
            "icr": kmap.get("icr"),
            "net_debt_ebitda": kmap.get("net_debt_ebitda"),
            "cfo_to_ni": (cc / 100.0) if cc is not None else None,
        }

    per = r["meta"]["periode"]
    p = per[-1]
    p_prev = per[-2] if len(per) > 1 else None
    ras = r.get("rasio", {})
    pend = r.get("pos_utama", {}).get("pendapatan", {}).get("nilai", {})
    rev_growth = ((pend[p] / pend[p_prev]) - 1.0) * 100.0 if (p_prev and pend.get(p_prev)) else None

    def val(k: str, pr: str | None = p) -> float | None:
        return ras.get(k, {}).get("nilai", {}).get(pr) if pr else None

    return {
        "perusahaan": r.get("meta", {}).get("perusahaan", "Perusahaan Anda"),
        "periode": p,
        "rev_growth": rev_growth,
        "gross_margin": val("gross_margin"),
        "gross_margin_prev": val("gross_margin", p_prev),
        "opex_ratio": val("opex_ratio"),
        "dso": val("dso"),
        "current_ratio": val("current_ratio"),
        "der_berbunga": val("der_berbunga"),
        "icr": val("interest_coverage"),
        "net_debt_ebitda": val("net_debt_ebitda"),
        "cfo_to_ni": val("cfo_to_ni"),
    }


def petakan_paparan(dimensi: list[dict[str, Any]], fin: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Petakan transmisi risiko makro daerah ke struktur keuangan perusahaan."""
    dmap = {d["kunci"]: d for d in dimensi}
    hasil: list[dict[str, Any]] = []

    if fin is None:
        for d in dimensi:
            hasil.append({
                "saluran": d["nama"],
                "status_makro": d["status"],
                "paparan": "Perlu data",
                "penjelasan": "PERLU DATA keuangan perusahaan (jalankan dengan --rasio rasio.json atau laporan.json).",
            })
        return hasil

    # 1. Permintaan -> Pendapatan & Piutang
    dso = fin.get("dso")
    rg = fin.get("rev_growth")
    rentan_dso = (dso is not None and dso >= 45) or (rg is not None and rg < 0)
    st_m = dmap["permintaan"]["status"]
    pap = "Tinggi" if (rentan_dso and st_m in ("Perlu perhatian", "Kritis")) else ("Sedang" if (rentan_dso or st_m != "Aman") else "Rendah")
    hasil.append({
        "saluran": "Pendapatan & penagihan piutang",
        "status_makro": st_m,
        "paparan": pap,
        "penjelasan": f"DSO saat ini {_idn(dso, 0)} hari; pertumbuhan penjualan {_idn(rg, 1)}%. "
                      + ("Pelambatan daya beli daerah berisiko memperpanjang tunggakan pelanggan." if rentan_dso
                         else "Penagihan masih relatif terjaga, tetap pantau pelanggan utama di daerah terdampak."),
    })

    # 2. Inflasi & Kurs -> Margin Kotor & HPP
    gm = fin.get("gross_margin")
    gm_p = fin.get("gross_margin_prev")
    gm_turun = (gm is not None and gm_p is not None and (gm - gm_p) <= -1.0)
    rentan_gm = (gm is not None and gm < 25.0) or gm_turun
    st_ik = "Kritis" if "Kritis" in (dmap["inflasi"]["status"], dmap["kurs"]["status"]) else (
        "Perlu perhatian" if "Perlu perhatian" in (dmap["inflasi"]["status"], dmap["kurs"]["status"]) else "Aman"
    )
    pap = "Tinggi" if (rentan_gm and st_ik != "Aman") else ("Sedang" if (rentan_gm or st_ik != "Aman") else "Rendah")
    hasil.append({
        "saluran": "Margin kotor & biaya bahan baku",
        "status_makro": st_ik,
        "paparan": pap,
        "penjelasan": f"Margin kotor {_idn(gm, 1)}%" + (f" (periode lalu {_idn(gm_p, 1)}%)" if gm_p is not None else "")
                      + ". " + ("Margin tipis/menurun; kenaikan harga bahan dan kurs sulit langsung dibebankan ke harga jual."
                                if rentan_gm else "Bantalan margin cukup memadai, namun kontrak harga pemasok tetap perlu dikunci."),
    })

    # 3. UMP/UMK -> Beban Usaha & Tenaga Kerja
    opex = fin.get("opex_ratio")
    rentan_opex = opex is not None and opex >= 20.0
    st_u = dmap["upah"]["status"]
    pap = "Tinggi" if (rentan_opex and st_u == "Kritis") else ("Sedang" if (rentan_opex or st_u in ("Perlu perhatian", "Kritis")) else ("Perlu data" if st_u == "Perlu data" and opex is None else "Rendah"))
    hasil.append({
        "saluran": "Beban operasional & upah daerah",
        "status_makro": st_u,
        "paparan": pap,
        "penjelasan": (f"Rasio beban usaha {_idn(opex, 1)}% dari pendapatan. " if opex is not None else "Rasio beban usaha belum terinci. ")
                      + ("Kenaikan UMP/UMK berpotensi langsung menekan laba operasi bila tidak diimbangi produktivitas."
                         if st_u in ("Perlu perhatian", "Kritis") else "Lengkapi data kenaikan UMP/UMK daerah untuk mengukur beban tetap tahun depan." if st_u == "Perlu data" else "Tekanan upah masih moderat."),
    })

    # 4. Suku Bunga -> Beban Bunga & Kovenan
    deb = fin.get("der_berbunga")
    icr = fin.get("icr")
    nde = fin.get("net_debt_ebitda")
    rentan_utang = (deb is not None and deb >= 0.5) or (icr is not None and icr < 3.0) or (nde is not None and nde >= 2.5)
    st_b = dmap["bunga"]["status"]
    pap = "Tinggi" if (rentan_utang and st_b != "Aman") else ("Sedang" if (rentan_utang or st_b != "Aman") else "Rendah")
    hasil.append({
        "saluran": "Beban bunga & kovenan utang",
        "status_makro": st_b,
        "paparan": pap,
        "penjelasan": f"Utang bank/ekuitas {_idn(deb, 2)}x, interest coverage {_idn(icr, 2)}x, utang bersih/EBITDA {_idn(nde, 2)}x. "
                      + ("Sensitivitas terhadap kenaikan suku bunga kredit tinggi." if rentan_utang
                         else "Struktur utang berbunga relatif rendah terhadap kapasitas laba."),
    })

    # 5. Penyangga Kas
    cr = fin.get("current_ratio")
    cfo = fin.get("cfo_to_ni")
    rentan_kas = (cr is not None and cr < 1.5) or (cfo is not None and cfo < 0.75)
    hasil.append({
        "saluran": "Penyangga likuiditas & kas operasi",
        "status_makro": "Perlu perhatian" if any(d["status"] in ("Perlu perhatian", "Kritis") for d in dimensi) else "Aman",
        "paparan": "Tinggi" if rentan_kas else "Rendah",
        "penjelasan": f"Rasio lancar {_idn(cr, 2)}x; arus kas operasi/laba bersih {_idn(cfo, 2)}x. "
                      + ("Bantalan kas tipis; guncangan eksternal perlu segera diuji dengan skill uji-ketahanan-kas."
                         if rentan_kas else "Bantalan likuiditas awal cukup, disarankan tetap disimulasikan pada horizon 6 bulan."),
    })

    return hasil


def bangun_skenario_kas(dimensi: list[dict[str, Any]], daerah: str) -> dict[str, Any]:
    """Turunkan skenario uji ketahanan kas yang kompatibel dengan uji_ketahanan_kas.py."""
    dmap = {d["kunci"]: d for d in dimensi}
    inf = dmap["inflasi"]["nilai"] or 3.5
    dep = max(0.0, dmap["kurs"]["nilai"] or 0.0)
    ump = dmap["upah"]["nilai"]
    pdrb = dmap["permintaan"]["nilai"]
    bunga = dmap["bunga"]["nilai"]

    harga_bahan = round(max(3.0, min(20.0, inf + 0.5 * dep)) * 2) / 2
    biaya_tetap = round(max(2.0, min(15.0, (ump * 0.5) if ump is not None else (inf * 0.5))) * 2) / 2
    turun_jual = -12 if (pdrb is not None and pdrb < 3.0) else (-8 if (pdrb is not None and pdrb < 5.0) else -5)
    molor_dso = 18 if (pdrb is not None and pdrb < 3.0) else (12 if (pdrb is not None and pdrb < 5.0) else 7)
    naik_bunga = 2.0 if (bunga is not None and bunga > 10.5) else (1.5 if (bunga is not None and bunga > 8.5) else 1.0)

    return {
        "horizon_bulan": 6,
        "plafon_tersedia": 0,
        "batas_dscr": 1.25,
        "batas_icr": 2.0,
        "kas_minimum": None,
        "skenario": [
            {"nama": f"Dasar ({daerah})"},
            {
                "nama": f"Tekanan biaya daerah (bahan +{harga_bahan}%, biaya tetap +{biaya_tetap}%)",
                "harga_bahan_pct": harga_bahan,
                "biaya_tetap_pct": biaya_tetap,
            },
            {
                "nama": f"Perlambatan permintaan daerah (jual {turun_jual}%, DSO +{molor_dso} hr)",
                "penjualan_pct": turun_jual,
                "tambah_dso_hari": molor_dso,
            },
            {
                "nama": f"Gabungan berat daerah (jual {turun_jual - 3}%, bahan +{harga_bahan}%, bunga +{naik_bunga} poin)",
                "penjualan_pct": turun_jual - 3,
                "harga_bahan_pct": harga_bahan,
                "biaya_tetap_pct": biaya_tetap,
                "tambah_dso_hari": molor_dso,
                "bunga_poin": naik_bunga,
            },
        ],
    }


def render_md(ek: dict[str, Any], dimensi: list[dict[str, Any]], fin: dict[str, Any] | None, paparan: list[dict[str, Any]], skenario: dict[str, Any], gaya: str) -> str:
    daerah = ek.get("daerah") or "Daerah"
    kritis = [d["nama"] for d in dimensi if d["status"] == "Kritis"]
    waspada = [d["nama"] for d in dimensi if d["status"] == "Perlu perhatian"]
    perlu_data = [d["nama"] for d in dimensi if d["status"] == "Perlu data"]

    ringkas_st = (
        f"Risiko makro {daerah}: {len(kritis)} dimensi kritis, {len(waspada)} perlu perhatian"
        + (f", {len(perlu_data)} perlu data." if perlu_data else ".")
    )
    L = [f"# Forecast Risiko Kondisi Ekonomi Daerah: {daerah}", "", ringkas_st, ""]
    if ek.get("catatan_risiko_daerah"):
        L += [f"> Catatan wilayah: {ek['catatan_risiko_daerah']}", ""]

    L += ["## 1. Kondisi 5 Dimensi Ekonomi Daerah", ""]
    if gaya == "checklist":
        for d in dimensi:
            centang = "x" if d["status"] == "Aman" else " "
            val_txt = f"{_idn(d['nilai'])}{d['unit']}" if d["nilai"] is not None else "PERLU DATA"
            L.append(f"- [{centang}] **{d['nama']}**: {val_txt} ({d['status']}) - {d['sumber']}")
    else:
        L += ["| Dimensi | Kini | Tahun lalu | Status | Sumber & Keterangan |", "|---|---:|---:|---|---|"]
        for d in dimensi:
            k_txt = f"{_idn(d['nilai'])}{d['unit']}" if d["nilai"] is not None else "PERLU DATA"
            l_txt = f"{_idn(d['lalu'])}{d['unit']}" if d["lalu"] is not None else "-"
            L.append(f"| {d['nama']} | {k_txt} | {l_txt} | {d['status']} | {d['sumber']} |")

    L += ["", "## 2. Forecast Dampak ke Keuangan Perusahaan" + (f" ({fin['perusahaan']} - {fin['periode']})" if fin else ""), ""]
    if gaya == "checklist":
        for p in paparan:
            centang = "x" if p["paparan"] == "Rendah" else " "
            L.append(f"- [{centang}] **{p['saluran']}** (Paparan: {p['paparan']}): {p['penjelasan']}")
    else:
        L += ["| Saluran Transmisi | Status Makro | Paparan Perusahaan | Penjelasan Operasional |", "|---|---|---|---|"]
        for p in paparan:
            L.append(f"| {p['saluran']} | {p['status_makro']} | {p['paparan']} | {p['penjelasan']} |")

    if gaya != "ringkas":
        L += ["", "## 3. Skenario Uji Ketahanan Kas yang Disarankan (`skenario-makro.json`)", ""]
        for s in skenario["skenario"]:
            detail = ", ".join(f"{k}={v}" for k, v in s.items() if k != "nama") or "tanpa guncangan"
            L.append(f"- **{s['nama']}**: {detail}")

    L += [
        "",
        "**Catatan cakupan**",
        "",
        "- Indikator daerah yang belum tersedia ditandai **PERLU DATA**; jika memakai proksi nasional World Bank, angka dapat berbeda dari kondisi spesifik provinsi/kota.",
        "- Skenario yang diturunkan merupakan asumsi awal terukur untuk disimulasikan lewat `uji_ketahanan_kas.py` (konfirmasikan terlebih dulu dengan direksi).",
        "",
        "_Alat bantu analisis, bukan proyeksi resmi otoritas atau nasihat investasi._",
        "",
        "Disusun dengan TQ Board Insight | totalquality.co.id",
    ]
    return "\n".join(L)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Analisa risiko ekonomi daerah & dampak ke keuangan")
    ap.add_argument("ekonomi", type=Path, help="File ekonomi.json (dari ambil_makro.py) atau CSV daerah")
    ap.add_argument("--rasio", type=Path, help="Opsional: rasio.json (tahunan) atau laporan.json (bulanan)")
    ap.add_argument("--gaya", choices=["ringkas", "detail", "checklist"])
    ap.add_argument("--preferensi", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-skenario", type=Path, help="Tulis skenario-makro.json untuk uji_ketahanan_kas.py")
    ap.add_argument("--diam", action="store_true")
    a = ap.parse_args(argv)

    pref = json.loads(a.preferensi.read_text(encoding="utf-8-sig")) if a.preferensi and a.preferensi.exists() else {}
    gaya = a.gaya or pref.get("gaya_narasi") or "detail"

    try:
        if not a.ekonomi.exists():
            raise FileNotFoundError(f"Berkas tidak ditemukan: {a.ekonomi}")
        if a.ekonomi.suffix.lower() == ".csv":
            d = baca_input_daerah(a.ekonomi)
            ek = {
                "daerah": d.get("daerah") or "Daerah",
                "indikator_daerah": {k: v for k, v in d.items() if isinstance(v, dict)},
                "catatan_risiko_daerah": d.get("catatan_risiko_daerah") or "",
                "nasional": {},
            }
        else:
            ek = json.loads(a.ekonomi.read_text(encoding="utf-8-sig"))
        fin = baca_profil_keuangan(a.rasio) if a.rasio else None
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"GAGAL: {e}", file=sys.stderr)
        return 1

    dimensi = nilai_dimensi(ek)
    paparan = petakan_paparan(dimensi, fin)
    skenario = bangun_skenario_kas(dimensi, ek.get("daerah") or "Daerah")
    md = render_md(ek, dimensi, fin, paparan, skenario, gaya)

    if a.out_md:
        a.out_md.parent.mkdir(parents=True, exist_ok=True)
        a.out_md.write_text(md, encoding="utf-8")
    if a.out_json:
        a.out_json.parent.mkdir(parents=True, exist_ok=True)
        a.out_json.write_text(json.dumps({
            "daerah": ek.get("daerah"),
            "dimensi": dimensi,
            "keuangan": fin,
            "paparan": paparan,
            "skenario": skenario,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    if a.out_skenario:
        a.out_skenario.parent.mkdir(parents=True, exist_ok=True)
        a.out_skenario.write_text(json.dumps(skenario, indent=2, ensure_ascii=False), encoding="utf-8")

    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
