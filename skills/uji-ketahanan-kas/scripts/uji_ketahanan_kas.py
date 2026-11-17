#!/usr/bin/env python3
"""Uji ketahanan kas (cash stress test) deterministik dari paket data bulanan.

Pemakaian:
    python scripts/uji_ketahanan_kas.py Data-Keuangan-Bulanan.xlsx
    python scripts/uji_ketahanan_kas.py paket.xlsx --skenario skenario.json --horizon 6 \
        --plafon 2500 --batas-dscr 1.25 --out-md uji-kas.md --out-json uji-kas.json

Masukan : paket data bulanan yang sama dengan skill laporan-analisa (Excel template-paket-data.xlsx atau JSON).
Skenario: JSON (lihat references/skema-skenario.md). Tanpa --skenario dipakai skenario bawaan.
Keluaran: tabel skenario (kas per bulan, bulan pertama di bawah kas minimum, lama bertahan, DSCR & interest
          coverage setelah guncangan), uji balik (berapa besar guncangan sampai kas habis), dan JSON semua angka.

Semua angka dihitung di sini; AI hanya menulis narasi dari hasilnya.
Exit code: 0 sukses | 1 input tidak terbaca | 2 validasi gagal (neraca tidak seimbang / data kurang).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
# Mesin bersama dari skill laporan-analisa. Dalam zip skill, salinannya ada di folder scripts/ ini sendiri.
for _p in (HERE, HERE.parents[1] / "laporan-analisa" / "scripts"):
    if (_p / "analisa.py").exists():
        sys.path.insert(0, str(_p))
        break
from analisa import Analisa, AnalisaError, Data, Fmt, lbl, geser, rentang  # noqa: E402
from baca_paket import PaketError, baca  # noqa: E402

VERSI = "1.0.0"
HARI_BULAN = 30.4

# Kunci guncangan yang dikenali (semua opsional, 0 = tidak ada guncangan).
KUNCI = {
    "penjualan_pct": "Perubahan penjualan (%), mis. -15",
    "harga_bahan_pct": "Perubahan harga bahan tanpa kenaikan harga jual (%), mis. 10",
    "biaya_tetap_pct": "Perubahan biaya tetap tunai: upah, overhead, beban umum (%)",
    "tambah_dso_hari": "Penagihan piutang molor (hari); kas tertahan sekali di bulan mulai",
    "kurang_dpo_hari": "Pemasok minta bayar lebih cepat (hari); kas keluar sekali di bulan mulai",
    "tambah_dio_hari": "Persediaan menumpuk (hari); kas tertahan sekali di bulan mulai",
    "bunga_poin": "Kenaikan suku bunga utang bank (poin persentase per tahun)",
    "belanja_tambahan": "Pengeluaran sekali (satuan paket), mis. denda, perbaikan mesin",
    "mulai_bulan": "Bulan ke- guncangan mulai (bawaan 1)",
    "durasi_bulan": "Lama guncangan berulang (bulan); kosong = sampai akhir horizon",
}

SKENARIO_BAWAAN = [
    {"nama": "Dasar (tren 3 bulan terakhir berlanjut)"},
    {"nama": "Penjualan turun 15%", "penjualan_pct": -15},
    {"nama": "Harga bahan naik 10% tanpa kenaikan harga jual", "harga_bahan_pct": 10},
    {"nama": "DSO molor 15 hari & penjualan turun 10%", "tambah_dso_hari": 15, "penjualan_pct": -10},
    {"nama": "Suku bunga naik 2 poin", "bunga_poin": 2},
    {"nama": "Gabungan: resesi ringan", "penjualan_pct": -10, "harga_bahan_pct": 5, "tambah_dso_hari": 10,
     "bunga_poin": 1},
    {"nama": "Kehilangan pelanggan terbesar (-25%) & pemasok minta bayar 15 hari lebih cepat",
     "penjualan_pct": -25, "kurang_dpo_hari": 15},
]


class SkenarioError(Exception):
    pass


# ================================================================ dasar ===
def cek_neraca(paket: dict, f: Fmt) -> list:
    """Jalankan gerbang validasi laporan-analisa (G1 neraca seimbang wajib lulus)."""
    obj = SimpleNamespace(p=paket, d=Data(paket), f=f)
    return Analisa.cek_gerbang(obj)


def angka_dasar(d: Data) -> dict:
    """Rata-rata 3 bulan terakhir, sama persis dengan uji_ketahanan() di laporan-analisa."""
    B = d.aktif
    bl = rentang(B, 3)
    x = d.periode(bl)
    if x is None:
        raise AnalisaError(f"Butuh laba rugi, arus kas, dan neraca lengkap untuk 3 bulan s.d. {lbl(B)}.")
    r = lambda k: x[k] / 3  # noqa: E731
    rev, bahan, sell = r("pendapatan"), r("hpp_bahan"), r("beban_penjualan")
    tetap = r("hpp_upah") + r("hpp_overhead") + r("beban_umum_adm")
    ltm = x.get("ltm") or {}
    cicilan_bln = r("pembayaran_pinjaman_panjang")
    return {
        "bulan_aktif": B, "bulan_dasar": bl,
        "kas": x["bs"]["kas"], "utang_bank": x["bs"]["utang_bank"],
        "pendapatan": rev, "bahan": bahan, "beban_penjualan": sell, "tetap": tetap,
        "ebitda": r("ebitda"), "bunga": r("beban_bunga"), "cicilan": cicilan_bln,
        "cm": (rev - bahan - sell) / rev if rev else 0.0,
        "arus_dasar": (x["arus_kas_operasi"] - x["belanja_modal"] - x["pembayaran_pinjaman_panjang"]) / 3,
        "ltm": ltm,
    }


# ============================================================== skenario ==
def validasi_skenario(s: dict, i: int, horizon: int) -> dict:
    if not isinstance(s, dict):
        raise SkenarioError(f"Skenario ke-{i} harus objek JSON.")
    asing = set(s) - set(KUNCI) - {"nama", "catatan"}
    if asing:
        raise SkenarioError(f"Skenario ke-{i}: kunci tidak dikenal {sorted(asing)}. Kunci sah: {sorted(KUNCI)}")
    out = {"nama": str(s.get("nama") or f"Skenario {i}"), "catatan": s.get("catatan", "")}
    for k in KUNCI:
        v = s.get(k)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise SkenarioError(f"Skenario '{out['nama']}': {k} harus angka.")
        out[k] = float(v)
    if out.get("penjualan_pct", 0) < -100:
        raise SkenarioError(f"Skenario '{out['nama']}': penjualan_pct tidak boleh di bawah -100.")
    mulai = int(out.get("mulai_bulan", 1))
    if not 1 <= mulai <= horizon:
        raise SkenarioError(f"Skenario '{out['nama']}': mulai_bulan harus 1..{horizon}.")
    out["mulai_bulan"] = mulai
    if "durasi_bulan" in out and out["durasi_bulan"] < 1:
        raise SkenarioError(f"Skenario '{out['nama']}': durasi_bulan minimal 1.")
    return out


def dampak_bulanan(s: dict, a: dict) -> tuple[float, float]:
    """(dampak kas per bulan berulang, EBITDA per bulan setelah guncangan)."""
    p = s.get("penjualan_pct", 0) / 100
    hb = s.get("harga_bahan_pct", 0) / 100
    bt = s.get("biaya_tetap_pct", 0) / 100
    bp = s.get("bunga_poin", 0) / 100
    d_jual = p * a["pendapatan"] * a["cm"]          # kontribusi yang hilang/bertambah
    d_bahan = -hb * a["bahan"] * (1 + p)            # bahan ikut volume penjualan
    d_tetap = -bt * a["tetap"]
    d_bunga = -bp * a["utang_bank"] / 12
    ebitda = a["ebitda"] + d_jual + d_bahan + d_tetap
    return d_jual + d_bahan + d_tetap + d_bunga, ebitda


def dampak_sekali(s: dict, a: dict) -> float:
    p = s.get("penjualan_pct", 0) / 100
    hpp_kas = a["bahan"] * (1 + p) + a["tetap"]
    # Piutang dihitung dari pendapatan dasar (sama dengan laporan-analisa): tagihan lama yang sudah terbit ikut tertahan.
    return -(s.get("tambah_dso_hari", 0) / HARI_BULAN * a["pendapatan"]
             + s.get("kurang_dpo_hari", 0) / HARI_BULAN * a["bahan"] * (1 + p)
             + s.get("tambah_dio_hari", 0) / HARI_BULAN * hpp_kas
             + s.get("belanja_tambahan", 0))


def jalankan(s: dict, a: dict, horizon: int, kas_min: float, plafon: float) -> dict:
    mulai = s["mulai_bulan"]
    akhir_guncang = mulai - 1 + int(s.get("durasi_bulan") or horizon)
    berulang, ebitda_baru = dampak_bulanan(s, a)
    sekali = dampak_sekali(s, a)
    kas = a["kas"]
    jalur, bawah_min, habis, habis_plafon = [], None, None, None
    for t in range(1, horizon + 1):
        kas += a["arus_dasar"]
        if mulai <= t <= akhir_guncang:
            kas += berulang
        if t == mulai:
            kas += sekali
        jalur.append(kas)
        if bawah_min is None and kas < kas_min:
            bawah_min = t
        if habis is None and kas < 0:
            habis = t
        if habis_plafon is None and kas + plafon < 0:
            habis_plafon = t
    akhir = jalur[-1]
    st = "kritis" if akhir < kas_min or habis else ("waspada" if akhir < 1.5 * kas_min else "aman")
    rev_baru = a["pendapatan"] * (1 + s.get("penjualan_pct", 0) / 100)
    bunga_baru = a["bunga"] + s.get("bunga_poin", 0) / 100 * a["utang_bank"] / 12
    layanan = bunga_baru + a["cicilan"]
    return {
        "nama": s["nama"], "parameter": {k: v for k, v in s.items() if k in KUNCI}, "catatan": s.get("catatan", ""),
        "dampak_berulang_bln": berulang, "dampak_sekali": sekali, "jalur_kas": jalur,
        "kas_terendah": min(jalur), "kas_akhir": akhir, "bulan_bawah_minimum": bawah_min,
        "bulan_kas_habis": habis, "bulan_habis_dengan_plafon": habis_plafon,
        # Kas akhir dibagi biaya tetap per bulan (sama dengan laporan-analisa); negatif berarti sudah defisit.
        "bertahan_bulan": akhir / a["tetap"] if a["tetap"] else None,
        "margin_ebitda": ebitda_baru / rev_baru * 100 if rev_baru else None,
        "dscr": ebitda_baru / layanan if layanan > 0 else None,
        "icr": ebitda_baru / bunga_baru if bunga_baru > 0 else None,
        "status": st,
    }


def uji_balik(a: dict, horizon: int, kas_min: float, kunci: str, batas: float, arah: int) -> float | None:
    """Cari besaran guncangan terkecil yang membuat kas terendah menyentuh kas minimum (bisection)."""
    def kas_terendah(v):
        return jalankan({"nama": "", "mulai_bulan": 1, kunci: arah * v}, a, horizon, kas_min, 0)["kas_terendah"]

    if kas_terendah(0) < kas_min:
        return 0.0
    if kas_terendah(batas) >= kas_min:
        return None
    lo, hi = 0.0, batas
    for _ in range(60):
        mid = (lo + hi) / 2
        if kas_terendah(mid) < kas_min:
            hi = mid
        else:
            lo = mid
    return hi


# ================================================================ utama ===
def analisa(paket: dict, skenario: list | None = None, horizon: int = 3, kas_minimum: float | None = None,
            plafon: float = 0.0, batas_dscr: float | None = None, batas_icr: float | None = None) -> dict:
    if not 1 <= horizon <= 24:
        raise SkenarioError("horizon harus 1..24 bulan.")
    info = paket.get("info", {})
    f = Fmt(info.get("satuan", "juta"), info.get("mata_uang", "IDR"))
    gerbang = cek_neraca(paket, f)
    a = angka_dasar(Data(paket))
    kas_min = a["tetap"] if kas_minimum is None else float(kas_minimum)
    daftar = [validasi_skenario(s, i + 1, horizon) for i, s in enumerate(skenario or SKENARIO_BAWAAN)]
    hasil = [jalankan(s, a, horizon, kas_min, plafon) for s in daftar]
    for h in hasil:
        h["kovenan"] = []
        if batas_dscr is not None:
            h["kovenan"].append({"nama": "DSCR", "batas": batas_dscr, "nilai": h["dscr"],
                                 "lulus": h["dscr"] is None or h["dscr"] >= batas_dscr})
        if batas_icr is not None:
            h["kovenan"].append({"nama": "Interest coverage", "batas": batas_icr, "nilai": h["icr"],
                                 "lulus": h["icr"] is None or h["icr"] >= batas_icr})
    balik = [
        {"guncangan": "Penjualan turun", "satuan": "%", "nilai": uji_balik(a, horizon, kas_min, "penjualan_pct", 100, -1)},
        {"guncangan": "Harga bahan naik", "satuan": "%", "nilai": uji_balik(a, horizon, kas_min, "harga_bahan_pct", 500, 1)},
        {"guncangan": "Penagihan molor", "satuan": "hari", "nilai": uji_balik(a, horizon, kas_min, "tambah_dso_hari", 365, 1)},
    ]
    bulan = [geser(a["bulan_aktif"], t) for t in range(1, horizon + 1)]
    return {"versi": VERSI, "perusahaan": info.get("perusahaan", ""), "satuan": info.get("satuan", "juta"),
            "bulan_aktif": a["bulan_aktif"], "bulan_proyeksi": bulan, "horizon": horizon,
            "kas_kini": a["kas"], "kas_minimum": kas_min, "plafon_tersedia": plafon, "dasar": a,
            "gerbang": gerbang, "skenario": hasil, "uji_balik": balik,
            "asumsi": ("Arus kas dasar per bulan = rata-rata 3 bulan terakhir (arus kas operasi - belanja modal - cicilan "
                       "pinjaman). Penjualan memengaruhi kas lewat margin kontribusi (pendapatan - bahan - beban "
                       "penjualan). Perubahan hari piutang/persediaan/utang usaha dihitung sekali di bulan mulai. "
                       "Kas minimum bawaan = 1 bulan biaya tetap tunai (upah, overhead, beban umum). DSCR = EBITDA / "
                       "(bunga + cicilan) per bulan setelah guncangan. Tanpa pinjaman baru kecuali plafon yang disebut. "
                       "Perhitungan deterministik sederhana, bukan simulasi atau proyeksi resmi."),
            "_fmt": f}


def ke_md(h: dict) -> str:
    f: Fmt = h["_fmt"]
    L = [f"# Uji Ketahanan Kas{' - ' + h['perusahaan'] if h['perusahaan'] else ''}", "",
         f"Data s.d. **{lbl(h['bulan_aktif'])}** | horizon **{h['horizon']} bulan** "
         f"({lbl(h['bulan_proyeksi'][0])} - {lbl(h['bulan_proyeksi'][-1])})", "",
         f"- Kas saat ini: **{f.uang(h['kas_kini'])}**",
         f"- Kas minimum: **{f.uang(h['kas_minimum'])}**",
         f"- Arus kas dasar per bulan: **{f.uang(h['dasar']['arus_dasar'], True)}**"]
    if h["plafon_tersedia"]:
        L.append(f"- Sisa plafon kredit: **{f.uang(h['plafon_tersedia'])}**")
    L += ["", "## Hasil skenario", "",
          "| Skenario | Kas terendah | Kas akhir | Di bawah minimum | Kas habis | Bertahan | Margin EBITDA | DSCR | Status |",
          "|---|---:|---:|---|---|---:|---:|---:|---|"]
    bln = lambda t: lbl(h["bulan_proyeksi"][t - 1]) if t else "-"  # noqa: E731
    for s in h["skenario"]:
        habis = bln(s["bulan_kas_habis"])
        if s["bulan_kas_habis"] and h["plafon_tersedia"]:
            habis += " (dengan plafon: " + (bln(s["bulan_habis_dengan_plafon"]) if s["bulan_habis_dengan_plafon"] else "aman") + ")"
        L.append(f"| {s['nama']} | {f.uang(s['kas_terendah'])} | {f.uang(s['kas_akhir'])} | {bln(s['bulan_bawah_minimum'])} | "
                 f"{habis} | {'defisit' if (s['bertahan_bulan'] or 0) < 0 else f.nilai(s['bertahan_bulan'], 'bulan')} | {f.nilai(s['margin_ebitda'], '%')} | "
                 f"{f.nilai(s['dscr'], 'x')} | **{s['status'].upper()}** |")
    kov = [(s["nama"], k) for s in h["skenario"] for k in s["kovenan"] if not k["lulus"]]
    if any(s["kovenan"] for s in h["skenario"]):
        L += ["", "## Kovenan bank", ""]
        L += [f"- {n}: {k['nama']} {f.nilai(k['nilai'], 'x')} < batas {f.nilai(k['batas'], 'x')}" for n, k in kov] or \
             ["- Semua skenario memenuhi batas kovenan yang diberikan."]
    L += ["", "## Kas per bulan", "", "| Skenario | " + " | ".join(lbl(b) for b in h["bulan_proyeksi"]) + " |",
          "|---|" + "---:|" * h["horizon"]]
    for s in h["skenario"]:
        L.append(f"| {s['nama']} | " + " | ".join(f.uang(v) for v in s["jalur_kas"]) + " |")
    L += ["", "## Uji balik: seberapa besar guncangan sampai kas menyentuh minimum", ""]
    for b in h["uji_balik"]:
        v = b["nilai"]
        if v is None:
            t = "tidak tercapai dalam rentang uji"
        elif v == 0:
            t = "kas sudah di bawah minimum tanpa guncangan"
        else:
            t = f.nilai(v, "%") if b["satuan"] == "%" else f.nilai(v, "hari")
        L.append(f"- {b['guncangan']}: **{t}**")
    L += ["", "## Asumsi", "", h["asumsi"], "",
          "_Alat bantu analisis, bukan proyeksi resmi atau nasihat keuangan._"]
    return "\n".join(L) + "\n"


def ke_json(h: dict) -> dict:
    return {k: v for k, v in h.items() if not k.startswith("_")}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Uji ketahanan kas dari paket data bulanan")
    ap.add_argument("paket", type=Path, help="Excel template-paket-data.xlsx atau JSON")
    ap.add_argument("--skenario", type=Path, help="JSON daftar skenario (bawaan: 7 skenario standar)")
    ap.add_argument("--horizon", type=int, help="Jumlah bulan ke depan (1-24, bawaan 3)")
    ap.add_argument("--kas-minimum", type=float, help="Kas minimum (satuan paket); bawaan 1 bulan biaya tetap")
    ap.add_argument("--plafon", type=float, help="Sisa plafon kredit yang bisa ditarik (satuan paket)")
    ap.add_argument("--batas-dscr", type=float, help="Batas kovenan DSCR, mis. 1.25")
    ap.add_argument("--batas-icr", type=float, help="Batas kovenan interest coverage, mis. 2")
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--diam", action="store_true", help="Jangan cetak ringkasan")
    a = ap.parse_args(argv)
    cfg: dict = {}
    try:
        paket = baca(a.paket)
        if a.skenario:
            cfg = json.loads(a.skenario.read_text(encoding="utf-8"))
            if isinstance(cfg, list):
                cfg = {"skenario": cfg}
    except (PaketError, OSError, json.JSONDecodeError) as e:
        print(f"GAGAL MEMBACA: {e}", file=sys.stderr)
        return 1
    pilih = lambda cli, k, d=None: cli if cli is not None else cfg.get(k, d)  # noqa: E731
    try:
        h = analisa(paket, cfg.get("skenario"), int(pilih(a.horizon, "horizon_bulan", 3)),
                    pilih(a.kas_minimum, "kas_minimum"), float(pilih(a.plafon, "plafon_tersedia", 0) or 0),
                    pilih(a.batas_dscr, "batas_dscr"), pilih(a.batas_icr, "batas_icr"))
    except (AnalisaError, SkenarioError) as e:
        print(f"VALIDASI GAGAL: {e}", file=sys.stderr)
        return 2
    md = ke_md(h)
    if a.out_md:
        a.out_md.write_text(md, encoding="utf-8")
    if a.out_json:
        a.out_json.write_text(json.dumps(ke_json(h), ensure_ascii=False, indent=2), encoding="utf-8")
    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
