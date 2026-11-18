#!/usr/bin/env python3
"""Analisa produktivitas Rp per karyawan & rekomendasi KPI + budgeting per departemen.

Pemakaian:
    python scripts/analisa_sdm_budget.py --rasio rasio.json --input sdm-departemen.csv --out-md sdm-budget.md --out-json sdm-budget.json
    python scripts/analisa_sdm_budget.py --rasio laporan.json --karyawan 120 --karyawan-lalu 112 --departemen "Produksi:70,Penjualan:20,Gudang:15,Keuangan & Umum:15"
    python scripts/analisa_sdm_budget.py --rasio rasio.json --karyawan 100 --gaya checklist

Mendukung masukan `rasio.json` (tahunan) maupun `laporan.json` (bulanan).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

KATEGORI_VALID = ("produksi", "penjualan", "gudang_logistik", "keuangan_adm", "umum_it_hr", "manajemen", "umum")


def _idn(x: float | None, d: int = 1) -> str:
    if x is None:
        return "-"
    s = f"{abs(x):,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return f"-{s}" if x < 0 else s


def _parse_angka(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    if not s or s in ("-", "--", "n/a", "na", "null"):
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
    """Parse string berformat 'Rp257,26 M' / '-Rp286 JT' / '257 u' menjadi nilai dalam juta (atau unit samaran)."""
    if not teks or teks == "-":
        return None
    s = teks.strip()
    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.lstrip("+-").strip("()").strip()
    s = re.sub(r"^rp\.?\s*", "", s, flags=re.IGNORECASE)
    faktor = 1.0
    if s.endswith(" T"):
        faktor = 1_000_000.0
        s = s[:-2].strip()
    elif s.endswith(" M"):
        faktor = 1_000.0
        s = s[:-2].strip()
    elif s.endswith(" JT"):
        faktor = 1.0
        s = s[:-3].strip()
    elif s.endswith(" u"):
        faktor = 1.0
        s = s[:-2].strip()
    val = _parse_angka(s)
    if val is None:
        return None
    return (-val if neg else val) * faktor


def _parse_rasio_fmt(teks: str | None) -> float | None:
    if not teks or teks == "-":
        return None
    s = teks.strip().replace("%", "").replace("x", "").replace("hari", "").strip()
    return _parse_angka(s)


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


def fmt_uang_juta(val_juta: float | None, samaran: bool = False) -> str:
    """Format nilai berbasis juta ke satuan eksplisit JT / .000 / M / T (atau unit samaran)."""
    if val_juta is None:
        return "PERLU DATA"
    tanda = "-" if val_juta < 0 else ""
    a = abs(val_juta)
    if samaran:
        return f"{tanda}{_idn(a, 1)} u"
    if a >= 1_000_000:
        return f"{tanda}Rp{_idn(a / 1_000_000, 2)} T"
    if a >= 1_000:
        return f"{tanda}Rp{_idn(a / 1_000, 2)} M"
    if a >= 1:
        return f"{tanda}Rp{_idn(a, 1)} JT"
    ribu = round(a * 1_000)
    return f"{tanda}Rp{_idn(ribu, 0)}.000" if ribu > 0 else "Rp0"


def muat_keuangan(path: Path) -> dict[str, Any]:
    """Ekstrak pos utama & rasio sinyal dari rasio.json atau laporan.json."""
    if not path.exists():
        raise FileNotFoundError(f"Berkas keuangan tidak ditemukan: {path}")
    r = json.loads(path.read_text(encoding="utf-8-sig"))

    # Jalur B: laporan.json (bulanan)
    if "kpi" in r and "rasio" not in r:
        meta = r.get("meta", {})
        samaran = bool(meta.get("samaran"))
        pid = "ytd" if "ytd" in r.get("kpi", {}) else "month"
        lr_rows = {row["nama"]: row for row in r.get("pos", {}).get(pid, {}).get("yoy", {}).get("lr", [])}
        kmap = {row["key"]: row.get("v") for row in r.get("kpi", {}).get(pid, {}).get("yoy", [])}
        lamp = {
            row["nama"]: _parse_rasio_fmt(row.get("cur"))
            for grp in r.get("lampiran", {}).get(pid, {}).get("yoy", [])
            for row in grp.get("rows", [])
        }

        def lr_val(nama: str, field: str = "cur") -> float | None:
            return _parse_uang_fmt((lr_rows.get(nama) or {}).get(field))

        b_jual = abs(lr_val("Beban penjualan & distribusi", "cur") or 0.0)
        b_umum = abs(lr_val("Beban umum & administrasi", "cur") or 0.0)
        b_peny = abs(lr_val("Penyusutan (di luar HPP)", "cur") or 0.0)
        b_jual_l = abs(lr_val("Beban penjualan & distribusi", "comp") or 0.0)
        b_umum_l = abs(lr_val("Beban umum & administrasi", "comp") or 0.0)
        b_peny_l = abs(lr_val("Penyusutan (di luar HPP)", "comp") or 0.0)

        cc = kmap.get("cash_conversion")
        return {
            "perusahaan": meta.get("perusahaan", "Perusahaan"),
            "periode": r.get("periode", {}).get(pid, {}).get("short") or meta.get("bulan_aktif", ""),
            "periode_lalu": "Tahun lalu (YTD)",
            "samaran": samaran,
            "basis": "juta",
            "kini": {
                "pendapatan": lr_val("Pendapatan neto", "cur"),
                "laba_kotor": lr_val("Laba kotor", "cur"),
                "beban_usaha": (b_jual + b_umum + b_peny) if (b_jual or b_umum) else None,
                "laba_bersih": lr_val("Laba bersih", "cur"),
            },
            "lalu": {
                "pendapatan": lr_val("Pendapatan neto", "comp"),
                "laba_kotor": lr_val("Laba kotor", "comp"),
                "beban_usaha": (b_jual_l + b_umum_l + b_peny_l) if (b_jual_l or b_umum_l) else None,
                "laba_bersih": lr_val("Laba bersih", "comp"),
            },
            "sinyal": {
                "rev_growth": kmap.get("rev_growth"),
                "gross_margin": kmap.get("gross_margin"),
                "gross_margin_lalu": None,
                "opex_ratio": lamp.get("Rasio beban usaha"),
                "dso": kmap.get("dso"),
                "dio": kmap.get("dio"),
                "dpo": kmap.get("dpo"),
                "cfo_to_ni": (cc / 100.0) if cc is not None else None,
                "current_ratio": kmap.get("current_ratio"),
            },
        }

    # Jalur A: rasio.json (tahunan/interim)
    meta = r.get("meta", {})
    per = meta.get("periode", [])
    p = per[-1]
    p_lalu = per[-2] if len(per) > 1 else None
    sat = meta.get("satuan", "juta")
    samaran = "samaran" in sat.lower()
    skala = _skala_ke_juta(sat)
    pos = r.get("pos_utama", {})
    ras = r.get("rasio", {})

    def pos_v(k: str, pr: str | None) -> float | None:
        if not pr:
            return None
        v = pos.get(k, {}).get("nilai", {}).get(pr)
        return (float(v) * skala) if v is not None else None

    def ras_v(k: str, pr: str | None = p) -> float | None:
        return ras.get(k, {}).get("nilai", {}).get(pr) if pr else None

    pend_k = pos_v("pendapatan", p)
    pend_l = pos_v("pendapatan", p_lalu)
    rev_growth = ((pend_k / pend_l) - 1.0) * 100.0 if (pend_k and pend_l) else None

    return {
        "perusahaan": meta.get("perusahaan", "Perusahaan"),
        "periode": p,
        "periode_lalu": p_lalu,
        "samaran": samaran,
        "basis": "juta",
        "kini": {
            "pendapatan": pend_k,
            "laba_kotor": pos_v("laba_kotor", p),
            "beban_usaha": pos_v("beban_usaha", p),
            "laba_bersih": pos_v("laba_bersih", p),
        },
        "lalu": {
            "pendapatan": pend_l,
            "laba_kotor": pos_v("laba_kotor", p_lalu),
            "beban_usaha": pos_v("beban_usaha", p_lalu),
            "laba_bersih": pos_v("laba_bersih", p_lalu),
        },
        "sinyal": {
            "rev_growth": rev_growth,
            "gross_margin": ras_v("gross_margin"),
            "gross_margin_lalu": ras_v("gross_margin", p_lalu),
            "opex_ratio": ras_v("opex_ratio"),
            "dso": ras_v("dso"),
            "dio": ras_v("dio"),
            "dpo": ras_v("dpo"),
            "cfo_to_ni": ras_v("cfo_to_ni"),
            "current_ratio": ras_v("current_ratio"),
        },
    }


def tebak_kategori(nama: str) -> str:
    s = nama.lower()
    if any(k in s for k in ("produksi", "pabrik", "manufaktur", "qc", "teknik", "operasi", "engineering")):
        return "produksi"
    if any(k in s for k in ("jual", "sales", "marketing", "pemasaran", "komersial", "bisnis")):
        return "penjualan"
    if any(k in s for k in ("gudang", "logistik", "warehouse", "supply", "pengadaan", "purchasing", "distribusi")):
        return "gudang_logistik"
    if any(k in s for k in ("keuangan", "finance", "akuntansi", "accounting", "pajak", "audit")):
        return "keuangan_adm"
    if any(k in s for k in ("hr", "sdm", "umum", "ga", "it", "legal", "admin")):
        return "umum_it_hr"
    if any(k in s for k in ("direksi", "manajemen", "management", "korporat")):
        return "manajemen"
    return "umum"


def muat_sdm(path: Path | None, karyawan_cli: int | None, karyawan_lalu_cli: int | None, dept_cli: str | None, satuan_input: str) -> dict[str, Any]:
    """Baca struktur departemen dan jumlah karyawan dari CSV/JSON atau argumen CLI."""
    skala = _skala_ke_juta(satuan_input)
    depts: list[dict[str, Any]] = []

    if path:
        if not path.exists():
            raise FileNotFoundError(f"Berkas SDM tidak ditemukan: {path}")
        if path.suffix.lower() == ".json":
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
            for row in raw.get("departemen", raw if isinstance(raw, list) else []):
                nama = str(row.get("departemen") or "").strip()
                if not nama:
                    continue
                kat = (row.get("kategori_fungsi") or "").strip() or tebak_kategori(nama)
                bsdm = _parse_angka(row.get("biaya_sdm_tahunan"))
                angg = _parse_angka(row.get("anggaran_tahun_depan"))
                depts.append({
                    "departemen": nama,
                    "kategori": kat if kat in KATEGORI_VALID else tebak_kategori(nama),
                    "karyawan_kini": _parse_angka(row.get("karyawan_kini")),
                    "karyawan_lalu": _parse_angka(row.get("karyawan_lalu")),
                    "biaya_sdm_juta": (bsdm * skala) if bsdm is not None else None,
                    "anggaran_juta": (angg * skala) if angg is not None else None,
                    "catatan": str(row.get("catatan") or "").strip(),
                })
        else:
            teks = path.read_text(encoding="utf-8-sig")
            delim = ";" if teks.count(";") > teks.count(",") else ","
            rows = list(csv.reader(teks.splitlines(), delimiter=delim))
            if not rows:
                raise ValueError("Berkas CSV SDM kosong.")
            head = [c.strip().lower() for c in rows[0]]
            idx = {k: i for i, k in enumerate(head)}
            if "departemen" not in idx or "karyawan_kini" not in idx:
                raise ValueError("CSV SDM harus memiliki kolom 'departemen' dan 'karyawan_kini'.")
            for r in rows[1:]:
                if not r or idx["departemen"] >= len(r) or not r[idx["departemen"]].strip():
                    continue
                nama = r[idx["departemen"]].strip()
                def col(k: str) -> str:
                    return r[idx[k]].strip() if k in idx and idx[k] < len(r) else ""
                kat = col("kategori_fungsi") or tebak_kategori(nama)
                bsdm = _parse_angka(col("biaya_sdm_tahunan"))
                angg = _parse_angka(col("anggaran_tahun_depan"))
                depts.append({
                    "departemen": nama,
                    "kategori": kat if kat in KATEGORI_VALID else tebak_kategori(nama),
                    "karyawan_kini": _parse_angka(col("karyawan_kini")),
                    "karyawan_lalu": _parse_angka(col("karyawan_lalu")),
                    "biaya_sdm_juta": (bsdm * skala) if bsdm is not None else None,
                    "anggaran_juta": (angg * skala) if angg is not None else None,
                    "catatan": col("catatan"),
                })

    if dept_cli and not depts:
        for bag in dept_cli.split(","):
            if ":" not in bag:
                continue
            nama, jml = bag.split(":", 1)
            nama = nama.strip()
            n_kini = _parse_angka(jml)
            if nama and n_kini is not None:
                depts.append({
                    "departemen": nama,
                    "kategori": tebak_kategori(nama),
                    "karyawan_kini": n_kini,
                    "karyawan_lalu": None,
                    "biaya_sdm_juta": None,
                    "anggaran_juta": None,
                    "catatan": "",
                })

    tot_kini = sum(d["karyawan_kini"] for d in depts if d["karyawan_kini"] is not None) if depts else None
    tot_lalu = (
        sum(d["karyawan_lalu"] for d in depts if d["karyawan_lalu"] is not None)
        if depts and all(d["karyawan_lalu"] is not None for d in depts)
        else None
    )
    if karyawan_cli is not None:
        tot_kini = float(karyawan_cli)
    if karyawan_lalu_cli is not None:
        tot_lalu = float(karyawan_lalu_cli)

    if tot_kini is None or tot_kini <= 0:
        raise ValueError("Jumlah karyawan periode kini wajib > 0 (via --karyawan atau --input).")

    return {
        "total_kini": tot_kini,
        "total_lalu": tot_lalu,
        "departemen": depts,
    }


def hitung_per_karyawan(fin: dict[str, Any], sdm: dict[str, Any]) -> dict[str, Any]:
    """Hitung rasio produktivitas & beban Rp per karyawan secara deterministik."""
    nk, nl = sdm["total_kini"], sdm["total_lalu"]
    kini, lalu = fin["kini"], fin["lalu"]

    def bagi(v: float | None, n: float | None) -> float | None:
        return (v / n) if (v is not None and n and n > 0) else None

    metrik = []
    for key, label in (
        ("pendapatan", "Pendapatan per karyawan"),
        ("laba_kotor", "Laba kotor per karyawan"),
        ("beban_usaha", "Beban usaha per karyawan"),
        ("laba_bersih", "Laba bersih per karyawan"),
    ):
        vk = bagi(kini.get(key), nk)
        vl = bagi(lalu.get(key), nl)
        chg = ((vk / vl) - 1.0) * 100.0 if (vk is not None and vl and vl != 0) else None
        metrik.append({"kunci": key, "label": label, "kini": vk, "lalu": vl, "perubahan_pct": chg})

    depts = sdm["departemen"]
    biaya_sdm_ada = depts and all(d["biaya_sdm_juta"] is not None for d in depts)
    tot_biaya_sdm = sum(d["biaya_sdm_juta"] for d in depts) if biaya_sdm_ada else None
    if tot_biaya_sdm is not None:
        metrik.append({
            "kunci": "biaya_sdm",
            "label": "Biaya SDM per karyawan",
            "kini": tot_biaya_sdm / nk,
            "lalu": None,
            "perubahan_pct": None,
        })

    porsi_sdm_pend = (tot_biaya_sdm / kini["pendapatan"] * 100.0) if (tot_biaya_sdm is not None and kini.get("pendapatan")) else None
    porsi_sdm_gk = (tot_biaya_sdm / kini["laba_kotor"] * 100.0) if (tot_biaya_sdm is not None and kini.get("laba_kotor")) else None

    return {
        "metrik": metrik,
        "total_biaya_sdm_juta": tot_biaya_sdm,
        "porsi_sdm_pendapatan_pct": porsi_sdm_pend,
        "porsi_sdm_laba_kotor_pct": porsi_sdm_gk,
    }


def susun_rekomendasi_departemen(fin: dict[str, Any], sdm: dict[str, Any]) -> list[dict[str, Any]]:
    """Bangun KPI prioritas dan arah budgeting per departemen berdasar sinyal keuangan."""
    sig = fin["sinyal"]
    dso = sig.get("dso")
    dio = sig.get("dio")
    gm = sig.get("gross_margin")
    gm_l = sig.get("gross_margin_lalu")
    opex = sig.get("opex_ratio")
    rg = sig.get("rev_growth")
    cfo = sig.get("cfo_to_ni")

    gm_turun = gm is not None and gm_l is not None and (gm - gm_l) <= -1.0
    stok_berat = dio is not None and dio >= 60
    piutang_lambat = dso is not None and dso >= 45
    opex_tinggi = opex is not None and opex >= 15.0
    kas_ketat = cfo is not None and cfo < 0.75

    aturan = {
        "penjualan": {
            "kpi": [
                "Pertumbuhan pendapatan neto (% YoY)",
                "Hari penagihan piutang / DSO pelanggan" + (f" (saat ini {_idn(dso, 0)} hari)" if dso is not None else ""),
                "Margin kotor per segmen / produk (cegah diskon berlebih)",
            ],
            "budget": (
                "Batasi kenaikan anggaran pemasaran/promosi di bawah target pertumbuhan penjualan; kaitkan insentif tim penjualan dengan kas tertagih (bukan hanya nilai faktur)."
                if (piutang_lambat or (rg is not None and rg < 5.0))
                else "Pertahankan rasio biaya penjualan terhadap omzet sambil memantau batas kredit pelanggan utama."
            ),
        },
        "produksi": {
            "kpi": [
                "Output & nilai tambah per karyawan produksi",
                "Tingkat reject / waste dan efisiensi pemakaian bahan",
                "Utilisasi kapasitas lini utama (%)",
            ],
            "budget": (
                "Tahan penambahan headcount tetap sampai produktivitas Rp/karyawan & margin kotor membaik; alokasikan anggaran hanya pada perbaikan bottleneck/efisiensi bahan."
                if (gm_turun or stok_berat)
                else "Ikat anggaran lembur dan tenaga kerja tidak tetap terhadap volume realisasi produksi."
            ),
        },
        "gudang_logistik": {
            "kpi": [
                "Hari persediaan / DIO" + (f" (saat ini {_idn(dio, 0)} hari)" if dio is not None else ""),
                "Persentase stok slow-moving (> 90 / > 180 hari)",
                "Biaya logistik per order / ton terkirim",
            ],
            "budget": (
                "Kunci batas stok maksimum (reorder cap) sebelum menambah anggaran sewa gudang/armada; fokuskan dana pada pengurasan stok lama."
                if stok_berat
                else "Anggaran logistik mengikuti volume pengiriman dengan target penurunan biaya per unit."
            ),
        },
        "keuangan_adm": {
            "kpi": [
                "Konversi laba ke kas operasi" + (f" (saat ini {_idn(cfo, 2)}x)" if cfo is not None else ""),
                "Kecepatan tutup buku bulanan (hari kerja)",
                "Kepatuhan batas kredit pelanggan & DPO pemasok",
            ],
            "budget": (
                "Pertahankan headcount inti; prioritaskan anggaran perbaikan otomasi penagihan, aging piutang, dan kontrol kas harian."
                if (kas_ketat or piutang_lambat)
                else "Terapkan anggaran operasional datar (flat) kecuali ada kebutuhan audit/sistem yang terbukti menurunkan biaya modal kerja."
            ),
        },
        "umum_it_hr": {
            "kpi": [
                "Rasio beban usaha / pendapatan" + (f" (saat ini {_idn(opex, 1)}%)" if opex is not None else ""),
                "Pendapatan per karyawan perusahaan",
                "Tingkat lembur & turnover karyawan kunci",
            ],
            "budget": (
                "Terapkan zero-based budgeting untuk biaya umum/administrasi; penambahan staf non-operasional ditunda hingga beban usaha per karyawan turun."
                if opex_tinggi
                else "Alokasikan anggaran pelatihan/produktivitas SDM yang berdampak langsung ke efisiensi tiap unit."
            ),
        },
        "manajemen": {
            "kpi": [
                "Siklus konversi kas (CCC) & arus kas bebas",
                "Imbal hasil aset (ROA) dan ekuitas (ROE)",
                "Realisasi vs target RKAP",
            ],
            "budget": "Prioritaskan belanja modal (capex) hanya pada proyek dengan payback jelas dan tidak mengganggu batas kas minimum.",
        },
        "umum": {
            "kpi": ["Produktivitas output per karyawan", "Realisasi biaya vs anggaran departemen"],
            "budget": "Tetapkan pagu biaya tahunan berbasis target output yang terukur.",
        },
    }

    daftar = sdm["departemen"] or [
        {"departemen": "Produksi / Operasional", "kategori": "produksi", "karyawan_kini": None, "karyawan_lalu": None, "biaya_sdm_juta": None, "anggaran_juta": None, "catatan": "Rincian headcount per departemen PERLU DATA"},
        {"departemen": "Penjualan & Pemasaran", "kategori": "penjualan", "karyawan_kini": None, "karyawan_lalu": None, "biaya_sdm_juta": None, "anggaran_juta": None, "catatan": "Rincian headcount per departemen PERLU DATA"},
        {"departemen": "Gudang & Logistik", "kategori": "gudang_logistik", "karyawan_kini": None, "karyawan_lalu": None, "biaya_sdm_juta": None, "anggaran_juta": None, "catatan": "Rincian headcount per departemen PERLU DATA"},
        {"departemen": "Keuangan, HR & Umum", "kategori": "keuangan_adm", "karyawan_kini": None, "karyawan_lalu": None, "biaya_sdm_juta": None, "anggaran_juta": None, "catatan": "Rincian headcount per departemen PERLU DATA"},
    ]

    hasil: list[dict[str, Any]] = []
    tot = sdm["total_kini"]
    for d in daftar:
        kat = d["kategori"]
        info_k = aturan.get(kat, aturan["umum"])
        nk = d["karyawan_kini"]
        porsi = (nk / tot * 100.0) if (nk is not None and tot > 0) else None
        hasil.append({
            "departemen": d["departemen"],
            "kategori": kat,
            "karyawan_kini": nk,
            "karyawan_lalu": d["karyawan_lalu"],
            "porsi_pct": porsi,
            "biaya_sdm_per_orang_juta": (d["biaya_sdm_juta"] / nk) if (d["biaya_sdm_juta"] is not None and nk) else None,
            "anggaran_juta": d["anggaran_juta"],
            "kpi_prioritas": info_k["kpi"],
            "rekomendasi_budget": info_k["budget"],
            "catatan": d["catatan"],
        })
    return hasil


def render_md(fin: dict[str, Any], sdm: dict[str, Any], prod: dict[str, Any], rek: list[dict[str, Any]], gaya: str) -> str:
    sam = fin["samaran"]
    p_kini, p_lalu = fin["periode"], fin["periode_lalu"]
    nk, nl = sdm["total_kini"], sdm["total_lalu"]
    m_map = {m["kunci"]: m for m in prod["metrik"]}
    rev_org = fmt_uang_juta(m_map["pendapatan"]["kini"], sam)

    L = [
        f"# Efisiensi SDM & Rekomendasi KPI Budgeting: {fin['perusahaan']} ({p_kini})",
        "",
        f"Dengan **{int(round(nk))} karyawan**, pendapatan per karyawan tercatat **{rev_org}/orang** "
        + (f"(sebelumnya {int(round(nl))} orang: {fmt_uang_juta(m_map['pendapatan']['lalu'], sam)}/orang)."
           if (nl and m_map["pendapatan"]["lalu"] is not None) else "(pembanding jumlah karyawan lalu PERLU DATA)."),
        "",
        "## 1. Rasio Rp per Karyawan",
        "",
    ]

    if gaya == "checklist":
        for m in prod["metrik"]:
            centang = "x" if (m["perubahan_pct"] is None or (m["kunci"] != "beban_usaha" and m["perubahan_pct"] >= 0)) else " "
            chg_txt = f" ({'+' if m['perubahan_pct'] > 0 else ''}{_idn(m['perubahan_pct'], 1)}%)" if m["perubahan_pct"] is not None else ""
            L.append(f"- [{centang}] **{m['label']}**: {fmt_uang_juta(m['kini'], sam)}/orang{chg_txt}")
    else:
        L += [f"| Indikator per Karyawan | {p_kini} | {p_lalu or 'Pembanding'} | Perubahan |", "|---|---:|---:|---:|"]
        for m in prod["metrik"]:
            chg_txt = f"{'+' if m['perubahan_pct'] > 0 else ''}{_idn(m['perubahan_pct'], 1)}%" if m["perubahan_pct"] is not None else "-"
            L.append(f"| {m['label']} | {fmt_uang_juta(m['kini'], sam)} | {fmt_uang_juta(m['lalu'], sam) if m['lalu'] is not None else '-'} | {chg_txt} |")

    if prod["total_biaya_sdm_juta"] is None:
        L += ["", "> Catatan biaya gaji/SDM total: **PERLU DATA** (isi kolom `biaya_sdm_tahunan` di CSV agar porsi biaya SDM terhadap omzet/laba kotor dapat dihitung)."]
    else:
        L += [
            "",
            f"- Total biaya SDM: **{fmt_uang_juta(prod['total_biaya_sdm_juta'], sam)}** "
            f"({_idn(prod['porsi_sdm_pendapatan_pct'], 1)}% dari pendapatan | {_idn(prod['porsi_sdm_laba_kotor_pct'], 1)}% dari laba kotor).",
        ]

    L += ["", "## 2. Struktur Organisasi, KPI Prioritas, & Arah Budgeting per Departemen", ""]
    if gaya == "ringkas":
        L += ["| Departemen | Karyawan | Porsi | KPI Utama | Arah Budgeting |", "|---|---:|---:|---|---|"]
        for r in rek:
            org = str(int(round(r["karyawan_kini"]))) if r["karyawan_kini"] is not None else "PERLU DATA"
            por = f"{_idn(r['porsi_pct'], 1)}%" if r["porsi_pct"] is not None else "-"
            L.append(f"| {r['departemen']} | {org} | {por} | {r['kpi_prioritas'][0]} | {r['rekomendasi_budget']} |")
    else:
        for r in rek:
            org = f"{int(round(r['karyawan_kini']))} orang ({_idn(r['porsi_pct'], 1)}%)" if r["karyawan_kini"] is not None else "PERLU DATA"
            L.append(f"### {r['departemen']} - {org}")
            if r["biaya_sdm_per_orang_juta"] is not None:
                L.append(f"- Biaya SDM rata-rata: {fmt_uang_juta(r['biaya_sdm_per_orang_juta'], sam)}/orang")
            if r["anggaran_juta"] is not None:
                L.append(f"- Usulan anggaran tahun depan: {fmt_uang_juta(r['anggaran_juta'], sam)}")
            L.append("- **KPI prioritas:** " + "; ".join(r["kpi_prioritas"]))
            L.append(f"- **Rekomendasi budgeting:** {r['rekomendasi_budget']}")
            L.append("")

    L += [
        "",
        "_Alat bantu perencanaan manajemen; angka target dan pagu final ditetapkan oleh direksi._",
        "",
        "Disusun dengan TQ Board Insight | totalquality.co.id",
    ]
    return "\n".join(L)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Analisa Rp per karyawan & KPI budgeting per departemen")
    ap.add_argument("--rasio", type=Path, required=True, help="rasio.json (tahunan) atau laporan.json (bulanan)")
    ap.add_argument("--input", type=Path, help="File CSV/JSON struktur departemen & headcount")
    ap.add_argument("--karyawan", type=int, help="Total jumlah karyawan periode kini")
    ap.add_argument("--karyawan-lalu", type=int, help="Total jumlah karyawan periode lalu (opsional)")
    ap.add_argument("--departemen", help="Ringkas CLI, mis. 'Produksi:70,Penjualan:20,Gudang:15,Keuangan & Umum:15'")
    ap.add_argument("--satuan-sdm", default="juta", help="Satuan angka biaya SDM/anggaran di input (default: juta)")
    ap.add_argument("--gaya", choices=["ringkas", "detail", "checklist"])
    ap.add_argument("--preferensi", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--diam", action="store_true")
    a = ap.parse_args(argv)

    pref = json.loads(a.preferensi.read_text(encoding="utf-8-sig")) if a.preferensi and a.preferensi.exists() else {}
    gaya = a.gaya or pref.get("gaya_narasi") or "detail"

    try:
        fin = muat_keuangan(a.rasio)
        sdm = muat_sdm(a.input, a.karyawan, a.karyawan_lalu, a.departemen, a.satuan_sdm)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"GAGAL: {e}", file=sys.stderr)
        return 1

    prod = hitung_per_karyawan(fin, sdm)
    rek = susun_rekomendasi_departemen(fin, sdm)
    md = render_md(fin, sdm, prod, rek, gaya)

    if a.out_md:
        a.out_md.parent.mkdir(parents=True, exist_ok=True)
        a.out_md.write_text(md, encoding="utf-8")
    if a.out_json:
        a.out_json.parent.mkdir(parents=True, exist_ok=True)
        a.out_json.write_text(json.dumps({
            "perusahaan": fin["perusahaan"],
            "periode": fin["periode"],
            "keuangan": fin,
            "sdm": sdm,
            "produktivitas": prod,
            "rekomendasi_departemen": rek,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
