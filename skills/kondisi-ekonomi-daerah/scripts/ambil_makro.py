#!/usr/bin/env python3
"""Ambil data makro nasional (World Bank API, tanpa key) dan gabungkan dengan data ekonomi daerah.

Pemakaian:
    python scripts/ambil_makro.py --daerah "Jawa Barat" --out ekonomi.json
    python scripts/ambil_makro.py --input templates/template-ekonomi-daerah.csv --out ekonomi.json
    python scripts/ambil_makro.py --daerah "Surabaya" --pdrb-pct 5.4 --inflasi-daerah-pct 3.2 --kenaikan-ump-pct 6.5 --out ekonomi.json
    python scripts/ambil_makro.py --input daerah.csv --offline --out ekonomi.json

Sumber online (opsional, tanpa API key): World Bank Indicators API v2 (api.worldbank.org).
Opsional BPS WebAPI: --bps-key <key> (atau env BPS_API_KEY) + --bps-domain <kode_domain>.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import datetime as _dt
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

WB_INDIKATOR = {
    "pertumbuhan_pdb_pct": ("NY.GDP.MKTP.KD.ZG", "Pertumbuhan PDB tahunan (%)"),
    "inflasi_nasional_pct": ("FP.CPI.TOTL.ZG", "Inflasi IHK nasional (%)"),
    "suku_bunga_pinjaman_pct": ("FR.INR.LEND", "Suku bunga pinjaman (%)"),
    "kurs_usd": ("PA.NUS.FCRF", "Kurs rata-rata resmi (IDR/USD)"),
    "pengangguran_nasional_pct": ("SL.UEM.TOTL.ZS", "Tingkat pengangguran nasional (%)"),
}

KUNCI_DAERAH = (
    "daerah",
    "pdrb_pct",
    "inflasi_daerah_pct",
    "kenaikan_ump_pct",
    "pengangguran_daerah_pct",
    "suku_bunga_pct",
    "kurs_usd",
    "catatan_risiko_daerah",
)


def parse_angka(v: Any) -> float | None:
    """Konversi angka ID/EN menjadi float, atau None jika kosong."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("%", "").replace(" ", "")
    if not s or s in ("-", "--", "n/a", "na", "null"):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _http_json(url: str, timeout: int = 8, coba: int = 2) -> Any:
    last_err = None
    for i in range(coba):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "corporate-health-check/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as e:
            last_err = e
            if i < coba - 1:
                time.sleep(1.0)
    raise RuntimeError(f"Gagal mengakses {url}: {last_err}")


def _ambil_satu_wb(negara: str, kunci: str, kode_wb: str, label: str) -> tuple[str, dict[str, Any] | None, str | None]:
    url = f"https://api.worldbank.org/v2/country/{negara}/indicator/{kode_wb}?format=json&per_page=10"
    try:
        payload = _http_json(url)
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            return kunci, None, f"Respons World Bank untuk {kode_wb} tidak lengkap."
        seri = [
            {"tahun": str(item["date"]), "nilai": float(item["value"])}
            for item in payload[1]
            if item.get("value") is not None
        ]
        seri.sort(key=lambda x: x["tahun"], reverse=True)
        return kunci, {
            "label": label,
            "kode_wb": kode_wb,
            "kini": seri[0] if seri else None,
            "lalu": seri[1] if len(seri) > 1 else None,
            "riwayat": seri[:5],
        }, None
    except RuntimeError as e:
        return kunci, None, f"{label}: {e}"


def ambil_world_bank(negara: str) -> tuple[dict[str, Any], list[str]]:
    """Ambil seri tahunan terbaru dari World Bank API tanpa API key."""
    hasil: dict[str, Any] = {}
    peringatan: list[str] = []
    with ThreadPoolExecutor(max_workers=len(WB_INDIKATOR)) as ex:
        futs = [
            ex.submit(_ambil_satu_wb, negara, k, kode_wb, label)
            for k, (kode_wb, label) in WB_INDIKATOR.items()
        ]
        for fut in futs:
            kunci, data, warn = fut.result()
            if data is not None:
                hasil[kunci] = data
            if warn:
                peringatan.append(warn)
    return hasil, peringatan


def ambil_bps_meta(domain: str, bps_key: str) -> dict[str, Any]:
    """Ambil daftar indikator strategis BPS WebAPI jika pengguna menyertakan API key."""
    url = f"https://webapi.bps.go.id/v1/api/list/model/indicators/domain/{domain}/key/{bps_key}/"
    payload = _http_json(url)
    data = payload.get("data")
    items = data[1] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []
    ringkas = [
        {"id": it.get("indicator_id"), "judul": it.get("title"), "nilai": it.get("value"), "satuan": it.get("unit")}
        for it in items[:20]
        if isinstance(it, dict)
    ]
    return {"domain": domain, "jumlah": len(ringkas), "indikator": ringkas}


def baca_input_daerah(path: Path) -> dict[str, Any]:
    """Baca file JSON atau CSV input kondisi ekonomi daerah."""
    if not path.exists():
        raise FileNotFoundError(f"Berkas tidak ditemukan: {path}")
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if "indikator_daerah" in raw and isinstance(raw["indikator_daerah"], dict):
            return raw["indikator_daerah"]
        return raw

    teks = path.read_text(encoding="utf-8-sig")
    sample = "\n".join(teks.splitlines()[:10])
    delim = ";" if sample.count(";") > sample.count(",") else ","
    rows = list(csv.reader(teks.splitlines(), delimiter=delim))
    if not rows:
        return {}
    head = [c.strip().lower() for c in rows[0]]
    idx = {k: i for i, k in enumerate(head)}
    if "kode" not in idx:
        raise ValueError("CSV daerah harus memiliki kolom 'kode' (lihat templates/template-ekonomi-daerah.csv).")

    out: dict[str, Any] = {}
    for r in rows[1:]:
        if not r or idx["kode"] >= len(r) or not r[idx["kode"]].strip():
            continue
        kode = r[idx["kode"]].strip()
        if kode not in KUNCI_DAERAH:
            continue
        kini_raw = r[idx["periode_kini"]].strip() if "periode_kini" in idx and idx["periode_kini"] < len(r) else (
            r[idx["nilai"]].strip() if "nilai" in idx and idx["nilai"] < len(r) else ""
        )
        lalu_raw = r[idx["periode_lalu"]].strip() if "periode_lalu" in idx and idx["periode_lalu"] < len(r) else ""
        sumber = r[idx["sumber"]].strip() if "sumber" in idx and idx["sumber"] < len(r) else ""

        if kode in ("daerah", "catatan_risiko_daerah"):
            if kini_raw:
                out[kode] = kini_raw
        else:
            vk = parse_angka(kini_raw)
            vl = parse_angka(lalu_raw)
            if vk is not None or vl is not None:
                out[kode] = {"kini": vk, "lalu": vl, "sumber": sumber or path.name}
    return out


def _norm_entry(val: Any, sumber_default: str = "Input pengguna") -> dict[str, Any] | None:
    if val is None:
        return None
    if isinstance(val, dict):
        kini = parse_angka(val.get("kini"))
        lalu = parse_angka(val.get("lalu"))
        if kini is None and lalu is None:
            return None
        return {"kini": kini, "lalu": lalu, "sumber": val.get("sumber") or sumber_default}
    v = parse_angka(val)
    if v is None:
        return None
    return {"kini": v, "lalu": None, "sumber": sumber_default}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Ambil data makro & susun ekonomi.json kondisi daerah")
    ap.add_argument("--negara", default="IDN", help="Kode negara ISO3 untuk World Bank API (default: IDN)")
    ap.add_argument("--daerah", help="Nama provinsi / kabupaten / kota operasional")
    ap.add_argument("--input", type=Path, help="File CSV/JSON kondisi ekonomi daerah")
    ap.add_argument("--pdrb-pct", type=float, help="Pertumbuhan PDRB daerah YoY (%%)")
    ap.add_argument("--inflasi-daerah-pct", type=float, help="Inflasi daerah YoY (%%)")
    ap.add_argument("--kenaikan-ump-pct", type=float, help="Kenaikan UMP/UMK tahunan (%%)")
    ap.add_argument("--pengangguran-daerah-pct", type=float, help="Tingkat pengangguran terbuka daerah (%%)")
    ap.add_argument("--suku-bunga-pct", type=float, help="Suku bunga acuan/kredit berlaku (%%)")
    ap.add_argument("--kurs-usd", type=float, help="Kurs IDR per USD terkini")
    ap.add_argument("--catatan-daerah", help="Catatan risiko wilayah (cuaca, logistik, regulasi)")
    ap.add_argument("--bps-key", default=os.environ.get("BPS_API_KEY", ""), help="API key BPS WebAPI (opsional)")
    ap.add_argument("--bps-domain", default="0000", help="Kode domain wilayah BPS (mis. 3200 Jawa Barat)")
    ap.add_argument("--offline", action="store_true", help="Lewati pengambilan World Bank API")
    ap.add_argument("--out", type=Path, help="Berkas JSON keluaran (mis. ekonomi.json)")
    ap.add_argument("--diam", action="store_true", help="Ringkas keluaran terminal")
    a = ap.parse_args(argv)

    daerah_data: dict[str, Any] = {}
    if a.input:
        try:
            daerah_data = baca_input_daerah(a.input)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
            print(f"GAGAL membaca input daerah: {e}", file=sys.stderr)
            return 1

    indikator_daerah: dict[str, Any] = {
        k: _norm_entry(daerah_data.get(k))
        for k in ("pdrb_pct", "inflasi_daerah_pct", "kenaikan_ump_pct", "pengangguran_daerah_pct", "suku_bunga_pct", "kurs_usd")
    }
    overrides = {
        "pdrb_pct": a.pdrb_pct,
        "inflasi_daerah_pct": a.inflasi_daerah_pct,
        "kenaikan_ump_pct": a.kenaikan_ump_pct,
        "pengangguran_daerah_pct": a.pengangguran_daerah_pct,
        "suku_bunga_pct": a.suku_bunga_pct,
        "kurs_usd": a.kurs_usd,
    }
    for k, v in overrides.items():
        if v is not None:
            indikator_daerah[k] = {"kini": float(v), "lalu": (indikator_daerah[k] or {}).get("lalu"), "sumber": "Argumen CLI"}

    nama_daerah = a.daerah or daerah_data.get("daerah") or "Nasional / Belum ditentukan"
    catatan_daerah = a.catatan_daerah or daerah_data.get("catatan_risiko_daerah") or ""

    nasional: dict[str, Any] = {}
    peringatan: list[str] = []
    sumber_list = []
    if not a.offline:
        nasional, warn_wb = ambil_world_bank(a.negara.upper())
        peringatan.extend(warn_wb)
        if nasional:
            sumber_list.append(f"World Bank Open Data API ({a.negara.upper()})")
    if a.input:
        sumber_list.append(f"Berkas daerah ({a.input.name})")

    bps_data = None
    if a.bps_key and not a.offline:
        try:
            bps_data = ambil_bps_meta(a.bps_domain, a.bps_key)
            sumber_list.append(f"BPS WebAPI (domain {a.bps_domain})")
        except RuntimeError as e:
            peringatan.append(f"BPS WebAPI: {e}")

    hasil = {
        "versi": "1.0.0",
        "diambil": _dt.datetime.now().isoformat(timespec="seconds"),
        "negara": a.negara.upper(),
        "daerah": nama_daerah,
        "sumber": sumber_list or ["Input manual / offline"],
        "peringatan": peringatan,
        "indikator_daerah": indikator_daerah,
        "catatan_risiko_daerah": catatan_daerah,
        "nasional": nasional,
    }
    if bps_data:
        hasil["bps"] = bps_data

    teks = json.dumps(hasil, indent=2, ensure_ascii=False)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(teks, encoding="utf-8")
        if not a.diam:
            print(f"Data ekonomi ditulis ke {a.out} (daerah: {nama_daerah}).")
    else:
        print(teks)
    for w in peringatan:
        print(f"PERINGATAN: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
