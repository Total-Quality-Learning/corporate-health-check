#!/usr/bin/env python3
"""Mesin analisa deterministik untuk skill laporan-analisa.

Masukan : paket data bulanan (lihat baca_paket.py)
Keluaran: "view model" JSON yang dirender templates/laporan.html.
Semua angka dihitung di sini. Teks penjelas dibentuk dari angka (bukan dari LLM).
Hanya pustaka standar Python (+ openpyxl lewat baca_paket untuk Excel).
"""
from __future__ import annotations

import calendar
import datetime as _dt

VERSI = "1.0.0"
BLN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
BLN_PANJANG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
               "November", "Desember"]


class AnalisaError(Exception):
    pass


# ================================================================ waktu ===
def geser(b: str, n: int) -> str:
    y, m = map(int, b.split("-"))
    t = y * 12 + (m - 1) + n
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def hari(b: str) -> int:
    y, m = map(int, b.split("-"))
    return calendar.monthrange(y, m)[1]


def lbl(b: str) -> str:
    return f"{BLN[int(b[5:]) - 1]} {b[:4]}"


def rentang(akhir: str, n: int) -> list[str]:
    return [geser(akhir, -i) for i in range(n - 1, -1, -1)]


# =============================================================== format ===
def _id(x: float, d: int) -> str:
    return f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")


class Fmt:
    def __init__(self, satuan: str, mata_uang: str = "IDR"):
        s = (satuan or "").lower()
        self.samaran = "samaran" in s
        self.juta = s.startswith("juta") and not self.samaran
        self.ribu = s.startswith("ribu") and not self.samaran
        self.rp = (mata_uang or "IDR").upper() == "IDR" and not self.samaran

    def uang(self, v, tanda=False):
        if v is None:
            return "-"
        neg = v < 0
        a = abs(v)
        if self.samaran:
            s = _id(a, 0) + " u"
        elif self.juta:
            s = (_id(a / 1000, 2) + " M") if a >= 1000 else (_id(a, 0) + " JT")
            s = ("Rp" if self.rp else "") + s
        elif self.ribu:
            s = (_id(a / 1_000_000, 2) + " M") if a >= 1_000_000 else (_id(a / 1000, 0) + " JT")
            s = ("Rp" if self.rp else "") + s
        else:
            s = _id(a, 0)
        if neg:
            return "-" + s
        return ("+" + s) if tanda and v > 0 else s

    def nilai(self, v, unit, tanda=False):
        if v is None:
            return "-"
        p = "+" if (tanda and v > 0) else ("-" if v < 0 else "")
        a = abs(v)
        if unit == "uang":
            return self.uang(v, tanda)
        if unit == "%":
            return f"{p}{_id(a, 1)}%"
        if unit == "poin":
            return f"{p}{_id(a, 1)} poin"
        if unit == "hari":
            return f"{p}{_id(a, 0)} hari"
        if unit == "x":
            return f"{p}{_id(a, 2)}x"
        if unit == "bulan":
            return f"{p}{_id(a, 1)} bulan"
        return f"{p}{_id(a, 1)}"

    def delta(self, cur, ref, unit):
        """Teks selisih + persen (untuk uang) atau poin/hari/x."""
        if cur is None or ref is None:
            return "-"
        d = cur - ref
        if unit == "uang":
            t = self.uang(d, True)
            if ref > 0 and abs(d / ref) <= 3:  # persen > 300% dari basis kecil membingungkan pembaca
                t += f" ({'+' if d >= 0 else '-'}{_id(abs(d / ref * 100), 1)}%)"
            elif ref > 0:
                t += " (lebih dari 3x)" if d > 0 else ""
            return t
        if unit == "%":
            return self.nilai(d, "poin", True)
        return self.nilai(d, unit, True)


# ================================================================ data ====
class Data:
    def __init__(self, paket: dict):
        self.p = paket
        self.lr = paket["laba_rugi"]
        self.n = paket["neraca"]
        self.ak = paket["arus_kas"]
        self.bulan_lr = sorted({b for v in self.lr.values() for b in v})
        if not self.bulan_lr:
            raise AnalisaError("Sheet LabaRugi tidak berisi angka.")
        info = paket.get("info", {})
        self.aktif = info.get("bulan_aktif") or self.bulan_lr[-1]
        if self.aktif not in self.bulan_lr:
            raise AnalisaError(f"bulan_aktif {self.aktif} tidak ada di LabaRugi.")
        self.ada = set(self.bulan_lr)

    def L(self, k, b):
        return self.lr.get(k, {}).get(b, 0.0) or 0.0

    def N(self, k, b):
        return self.n.get(k, {}).get(b, 0.0) or 0.0

    def A(self, k, b):
        return self.ak.get(k, {}).get(b, 0.0) or 0.0

    def lengkap(self, months):
        return months is not None and all(b in self.ada for b in months)

    def neraca_ada(self, b):
        return b in self.n.get("kas", {})

    # --------------------------------------------------------- per bulan
    def hpp(self, b):
        return sum(self.L(k, b) for k in ("hpp_bahan", "hpp_upah", "hpp_overhead", "hpp_penyusutan"))

    def beban_usaha(self, b):
        return self.L("beban_penjualan", b) + self.L("beban_umum_adm", b) + self.L("beban_penyusutan_usaha", b)

    def ebit(self, b):
        return self.L("pendapatan", b) - self.hpp(b) - self.beban_usaha(b)

    def penyusutan(self, b):
        return self.L("hpp_penyusutan", b) + self.L("beban_penyusutan_usaha", b)

    def laba_hitung(self, b):
        return self.ebit(b) + self.L("pendapatan_beban_lain", b) - self.L("beban_bunga", b) - self.L("beban_pajak", b)

    # --------------------------------------------------------- neraca
    def bs(self, b):
        N = lambda k: self.N(k, b)  # noqa: E731
        d = {}
        d["kas"] = N("kas")
        d["piutang"] = N("piutang_usaha_bruto") - N("cadangan_kerugian_piutang")
        d["persediaan"] = N("persediaan_bahan_baku") + N("persediaan_barang_dalam_proses") + N("persediaan_barang_jadi")
        d["dimuka"] = N("uang_muka_dan_dibayar_dimuka")
        d["aset_lancar"] = d["kas"] + d["piutang"] + d["persediaan"] + d["dimuka"]
        d["aset_tetap"] = N("aset_tetap_perolehan") - N("akumulasi_penyusutan")
        d["aset_tl_lain"] = N("aset_tidak_lancar_lain")
        d["total_aset"] = d["aset_lancar"] + d["aset_tetap"] + d["aset_tl_lain"]
        d["utang_usaha"] = N("utang_usaha")
        d["utang_bank"] = N("utang_bank_pendek") + N("bagian_lancar_utang_panjang") + N("utang_bank_panjang")
        d["ljp"] = (N("utang_usaha") + N("utang_bank_pendek") + N("bagian_lancar_utang_panjang") + N("beban_akrual")
                    + N("utang_pajak"))
        d["ljpg"] = N("utang_bank_panjang") + N("liabilitas_imbalan_kerja")
        d["total_liabilitas"] = d["ljp"] + d["ljpg"]
        d["ekuitas"] = N("modal_disetor") + N("saldo_laba")
        d["utang_bersih"] = d["utang_bank"] - d["kas"]
        d["modal_kerja"] = d["aset_lancar"] - d["ljp"]
        return d

    # --------------------------------------------------------- periode
    def periode(self, months, ltm_akhir=None):
        """Hitung semua angka untuk sekumpulan bulan berurutan."""
        if not self.lengkap(months):
            return None
        akhir = months[-1]
        awal = geser(months[0], -1)
        if not self.neraca_ada(akhir):
            return None
        S = lambda f: sum(f(b) for b in months)  # noqa: E731
        x = {"bulan": months, "hari": sum(hari(b) for b in months)}
        for k in ("penjualan_bruto", "potongan_dan_retur", "pendapatan", "hpp_bahan", "hpp_upah", "hpp_overhead",
                  "hpp_penyusutan", "beban_penjualan", "beban_umum_adm", "beban_penyusutan_usaha",
                  "pendapatan_beban_lain", "beban_bunga", "beban_pajak", "laba_bersih"):
            x[k] = S(lambda b: self.L(k, b))
        x["hpp"] = S(self.hpp)
        x["laba_kotor"] = x["pendapatan"] - x["hpp"]
        x["beban_usaha"] = S(self.beban_usaha)
        x["ebit"] = x["laba_kotor"] - x["beban_usaha"]
        x["penyusutan"] = S(self.penyusutan)
        x["ebitda"] = x["ebit"] + x["penyusutan"]
        x["ebt"] = x["ebit"] + x["pendapatan_beban_lain"] - x["beban_bunga"]
        for k in ("arus_kas_operasi", "belanja_modal", "penerimaan_pinjaman_panjang", "pembayaran_pinjaman_panjang",
                  "perubahan_utang_bank_pendek", "dividen"):
            x[k] = S(lambda b: self.A(k, b))
        x["fcf"] = x["arus_kas_operasi"] - x["belanja_modal"]
        bs1 = self.bs(akhir)
        x["bs"] = bs1
        if self.neraca_ada(awal):
            bs0 = self.bs(awal)
            x["bs_awal"] = bs0
            x["d_piutang"] = -(bs1["piutang"] - bs0["piutang"])
            x["d_persediaan"] = -(bs1["persediaan"] - bs0["persediaan"])
            x["d_utang_usaha"] = bs1["utang_usaha"] - bs0["utang_usaha"]
            x["d_lain"] = (x["arus_kas_operasi"] - x["laba_bersih"] - x["penyusutan"] - x["d_piutang"]
                           - x["d_persediaan"] - x["d_utang_usaha"])
        # LTM
        la = ltm_akhir or akhir
        ltm = rentang(la, 12)
        if self.lengkap(ltm):
            x["ltm"] = {"pendapatan": sum(self.L("pendapatan", b) for b in ltm),
                        "laba_bersih": sum(self.L("laba_bersih", b) for b in ltm),
                        "ebit": sum(self.ebit(b) for b in ltm),
                        "ebitda": sum(self.ebit(b) + self.penyusutan(b) for b in ltm),
                        "bunga": sum(self.L("beban_bunga", b) for b in ltm)}
        x["kpi"] = self.kpi(x)
        return x

    @staticmethod
    def bagi(a, b, k=1.0):
        if a is None or b is None or b == 0:
            return None
        return a / b * k

    def kpi(self, x):
        bs, h = x["bs"], x["hari"]
        B = self.bagi
        k = {}
        k["gross_margin"] = B(x["laba_kotor"], x["pendapatan"], 100)
        k["ebit_margin"] = B(x["ebit"], x["pendapatan"], 100)
        k["ebitda_margin"] = B(x["ebitda"], x["pendapatan"], 100)
        k["net_margin"] = B(x["laba_bersih"], x["pendapatan"], 100)
        k["opex_ratio"] = B(x["beban_usaha"], x["pendapatan"], 100)
        k["dso"] = B(bs["piutang"] * h, x["pendapatan"])
        k["dio"] = B(bs["persediaan"] * h, x["hpp"])
        k["dpo"] = B(bs["utang_usaha"] * h, x["hpp"])
        k["ccc"] = None if None in (k["dso"], k["dio"], k["dpo"]) else k["dso"] + k["dio"] - k["dpo"]
        k["current_ratio"] = B(bs["aset_lancar"], bs["ljp"])
        k["quick_ratio"] = B(bs["kas"] + bs["piutang"], bs["ljp"])
        k["cash_ratio"] = B(bs["kas"], bs["ljp"])
        k["der"] = B(bs["total_liabilitas"], bs["ekuitas"]) if bs["ekuitas"] > 0 else None
        k["bank_der"] = B(bs["utang_bank"], bs["ekuitas"]) if bs["ekuitas"] > 0 else None
        # konversi kas hanya bermakna bila laba cukup besar (>= 1% pendapatan)
        k["cash_conversion"] = (B(x["arus_kas_operasi"], x["laba_bersih"], 100)
                                if x["laba_bersih"] > 0.01 * max(x["pendapatan"], 1) else None)
        k["capex_dep"] = B(x["belanja_modal"], x["penyusutan"])
        lt = x.get("ltm")
        if lt:
            k["roe_ltm"] = B(lt["laba_bersih"], bs["ekuitas"], 100) if bs["ekuitas"] > 0 else None
            k["roa_ltm"] = B(lt["laba_bersih"], bs["total_aset"], 100)
            k["asset_turn"] = B(lt["pendapatan"], bs["total_aset"])
            k["eq_mult"] = B(bs["total_aset"], bs["ekuitas"]) if bs["ekuitas"] > 0 else None
            k["net_margin_ltm"] = B(lt["laba_bersih"], lt["pendapatan"], 100)
            k["net_debt_ebitda"] = B(bs["utang_bersih"], lt["ebitda"]) if lt["ebitda"] > 0 else None
            k["icr"] = B(lt["ebit"], lt["bunga"]) if lt["bunga"] > 0 else None
        return k


# ============================================================ KPI meta ====
# (key, nama, kelompok, unit, arah, aturan, waspada, kritis, definisi, rumus)
KPI_META = [
    ("gross_margin", "Margin laba kotor", "Profitabilitas", "%", "tinggi", "rel", 1.0, 2.5,
     "Sisa tiap Rp100 penjualan setelah biaya produksi / harga pokok.", "Laba kotor ÷ Pendapatan neto × 100%"),
    ("ebitda_margin", "Margin EBITDA", "Profitabilitas", "%", "tinggi", "rel", 1.0, 2.5,
     "Laba operasional sebelum bunga, pajak, dan penyusutan dibanding pendapatan.", "(Laba usaha + Penyusutan) ÷ Pendapatan × 100%"),
    ("net_margin", "Margin laba bersih", "Profitabilitas", "%", "tinggi", "rel", 1.0, 2.0,
     "Porsi pendapatan yang menjadi laba bersih.", "Laba bersih ÷ Pendapatan × 100%"),
    ("rev_growth", "Pertumbuhan pendapatan (YoY)", "Pertumbuhan", "%", "tinggi", "abs", 0.0, -5.0,
     "Perubahan pendapatan dibanding periode yang sama tahun lalu.", "(Pendapatan ÷ Pendapatan tahun lalu - 1) × 100%"),
    ("roe_ltm", "ROE (12 bulan)", "Profitabilitas & DuPont", "%", "tinggi", "abs", 10.0, 5.0,
     "Imbal hasil atas modal pemilik, laba 12 bulan terakhir.", "Laba bersih 12 bln ÷ Ekuitas akhir × 100%"),
    ("roa_ltm", "ROA (12 bulan)", "Profitabilitas & DuPont", "%", "tinggi", "abs", 5.0, 2.0,
     "Produktivitas seluruh aset menghasilkan laba.", "Laba bersih 12 bln ÷ Total aset akhir × 100%"),
    ("cash_conversion", "Konversi laba ke kas operasi", "Kas & modal kerja", "%", "tinggi", "abs", 75.0, 50.0,
     "Berapa bagian laba bersih yang benar-benar menjadi uang tunai dari operasi.", "Arus kas operasi ÷ Laba bersih × 100%"),
    ("dso", "Hari penagihan piutang (DSO)", "Kas & modal kerja", "hari", "rendah", "rel", 10.0, 20.0,
     "Rata-rata hari pelanggan membayar.", "Piutang usaha neto ÷ Pendapatan × hari periode"),
    ("dio", "Hari persediaan (DIO)", "Kas & modal kerja", "hari", "rendah", "rel", 10.0, 20.0,
     "Rata-rata hari barang tersimpan sebelum terjual.", "Persediaan ÷ HPP × hari periode"),
    ("dpo", "Hari pembayaran pemasok (DPO)", "Kas & modal kerja", "hari", "wajar", "rel", 10.0, 20.0,
     "Rata-rata hari perusahaan membayar pemasok; perubahan tajam ke dua arah perlu dicermati.", "Utang usaha ÷ HPP × hari periode"),
    ("ccc", "Siklus konversi kas (CCC)", "Kas & modal kerja", "hari", "rendah", "rel", 15.0, 30.0,
     "Berapa hari uang tertahan dari membeli bahan sampai dibayar pelanggan.", "DSO + DIO - DPO"),
    ("current_ratio", "Rasio lancar", "Likuiditas", "x", "tinggi", "abs", 1.5, 1.1,
     "Kemampuan membayar kewajiban < 1 tahun dengan aset lancar.", "Aset lancar ÷ Liabilitas jangka pendek"),
    ("quick_ratio", "Rasio cepat", "Likuiditas", "x", "tinggi", "abs", 1.0, 0.7,
     "Sama dengan rasio lancar tanpa mengandalkan persediaan.", "(Kas + Piutang usaha) ÷ Liabilitas jangka pendek"),
    ("net_debt_ebitda", "Utang bersih / EBITDA", "Solvabilitas", "x", "rendah", "abs", 2.5, 3.5,
     "Berapa tahun EBITDA dibutuhkan untuk melunasi utang bank bersih.", "(Utang bank - Kas) ÷ EBITDA 12 bln"),
    ("icr", "Interest coverage", "Solvabilitas", "x", "tinggi", "abs", 3.0, 1.5,
     "Berapa kali laba usaha menutup beban bunga.", "Laba usaha 12 bln ÷ Beban bunga 12 bln"),
]
KPI_KEYS = [m[0] for m in KPI_META]


def status_kpi(meta, cur, yoy, ambang):
    key, _, _, unit, arah, aturan, w, c = meta[:8]
    if key in ambang:
        a = ambang[key]
        aturan, w, c = "abs", a["waspada"], a["kritis"]
        arah = {"tinggi": "tinggi", "rendah": "rendah"}.get(a.get("arah") or "", arah)
    if cur is None:
        return "netral", ("-", "-")
    if aturan == "abs":
        if arah == "tinggi":
            st = "kritis" if cur < c else ("waspada" if cur < w else "aman")
            return st, (f"< {_id(w, 2 if unit == 'x' else 1)}{'x' if unit == 'x' else ('%' if unit == '%' else ' hari')}",
                        f"< {_id(c, 2 if unit == 'x' else 1)}{'x' if unit == 'x' else ('%' if unit == '%' else ' hari')}")
        st = "kritis" if cur > c else ("waspada" if cur > w else "aman")
        return st, (f"> {_id(w, 2 if unit == 'x' else 0)}{'x' if unit == 'x' else ('%' if unit == '%' else ' hari')}",
                    f"> {_id(c, 2 if unit == 'x' else 0)}{'x' if unit == 'x' else ('%' if unit == '%' else ' hari')}")
    # relatif terhadap tahun lalu
    sat = "poin" if unit == "%" else "hari"
    if yoy is None:
        return "netral", (f"Δ ≥ {_id(w, 1 if sat == 'poin' else 0)} {sat} vs thn lalu", f"Δ ≥ {_id(c, 1 if sat == 'poin' else 0)} {sat}")
    d = cur - yoy
    if arah == "tinggi":
        st = "kritis" if d <= -c else ("waspada" if d <= -w else "aman")
        teks = (f"turun ≥ {_id(w, 1)} {sat} YoY", f"turun ≥ {_id(c, 1)} {sat} YoY")
    elif arah == "rendah":
        st = "kritis" if d >= c else ("waspada" if d >= w else "aman")
        teks = (f"naik ≥ {_id(w, 0)} {sat} YoY", f"naik ≥ {_id(c, 0)} {sat} YoY")
    else:
        st = "kritis" if abs(d) >= c else ("waspada" if abs(d) >= w else "aman")
        teks = (f"berubah ≥ {_id(w, 0)} {sat} YoY", f"berubah ≥ {_id(c, 0)} {sat} YoY")
    return st, teks


def lebih_baik(arah, d):
    if d is None or d == 0 or arah in ("wajar", ""):
        return None
    return (d > 0) if arah == "tinggi" else (d < 0)


# =============================================================== analisa ==
class Analisa:
    def __init__(self, paket: dict, narasi: dict | None = None):
        self.p = paket
        self.d = Data(paket)
        info = paket.get("info", {})
        self.f = Fmt(info.get("satuan", "juta"), info.get("mata_uang", "IDR"))
        self.narasi = narasi or {}
        self.ambang = {a["kpi"]: a for a in (paket.get("ambang_kpi") or [])
                       if a.get("kpi") and a.get("waspada") is not None and a.get("kritis") is not None}
        self.gates = self.cek_gerbang()
        self.siapkan_periode()

    # ------------------------------------------------------------ gerbang
    def cek_gerbang(self):
        d = self.d
        hasil = []
        bl = d.bulan_lr
        tidak_seimbang = []
        for b in sorted(d.n.get("kas", {})):
            bs = d.bs(b)
            sel = bs["total_aset"] - bs["total_liabilitas"] - bs["ekuitas"]
            if abs(sel) > max(2.0, abs(bs["total_aset"]) * 0.001):
                tidak_seimbang.append(f"{lbl(b)} (selisih {self.f.uang(sel)})")
        hasil.append({"kode": "G1", "nama": "Neraca seimbang setiap bulan (aset = liabilitas + ekuitas)",
                      "status": "Gagal" if tidak_seimbang else "Lulus",
                      "catatan": ("Tidak seimbang: " + ", ".join(tidak_seimbang[:4])) if tidak_seimbang else
                      f"Seimbang pada {len(d.n.get('kas', {}))} titik neraca"})
        celah = [b for b in rentang(bl[-1], len(bl)) if b not in d.ada]
        hasil.append({"kode": "G2", "nama": "Kelengkapan bulan laba rugi (tanpa celah, ≥ 13 bulan)",
                      "status": "Lulus" if (not celah and len(bl) >= 13) else "Perhatian",
                      "catatan": f"{len(bl)} bulan ({lbl(bl[0])} - {lbl(bl[-1])})" + (f"; bulan hilang: {', '.join(lbl(x) for x in celah[:5])}" if celah else "")})
        beda_kas = []
        for b in bl:
            if "kas_akhir" in d.ak and b in d.ak["kas_akhir"] and d.neraca_ada(b):
                if abs(d.ak["kas_akhir"][b] - d.N("kas", b)) > 1:
                    beda_kas.append(lbl(b))
        hasil.append({"kode": "G3", "nama": "Kas akhir arus kas = kas di neraca",
                      "status": "Perhatian" if beda_kas else ("Lulus" if "kas_akhir" in d.ak else "Tidak diuji"),
                      "catatan": ("Berbeda: " + ", ".join(beda_kas[:5])) if beda_kas else "Cocok di semua bulan"})
        beda_ocf = []
        for b in bl:
            pb = geser(b, -1)
            if not d.neraca_ada(pb) or not d.neraca_ada(b) or b not in d.ak.get("arus_kas_operasi", {}):
                continue
            kas_hitung = (d.N("kas", pb) + d.A("arus_kas_operasi", b) - d.A("belanja_modal", b)
                          + d.A("penerimaan_pinjaman_panjang", b) - d.A("pembayaran_pinjaman_panjang", b)
                          + d.A("perubahan_utang_bank_pendek", b) - d.A("dividen", b))
            if abs(kas_hitung - d.N("kas", b)) > max(2.0, abs(d.N("kas", b)) * 0.002):
                beda_ocf.append(lbl(b))
        hasil.append({"kode": "G4", "nama": "Rekonsiliasi kas: kas awal + arus kas = kas akhir",
                      "status": "Perhatian" if beda_ocf else "Lulus",
                      "catatan": ("Tidak rekonsiliasi: " + ", ".join(beda_ocf[:5])) if beda_ocf else "Terekonsiliasi penuh"})
        beda_lb = [lbl(b) for b in bl if "laba_bersih" in d.lr and b in d.lr["laba_bersih"]
                   and abs(d.laba_hitung(b) - d.lr["laba_bersih"][b]) > 1]
        hasil.append({"kode": "G5", "nama": "Laba bersih = pendapatan - beban (dihitung ulang)",
                      "status": "Perhatian" if beda_lb else "Lulus",
                      "catatan": ("Berbeda: " + ", ".join(beda_lb[:5])) if beda_lb else "Cocok di semua bulan"})
        beda_sl = []
        for b in bl:
            pb = geser(b, -1)
            if d.neraca_ada(pb) and d.neraca_ada(b) and "saldo_laba" in d.n:
                if abs(d.N("saldo_laba", pb) + d.L("laba_bersih", b) - d.A("dividen", b) - d.N("saldo_laba", b)) > 1:
                    beda_sl.append(lbl(b))
        hasil.append({"kode": "G6", "nama": "Saldo laba bergerak sesuai laba bersih - dividen",
                      "status": "Perhatian" if beda_sl else "Lulus",
                      "catatan": ("Ada penyesuaian lain: " + ", ".join(beda_sl[:5])) if beda_sl else "Konsisten"})
        hasil.append({"kode": "G7", "nama": "Target / anggaran (RKAP) tersedia",
                      "status": "Lulus" if self.p.get("target") else "PERLU DATA",
                      "catatan": "Sheet Target terisi" if self.p.get("target") else "Pembanding target tidak bisa ditampilkan"})
        ops = [k for k in ("piutang_pelanggan", "penjualan_produk", "pemasok", "persediaan_rincian", "operasional",
                           "produksi_lini") if self.p.get(k)]
        hasil.append({"kode": "G8", "nama": "Data operasional tersedia",
                      "status": "Lulus" if len(ops) >= 5 else ("Sebagian" if ops else "PERLU DATA"),
                      "catatan": f"{len(ops)} dari 6 tabel operasional terisi"})
        if tidak_seimbang:
            raise AnalisaError("VALIDASI GAGAL (G1) - neraca tidak seimbang: " + ", ".join(tidak_seimbang[:6])
                               + ". Perbaiki data; laporan tidak disusun.")
        return hasil

    # ------------------------------------------------------------ periode
    def siapkan_periode(self):
        d, B = self.d, self.d.aktif
        m = int(B[5:])
        q_akhir = B if m % 3 == 0 else geser(B, -(m % 3))
        q = rentang(q_akhir, 3)
        qn = (int(q_akhir[5:]) - 1) // 3 + 1
        romawi = ["I", "II", "III", "IV"]
        ytd = [f"{B[:4]}-{i:02d}" for i in range(1, m + 1)]
        self.periode = {
            "month": {"label": f"{BLN_PANJANG[m - 1]} {B[:4]} (Bulanan)", "short": lbl(B),
                      "range": f"1-{hari(B)} {BLN_PANJANG[m - 1]} {B[:4]}", "months": [B],
                      "comps": {"prev": ([geser(B, -1)], f"{lbl(geser(B, -1))} (bulan lalu)"),
                                "yoy": ([geser(B, -12)], f"{lbl(geser(B, -12))} (tahun lalu)"),
                                "target": ([B], f"Target {lbl(B)}")}},
            "quarter": {"label": f"Triwulan {romawi[qn - 1]} {q_akhir[:4]} ({BLN[int(q[0][5:]) - 1]}-{BLN[int(q[-1][5:]) - 1]})",
                        "short": f"Q{qn} {q_akhir[:4]}",
                        "range": f"1 {BLN_PANJANG[int(q[0][5:]) - 1]} - {hari(q[-1])} {BLN_PANJANG[int(q[-1][5:]) - 1]} {q_akhir[:4]}",
                        "months": q,
                        "comps": {"prev": ([geser(b, -3) for b in q], f"Q{(qn - 2) % 4 + 1} {geser(q_akhir, -3)[:4]} (triwulan lalu)"),
                                  "yoy": ([geser(b, -12) for b in q], f"Q{qn} {int(q_akhir[:4]) - 1} (tahun lalu)"),
                                  "target": (q, f"Target Q{qn} {q_akhir[:4]}")}},
            "ytd": {"label": f"Tahun berjalan s.d. {BLN[m - 1]} {B[:4]} ({m} bulan)", "short": f"YTD {BLN[m - 1]} {B[:4]}",
                    "range": f"1 Januari - {hari(B)} {BLN_PANJANG[m - 1]} {B[:4]}", "months": ytd,
                    "comps": {"prev": (None, "Tidak berlaku untuk YTD"),
                              "yoy": ([geser(b, -12) for b in ytd], f"YTD {BLN[m - 1]} {int(B[:4]) - 1} (tahun lalu)"),
                              "target": (ytd, f"Target YTD {BLN[m - 1]} {B[:4]}")}},
        }
        self.hasil = {}
        for pid, P in self.periode.items():
            cur = d.periode(P["months"])
            if cur is None:
                raise AnalisaError(f"Data periode {P['label']} tidak lengkap.")
            comps = {}
            for cid, (months, label) in P["comps"].items():
                if cid == "target":
                    comps[cid] = self.periode_target(months)
                else:
                    comps[cid] = d.periode(months) if months else None
            self.hasil[pid] = {"cur": cur, "comps": comps}

    def periode_target(self, months):
        t = self.p.get("target")
        if not t or not all(b in t.get("pendapatan", {}) for b in months):
            return None
        S = lambda k: sum(t.get(k, {}).get(b, 0) for b in months) if all(b in t.get(k, {}) for b in months) else None  # noqa: E731
        x = {"pendapatan": S("pendapatan"), "laba_kotor": S("laba_kotor"), "beban_usaha": S("beban_usaha"),
             "laba_bersih": S("laba_bersih"), "target": True}
        x["ebit"] = (x["laba_kotor"] - x["beban_usaha"]) if None not in (x["laba_kotor"], x["beban_usaha"]) else None
        B = Data.bagi
        x["kpi"] = {"gross_margin": B(x["laba_kotor"], x["pendapatan"], 100),
                    "net_margin": B(x["laba_bersih"], x["pendapatan"], 100)}
        return x

    # ============================================================ KPI ====
    def tabel_kpi(self, pid, cid):
        H = self.hasil[pid]
        cur, comp, yoy = H["cur"], H["comps"].get(cid), H["comps"].get("yoy")
        rows = []
        for meta in KPI_META:
            key, nama, kel, unit, arah = meta[:5]
            v = self.nilai_kpi(key, cur, yoy)
            vy = self.nilai_kpi(key, yoy, None) if yoy else None
            vc = self.nilai_kpi(key, comp, None) if comp else None
            if key == "rev_growth" and cid in ("prev", "target"):
                vc = None
            st, (tw, tk) = status_kpi(meta, v, vy, self.ambang)
            d = (v - vc) if (v is not None and vc is not None) else None
            rows.append({"key": key, "nama": nama, "kel": kel, "cur": self.f.nilai(v, unit),
                         "comp": self.f.nilai(vc, unit) if comp else "PERLU DATA" if cid == "target" else "-",
                         "delta": self.f.nilai(d, "poin" if unit == "%" else unit, True) if d is not None else "-",
                         "baik": lebih_baik(arah, d), "status": st, "waspada": tw, "kritis": tk,
                         "def": meta[8], "rumus": meta[9],
                         "sumber_ambang": "Kebijakan perusahaan (sheet Ambang_KPI)" if key in self.ambang else
                         ("Relatif terhadap periode sama tahun lalu" if meta[5] == "rel" else "Ambang umum TQ Board Insight (bukan benchmark industri)"),
                         "v": v})
        return rows

    def nilai_kpi(self, key, x, yoy):
        if not x:
            return None
        if key == "rev_growth":
            if not yoy or not yoy.get("pendapatan"):
                return None
            return (x["pendapatan"] / yoy["pendapatan"] - 1) * 100
        return x.get("kpi", {}).get(key)

    def skor(self, rows):
        nilai = {"aman": 2, "waspada": 1, "kritis": 0}
        s = [nilai[r["status"]] for r in rows if r["status"] in nilai]
        if not s:
            return None, "-"
        pct = sum(s) / (2 * len(s)) * 100
        for batas, g in ((85, "A"), (75, "B+"), (65, "B"), (55, "C+"), (45, "C")):
            if pct >= batas:
                return round(pct), g
        return round(pct), "D"

    # ======================================================= laporan pos ==
    def baris_lr(self, x):
        # beban disajikan negatif: nilai lebih tinggi (kurang negatif) = lebih baik -> arah "tinggi"
        return [("Pendapatan neto", x["pendapatan"], "tinggi", True), ("Beban pokok penjualan", -x["hpp"], "tinggi", False),
                ("Laba kotor", x["laba_kotor"], "tinggi", True), ("Beban penjualan & distribusi", -x["beban_penjualan"], "tinggi", False),
                ("Beban umum & administrasi", -x["beban_umum_adm"], "tinggi", False),
                ("Penyusutan (di luar HPP)", -x["beban_penyusutan_usaha"], "", False),
                ("Laba usaha (EBIT)", x["ebit"], "tinggi", True), ("Penyusutan total", x["penyusutan"], "", False),
                ("EBITDA", x["ebitda"], "tinggi", True), ("Pendapatan (beban) lain-lain", x["pendapatan_beban_lain"], "tinggi", False),
                ("Beban bunga", -x["beban_bunga"], "tinggi", False), ("Laba sebelum pajak", x["ebt"], "tinggi", True),
                ("Beban pajak", -x["beban_pajak"], "", False), ("Laba bersih", x["laba_bersih"], "tinggi", True)]

    def baris_bs(self, x):
        b = x["bs"]
        return [("Kas & setara kas", b["kas"], "tinggi", False), ("Piutang usaha neto", b["piutang"], "rendah", False),
                ("Persediaan", b["persediaan"], "rendah", False), ("Uang muka & dibayar di muka", b["dimuka"], "", False),
                ("Aset lancar", b["aset_lancar"], "", True), ("Aset tetap neto", b["aset_tetap"], "", False),
                ("Total aset", b["total_aset"], "", True), ("Utang usaha", b["utang_usaha"], "", False),
                ("Utang bank (total)", b["utang_bank"], "rendah", False), ("Liabilitas jangka pendek", b["ljp"], "", True),
                ("Total liabilitas", b["total_liabilitas"], "rendah", True), ("Ekuitas", b["ekuitas"], "tinggi", True),
                ("Modal kerja (aset lancar - liab. pendek)", b["modal_kerja"], "", False),
                ("Utang bersih (utang bank - kas)", b["utang_bersih"], "rendah", False)]

    def baris_ak(self, x):
        r = [("Laba bersih", x["laba_bersih"], "tinggi", False), ("Penyusutan", x["penyusutan"], "", False)]
        if "d_piutang" in x:
            r += [("(Kenaikan) penurunan piutang", x["d_piutang"], "tinggi", False),
                  ("(Kenaikan) penurunan persediaan", x["d_persediaan"], "tinggi", False),
                  ("Kenaikan (penurunan) utang usaha", x["d_utang_usaha"], "", False),
                  ("Perubahan pos lain", x["d_lain"], "", False)]
        r += [("Arus kas operasi", x["arus_kas_operasi"], "tinggi", True), ("Belanja modal", -x["belanja_modal"], "", False),
              ("Arus kas bebas (operasi - belanja modal)", x["fcf"], "tinggi", True),
              ("Pinjaman jangka panjang: tarik - cicil", x["penerimaan_pinjaman_panjang"] - x["pembayaran_pinjaman_panjang"], "", False),
              ("Utang bank jangka pendek, neto", x["perubahan_utang_bank_pendek"], "", False),
              ("Dividen", -x["dividen"], "", False)]
        return r

    def tabel_pos(self, baris_cur, baris_comp, target=None):
        out = []
        for i, (nama, v, arah, tebal) in enumerate(baris_cur):
            vc = baris_comp[i][1] if baris_comp else None
            if target is not None:
                vc = target.get(nama)
            d = (v - vc) if (vc is not None) else None
            out.append({"nama": nama, "cur": self.f.uang(v), "comp": self.f.uang(vc) if vc is not None else "-",
                        "delta": self.f.delta(v, vc, "uang") if vc is not None else "-",
                        "baik": lebih_baik(arah, d), "tebal": tebal})
        return out

    def laporan_pos(self, pid, cid):
        H = self.hasil[pid]
        cur, comp = H["cur"], H["comps"].get(cid)
        if cid == "target":
            t = comp or {}
            peta = {"Pendapatan neto": t.get("pendapatan"), "Laba kotor": t.get("laba_kotor"),
                    "Laba usaha (EBIT)": t.get("ebit"), "Laba bersih": t.get("laba_bersih")}
            lr = self.tabel_pos(self.baris_lr(cur), None, peta if comp else {})
            return {"lr": lr, "neraca": self.tabel_pos(self.baris_bs(cur), None),
                    "ak": self.tabel_pos(self.baris_ak(cur), None)}
        return {"lr": self.tabel_pos(self.baris_lr(cur), self.baris_lr(comp) if comp else None),
                "neraca": self.tabel_pos(self.baris_bs(cur), self.baris_bs(comp) if comp else None),
                "ak": self.tabel_pos(self.baris_ak(cur), self.baris_ak(comp) if comp and "d_piutang" in comp else
                                     (self.baris_ak(comp) if comp else None))}

    def selisih(self, pid, cid):
        H = self.hasil[pid]
        cur, comp = H["cur"], H["comps"].get(cid)
        if not comp:
            return {"ada": False, "rows": [], "penjelas": []}
        pos = [("Pendapatan neto", "pendapatan", "tinggi"), ("Laba kotor", "laba_kotor", "tinggi"),
               ("Beban usaha", "beban_usaha", "rendah"), ("Laba usaha (EBIT)", "ebit", "tinggi"),
               ("Laba bersih", "laba_bersih", "tinggi")]
        if cid != "target":
            pos.insert(1, ("Beban pokok penjualan", "hpp", "rendah"))
            pos += [("Arus kas operasi", "arus_kas_operasi", "tinggi"), ("Beban bunga", "beban_bunga", "rendah")]
        rows, pen = [], []
        for nama, k, arah in pos:
            v, vc = cur.get(k), comp.get(k)
            if v is None or vc is None:
                continue
            d = v - vc
            rows.append({"nama": nama, "cur": self.f.uang(v), "comp": self.f.uang(vc), "delta": self.f.delta(v, vc, "uang"),
                         "baik": lebih_baik(arah, d), "abs": abs(d)})
        # penjelas: 3 selisih terbesar selain pendapatan/laba
        lab = {"pendapatan": "Pendapatan", "hpp": "Beban pokok penjualan", "beban_usaha": "Beban usaha",
               "arus_kas_operasi": "Arus kas operasi", "beban_bunga": "Beban bunga"}
        cands = []
        for k, nama in lab.items():
            if cur.get(k) is not None and comp.get(k) is not None:
                cands.append((abs(cur[k] - comp[k]), k, nama))
        for _, k, nama in sorted(cands, reverse=True)[:3]:
            d = cur[k] - comp[k]
            pen.append(f"{nama} {'naik' if d > 0 else 'turun'} {self.f.uang(abs(d))}"
                       + (f" ({_id(abs(d / comp[k] * 100), 1)}%)" if comp[k] else "") + f" dibanding {self.periode[pid]['comps'][cid][1]}.")
        if cid != "target" and cur["kpi"].get("gross_margin") is not None and comp.get("kpi", {}).get("gross_margin") is not None:
            dgm = cur["kpi"]["gross_margin"] - comp["kpi"]["gross_margin"]
            pen.append(f"Efek margin: perubahan margin kotor {self.f.nilai(dgm, 'poin', True)} setara "
                       f"{self.f.uang(dgm / 100 * cur['pendapatan'], True)} laba kotor pada pendapatan periode ini.")
        for r in rows:
            r.pop("abs", None)
        return {"ada": True, "rows": rows, "penjelas": pen}

    # ===================================================== seri bulanan ==
    def seri(self):
        d, B = self.d, self.d.aktif
        bl = [b for b in rentang(B, 22) if b in d.ada and d.neraca_ada(b)]
        S = {"label": [lbl(b) for b in bl], "pendapatan": [], "laba_bersih": [], "ocf": [], "gm": [], "nm": [],
             "dso": [], "dio": [], "ccc": [], "kas": []}
        for b in bl:
            x = d.periode([b])
            S["pendapatan"].append(round(x["pendapatan"], 1))
            S["laba_bersih"].append(round(x["laba_bersih"], 1))
            S["ocf"].append(round(x["arus_kas_operasi"], 1))
            S["kas"].append(round(x["bs"]["kas"], 1))
            for k, kk in (("gm", "gross_margin"), ("nm", "net_margin"), ("dso", "dso"), ("dio", "dio"), ("ccc", "ccc")):
                v = x["kpi"].get(kk)
                S[k].append(None if v is None else round(v, 2))
        return S

    def bulanan_tahun_ini(self):
        d, B = self.d, self.d.aktif
        bl = [f"{B[:4]}-{i:02d}" for i in range(1, int(B[5:]) + 1)]
        xs = [d.periode([b]) for b in bl]
        f = self.f
        defs = [("Pendapatan neto", lambda x: f.uang(x["pendapatan"])),
                ("Laba kotor", lambda x: f.uang(x["laba_kotor"])),
                ("Margin kotor", lambda x: f.nilai(x["kpi"]["gross_margin"], "%")),
                ("Beban usaha", lambda x: f.uang(x["beban_usaha"])),
                ("EBITDA", lambda x: f.uang(x["ebitda"])),
                ("Laba bersih", lambda x: f.uang(x["laba_bersih"])),
                ("Arus kas operasi", lambda x: f.uang(x["arus_kas_operasi"])),
                ("Kas akhir", lambda x: f.uang(x["bs"]["kas"])),
                ("Piutang usaha", lambda x: f.uang(x["bs"]["piutang"])),
                ("Persediaan", lambda x: f.uang(x["bs"]["persediaan"])),
                ("Utang usaha", lambda x: f.uang(x["bs"]["utang_usaha"])),
                ("Utang bank", lambda x: f.uang(x["bs"]["utang_bank"])),
                ("DSO (hari)", lambda x: f.nilai(x["kpi"]["dso"], "hari")),
                ("DIO (hari)", lambda x: f.nilai(x["kpi"]["dio"], "hari"))]
        dup = [("Margin laba bersih (bulan)", lambda x: f.nilai(x["kpi"]["net_margin"], "%")),
               ("Perputaran aset (disetahunkan)", lambda x: f.nilai(Data.bagi(x["pendapatan"] * 12, x["bs"]["total_aset"]), "x")),
               ("Pengali ekuitas (aset ÷ ekuitas)", lambda x: f.nilai(Data.bagi(x["bs"]["total_aset"], x["bs"]["ekuitas"]), "x")),
               ("ROE (disetahunkan)", lambda x: f.nilai(Data.bagi(x["laba_bersih"] * 12, x["bs"]["ekuitas"], 100), "%"))]
        return {"label": [BLN[int(b[5:]) - 1] for b in bl],
                "pos": [{"nama": n, "nilai": [fn(x) for x in xs]} for n, fn in defs],
                "dupont": [{"nama": n, "nilai": [fn(x) for x in xs]} for n, fn in dup]}

    # ========================================================== jembatan ==
    def jembatan(self, pid):
        x = self.hasil[pid]["cur"]
        if "d_piutang" not in x:
            return []
        items = [("Laba bersih", x["laba_bersih"]), ("Penyusutan", x["penyusutan"]), ("Piutang", x["d_piutang"]),
                 ("Persediaan", x["d_persediaan"]), ("Utang usaha", x["d_utang_usaha"]), ("Pos lain", x["d_lain"])]
        out = [{"label": a, "v": round(b, 1), "teks": self.f.uang(b, True)} for a, b in items]
        out.append({"label": "Arus kas operasi", "v": round(x["arus_kas_operasi"], 1), "teks": self.f.uang(x["arus_kas_operasi"]), "total": True})
        return out

    # ===================================================== operasional ===
    def ops_piutang(self):
        rows = self.p.get("piutang_pelanggan")
        kebutuhan = ("Daftar piutang per pelanggan dengan umur (0-30, 31-60, 61-90, >90 hari), batas kredit, dan status pihak berelasi",
                     "Biasanya tersedia jika penjualan, pengiriman, dan penagihan tercatat dalam satu sistem.")
        if not rows:
            return {"ada": False, "butuh": kebutuhan[0], "sumber": kebutuhan[1]}
        tot = {k: sum(r.get(k) or 0 for r in rows) for k in ("umur_0_30", "umur_31_60", "umur_61_90", "umur_90_plus", "penjualan_ytd")}
        total = sum(tot[k] for k in ("umur_0_30", "umur_31_60", "umur_61_90", "umur_90_plus")) or 1
        bucket = [("Belum jatuh tempo / 0-30 hari", tot["umur_0_30"], "aman"), ("31-60 hari", tot["umur_31_60"], "waspada"),
                  ("61-90 hari", tot["umur_61_90"], "waspada"), ("> 90 hari", tot["umur_90_plus"], "kritis")]
        pel = []
        for r in rows:
            saldo = sum(r.get(k) or 0 for k in ("umur_0_30", "umur_31_60", "umur_61_90", "umur_90_plus"))
            limit = r.get("batas_kredit") or 0
            pel.append({"nama": r.get("pelanggan"), "wilayah": r.get("wilayah") or "", "omzet": (r.get("penjualan_ytd") or 0) / (tot["penjualan_ytd"] or 1) * 100,
                        "saldo": saldo, "lewat90": r.get("umur_90_plus") or 0, "pakai_limit": saldo / limit * 100 if limit else None,
                        "berelasi": (str(r.get("terafiliasi") or "").lower().startswith("y")), "catatan": r.get("catatan") or "",
                        "margin": r.get("margin_kotor_pct")})
        pel.sort(key=lambda z: -z["saldo"])
        def gabungan(nama):
            n = (nama or "").lower()
            return n.startswith("lain") or "outlet" in n or "pelanggan kecil" in n
        top3 = sorted([z for z in pel if not gabungan(z["nama"])], key=lambda z: -z["omzet"])[:3]
        wil = {}
        for z in pel:
            w = wil.setdefault(z["wilayah"] or "-", {"omzet": 0, "saldo": 0, "lewat90": 0})
            w["omzet"] += z["omzet"]
            w["saldo"] += z["saldo"]
            w["lewat90"] += z["lewat90"]
        f = self.f
        return {"ada": True,
                "bucket": [{"nama": n, "v": v, "teks": f.uang(v), "porsi": f"{_id(v / total * 100, 1)}%", "status": s} for n, v, s in bucket],
                "lewat90": f.uang(tot["umur_90_plus"]), "lewat90_pct": _id(tot["umur_90_plus"] / total * 100, 1),
                "top3_nama": ", ".join(z["nama"] for z in top3), "top3_omzet": _id(sum(z["omzet"] for z in top3), 1),
                "pelanggan": [{"nama": z["nama"], "wilayah": z["wilayah"], "omzet": f"{_id(z['omzet'], 1)}%", "saldo": f.uang(z["saldo"]),
                               "lewat90": f.uang(z["lewat90"]) if z["lewat90"] else "-",
                               "limit": f"{_id(z['pakai_limit'], 0)}%" if z["pakai_limit"] else "-",
                               "limit_status": "kritis" if (z["pakai_limit"] or 0) > 100 else ("waspada" if (z["pakai_limit"] or 0) > 90 else "aman"),
                               "berelasi": "Ya" if z["berelasi"] else "Tidak",
                               "margin": f"{_id(z['margin'], 1)}%" if z["margin"] is not None else "-",
                               "catatan": z["catatan"]} for z in pel],
                "wilayah": [{"nama": k, "omzet": f"{_id(v['omzet'], 1)}%", "saldo": f.uang(v["saldo"]),
                             "lewat90": f.uang(v["lewat90"]) if v["lewat90"] else "-"}
                            for k, v in sorted(wil.items(), key=lambda kv: -kv[1]["omzet"])],
                "_raw": {"lewat90": tot["umur_90_plus"], "total": total, "pel": pel, "top3": top3}}

    def ops_produk(self, pid):
        rows = self.p.get("penjualan_produk")
        if not rows:
            return {"ada": False, "butuh": "Pendapatan & HPP per produk / kelompok produk per bulan",
                    "sumber": "Biasanya tersedia jika HPP dihitung per order/produk dari data produksi dan pembelian."}
        P = self.periode[pid]
        cur_m = set(P["months"])
        yoy_m = {geser(b, -12) for b in P["months"]}
        agg = {}
        for r in rows:
            per = r.get("periode")
            if per in cur_m or per in yoy_m:
                a = agg.setdefault(r["produk"], {"c": [0, 0, 0], "y": [0, 0, 0], "satuan": r.get("satuan") or ""})
                key = "c" if per in cur_m else "y"
                a[key][0] += r.get("pendapatan") or 0
                a[key][1] += r.get("hpp") or 0
                a[key][2] += r.get("volume") or 0
        tot = sum(a["c"][0] for a in agg.values()) or 1
        f = self.f
        out = []
        for nama, a in sorted(agg.items(), key=lambda kv: -kv[1]["c"][0]):
            gm = (a["c"][0] - a["c"][1]) / a["c"][0] * 100 if a["c"][0] else None
            gmy = (a["y"][0] - a["y"][1]) / a["y"][0] * 100 if a["y"][0] else None
            gr = (a["c"][0] / a["y"][0] - 1) * 100 if a["y"][0] else None
            out.append({"nama": nama, "pendapatan": f.uang(a["c"][0]), "porsi": f"{_id(a['c'][0] / tot * 100, 1)}%",
                        "tumbuh": f.nilai(gr, "%", True) if gr is not None else "-", "gm": f.nilai(gm, "%"),
                        "dgm": f.nilai(gm - gmy, "poin", True) if None not in (gm, gmy) else "-",
                        "dgm_v": (gm - gmy) if None not in (gm, gmy) else None,
                        "volume": f"{_id(a['c'][2], 1)} {a['satuan']}", "laba_kotor": f.uang(a["c"][0] - a["c"][1])})
        return {"ada": True, "rows": out}

    def ops_pemasok(self):
        rows = self.p.get("pemasok")
        if not rows:
            return {"ada": False, "butuh": "Pembelian per pemasok, perubahan harga, dan hari pembayaran",
                    "sumber": "Biasanya tersedia jika pembelian dan utang usaha tercatat per pemasok dalam satu sistem."}
        tot = sum(r.get("pembelian_ytd") or 0 for r in rows) or 1
        f = self.f
        out = [{"nama": r.get("pemasok"), "kategori": r.get("kategori") or "", "beli": f.uang(r.get("pembelian_ytd") or 0),
                "porsi": f"{_id((r.get('pembelian_ytd') or 0) / tot * 100, 1)}%",
                "harga": f.nilai(r.get("perubahan_harga_pct"), "%", True) if r.get("perubahan_harga_pct") is not None else "-",
                "harga_v": r.get("perubahan_harga_pct"),
                "dpo": f.nilai(r.get("dpo_hari"), "hari") if r.get("dpo_hari") is not None else "-", "catatan": r.get("catatan") or ""}
               for r in sorted(rows, key=lambda r: -(r.get("pembelian_ytd") or 0))]
        rata = sum((r.get("perubahan_harga_pct") or 0) * (r.get("pembelian_ytd") or 0) for r in rows) / tot
        return {"ada": True, "rows": out, "harga_rata": f.nilai(rata, "%", True), "harga_rata_v": rata,
                "top1_porsi": out[0]["porsi"] if out else "-"}

    def ops_persediaan(self):
        rows = self.p.get("persediaan_rincian")
        if not rows:
            return {"ada": False, "butuh": "Saldo persediaan per item/SKU/style dengan umur (0-30, 31-90, 91-180, >180 hari)",
                    "sumber": "Biasanya tersedia jika gudang, produksi, dan keuangan memakai data stok yang sama."}
        f = self.f
        jen = {}
        for r in rows:
            j = jen.setdefault(r.get("jenis") or "-", [0, 0, 0, 0, 0])
            for i, k in enumerate(("nilai", "umur_0_30", "umur_31_90", "umur_91_180", "umur_180_plus")):
                j[i] += r.get(k) or 0
        nama_j = {"bahan": "Bahan baku & kemasan", "wip": "Barang dalam proses (WIP)", "jadi": "Barang jadi / dagangan"}
        tua = sorted(rows, key=lambda r: -((r.get("umur_91_180") or 0) + (r.get("umur_180_plus") or 0)))
        total = sum(v[0] for v in jen.values()) or 1
        lebih90 = sum(v[3] + v[4] for v in jen.values())
        return {"ada": True, "lebih90": f.uang(lebih90), "lebih90_pct": _id(lebih90 / total * 100, 1),
                "jenis": [{"nama": nama_j.get(k, k), "nilai": f.uang(v[0]), "u1": f.uang(v[1]), "u2": f.uang(v[2]),
                           "u3": f.uang(v[3]), "u4": f.uang(v[4]),
                           "tua_pct": f"{_id((v[3] + v[4]) / v[0] * 100, 1)}%" if v[0] else "-"} for k, v in jen.items()],
                "tertua": [{"nama": r.get("item"), "jenis": nama_j.get(r.get("jenis"), r.get("jenis")), "nilai": f.uang(r.get("nilai") or 0),
                            "tua": f.uang((r.get("umur_91_180") or 0) + (r.get("umur_180_plus") or 0)),
                            "catatan": r.get("catatan") or ""} for r in tua[:6] if (r.get("umur_91_180") or 0) + (r.get("umur_180_plus") or 0) > 0],
                "_raw": {"lebih90": lebih90, "total": total, "tua": tua}}

    def ops_kpi(self):
        ops = self.p.get("operasional")
        if not ops:
            return {"ada": False, "butuh": "KPI operasional bulanan (utilisasi, output, reject/scrap, OEE, downtime, karyawan, dll.)",
                    "sumber": "Biasanya tersedia jika KPI produksi dicatat harian dan direkap otomatis."}
        B = self.d.aktif
        bl = rentang(B, 6)
        out = []
        for k, v in ops.items():
            n = v["nilai"]
            cur, ly = n.get(B), n.get(geser(B, -12))
            arah = v.get("arah") or ""
            st = "netral"
            if cur is not None and ly not in (None, 0) and arah in ("tinggi", "rendah"):
                ch = (cur - ly) / abs(ly) * 100
                buruk = -ch if arah == "tinggi" else ch
                st = "kritis" if buruk >= 15 else ("waspada" if buruk >= 5 else "aman")
            out.append({"kode": k, "nama": v["uraian"], "satuan": v["satuan"], "status": st,
                        "nilai": [("-" if n.get(b) is None else _id(n[b], 1 if abs(n[b]) < 100 else 0)) for b in bl],
                        "ly": "-" if ly is None else _id(ly, 1 if abs(ly) < 100 else 0),
                        "seri": [n.get(b) for b in rentang(B, 22)], "cur_v": cur, "ly_v": ly})
        return {"ada": True, "label": [lbl(b) for b in bl], "rows": out}

    def ops_lini(self):
        rows = self.p.get("produksi_lini")
        if not rows:
            return {"ada": False, "butuh": "Rencana vs realisasi produksi, WIP, reject, dan utilisasi per lini/gudang",
                    "sumber": "Biasanya tersedia jika perencanaan dan pencatatan produksi harian terhubung."}
        out = []
        rata_rej = sum(r.get("reject_pct") or 0 for r in rows) / len(rows)
        for r in rows:
            ren, rea = r.get("rencana") or 0, r.get("realisasi") or 0
            capai = rea / ren * 100 if ren else None
            tanda = []
            if capai is not None and capai > 110:
                tanda.append("produksi melebihi rencana")
            if capai is not None and capai < 85:
                tanda.append("jauh di bawah rencana")
            if (r.get("reject_pct") or 0) > rata_rej * 1.5:
                tanda.append("reject tinggi")
            if (r.get("utilisasi_pct") or 100) < 50:
                tanda.append("utilisasi rendah")
            out.append({"nama": r.get("lini"), "rencana": _id(ren, 1 if ren < 100 else 0), "realisasi": _id(rea, 1 if rea < 100 else 0),
                        "satuan": r.get("satuan") or "", "capai": f"{_id(capai, 0)}%" if capai is not None else "-",
                        "wip": _id(r.get("wip") or 0, 1), "reject": f"{_id(r.get('reject_pct') or 0, 1)}%",
                        "util": f"{_id(r.get('utilisasi_pct') or 0, 0)}%", "tanda": ", ".join(tanda),
                        "status": "kritis" if len(tanda) >= 2 else ("waspada" if tanda else "aman"), "catatan": r.get("catatan") or ""})
        return {"ada": True, "rows": out}

    # ============================================================ cerita ==
    def cerita(self, ops):
        H = self.hasil["ytd"]
        x, y = H["cur"], H["comps"].get("yoy")
        f = self.f
        k = x["kpi"]
        ky = y["kpi"] if y else {}
        m = self.hasil["month"]["cur"]
        cand = []
        P = self.periode["ytd"]["short"]

        def add(sev, skor, kind, judul, fakta, penyebab, opsi, butuh, dampak=None, jenis=""):
            cand.append({"sev": sev, "skor": skor, "kind": kind, "judul": judul, "fakta": fakta, "penyebab": penyebab,
                         "opsi": opsi, "butuh": butuh, "dampak": dampak, "jenis": jenis})

        pp, pr, pl = ops["piutang"], ops["persediaan"], ops["lini"]
        # 1. laba belum jadi kas
        cc = k.get("cash_conversion")
        konv = x["arus_kas_operasi"] / x["laba_bersih"] * 100 if x["laba_bersih"] > 0 else None
        if konv is not None and konv < 75:
            cc = konv if cc is None else cc
            sev = "kritis" if konv < 50 else "waspada"
            fakta = (f"Laba bersih {P} {f.uang(x['laba_bersih'])}, tetapi arus kas operasi {f.uang(x['arus_kas_operasi'])} "
                     f"(konversi {f.nilai(cc, '%') if cc >= 0 else 'negatif'}). Bulan {lbl(self.d.aktif)}: laba "
                     f"{f.uang(m['laba_bersih'])}, kas operasi {f.uang(m['arus_kas_operasi'])}.")
            if "d_piutang" in x:
                fakta += (f" Sejak awal tahun piutang menyerap {f.uang(max(-x['d_piutang'], 0))} dan persediaan "
                          f"{f.uang(max(-x['d_persediaan'], 0))}.")
            if pp["ada"]:
                pen = (f"Dari data piutang: {pp['lewat90']} ({pp['lewat90_pct']}%) lewat 90 hari; tiga pelanggan terbesar "
                       f"({pp['top3_nama']}) menyumbang {pp['top3_omzet']}% omzet.")
            else:
                pen = "PERLU DATA: penyebab tidak bisa dipastikan dari laporan keuangan, butuh umur piutang per pelanggan dan status order-to-cash."
            add(sev, 100 - (cc or -100), f"Kualitas laba | konversi kas {f.nilai(cc, '%') if cc >= 0 else 'negatif'}",
                "Laba belum menjadi kas", fakta, pen,
                ["Tinjau mingguan 10 piutang & 10 stok terbesar di rapat direksi",
                 "Susun proyeksi kas 13 minggu dan tetapkan batas kas minimum"],
                "Umur piutang per pelanggan; siklus order-kirim-tagih-bayar; proyeksi kas mingguan",
                f.uang(x["laba_bersih"] - x["arus_kas_operasi"]), "kas")
        # 2. piutang
        if y and k.get("dso") is not None and ky.get("dso") is not None and k["dso"] - ky["dso"] >= 10:
            dd = k["dso"] - ky["dso"]
            lepas = dd / x["hari"] * x["pendapatan"]
            fakta = (f"DSO naik dari {f.nilai(ky['dso'], 'hari')} menjadi {f.nilai(k['dso'], 'hari')}; piutang usaha "
                     f"{f.uang(x['bs']['piutang'])}. Jika DSO kembali ke level tahun lalu, kas sekitar {f.uang(lepas)} dapat dilepas.")
            if pp["ada"]:
                raw = pp["_raw"]
                terlewat = [z for z in raw["pel"] if z["lewat90"] > 0]
                terlewat.sort(key=lambda z: -z["lewat90"])
                nama = ", ".join(f"{z['nama']} ({f.uang(z['lewat90'])})" for z in terlewat[:3])
                rel = [z["nama"] for z in terlewat if z["berelasi"]]
                lim = [z["nama"] for z in raw["pel"] if (z["pakai_limit"] or 0) > 100]
                pen = f"Tunggakan >90 hari terpusat pada {nama}."
                if lim:
                    pen += f" Batas kredit terlampaui: {', '.join(lim[:3])}."
                if rel:
                    pen += f" Termasuk pihak berelasi: {', '.join(rel[:2])}, perlu kebijakan kredit khusus."
            else:
                pen = "PERLU DATA: tidak terlihat pelanggan mana yang terlambat dari laporan keuangan, butuh umur piutang per pelanggan dan tanggal kirim vs invoice."
            add("kritis" if dd >= 20 else "waspada", dd * 3, f"Eksposur kas | piutang {f.uang(x['bs']['piutang'])}",
                "Piutang semakin lama tertagih", fakta, pen,
                ["Bekukan pengiriman kredit baru untuk akun lewat jatuh tempo > 60 hari",
                 "Tetapkan dan tegakkan batas kredit per pelanggan", "Percepat penerbitan invoice setelah pengiriman"],
                "Umur piutang per pelanggan; batas kredit; tanggal kirim → invoice → bayar", f.uang(lepas), "piutang")
        # 3. persediaan
        if y and k.get("dio") is not None and ky.get("dio") is not None and k["dio"] - ky["dio"] >= 10:
            dd = k["dio"] - ky["dio"]
            lepas = dd / x["hari"] * x["hpp"]
            fakta = (f"DIO naik dari {f.nilai(ky['dio'], 'hari')} menjadi {f.nilai(k['dio'], 'hari')}; persediaan "
                     f"{f.uang(x['bs']['persediaan'])} (tahun lalu {f.uang(y['bs']['persediaan'])}). "
                     f"Jika DIO kembali ke level tahun lalu, kas sekitar {f.uang(lepas)} dapat dilepas.")
            pen_list = []
            if pr["ada"]:
                tua = pr["_raw"]["tua"][0]
                pen_list.append(f"{pr['lebih90']} ({pr['lebih90_pct']}%) persediaan berumur > 90 hari; terbesar: {tua['item']}"
                                + (f", {tua['catatan']}" if tua.get("catatan") else "") + ".")
            if pl["ada"]:
                lebih = [r for r in pl["rows"] if "melebihi" in r["tanda"]]
                if lebih:
                    pen_list.append(f"{lebih[0]['nama']} berproduksi {lebih[0]['capai']} dari rencana" +
                                    (f" ({lebih[0]['catatan']})" if lebih[0]["catatan"] else "") + ".")
            pen = " ".join(pen_list) if pen_list else ("PERLU DATA: laporan keuangan hanya menunjukkan total persediaan, "
                                                       "butuh stok per SKU/style, umur stok, dan WIP per lini.")
            add("kritis" if dd >= 20 else "waspada", dd * 3, f"Modal kerja | persediaan {f.uang(x['bs']['persediaan'])}",
                "Persediaan menumpuk", fakta, pen,
                ["Hentikan sementara produksi/pembelian di luar order pasti", "Program penjualan stok berumur > 90 hari",
                 "Tinjau kebijakan minimum order bahan"],
                "Stok per SKU & umur; WIP per lini; rencana vs realisasi produksi", f.uang(lepas), "persediaan")
        # 4. margin
        if y and k.get("gross_margin") is not None and ky.get("gross_margin") is not None:
            dgm = k["gross_margin"] - ky["gross_margin"]
            if dgm <= -1.0:
                hilang = -dgm / 100 * x["pendapatan"]
                fakta = (f"Margin kotor {P} {f.nilai(k['gross_margin'], '%')} dibanding {f.nilai(ky['gross_margin'], '%')} "
                         f"tahun lalu ({f.nilai(dgm, 'poin', True)}), setara laba kotor sekitar {f.uang(hilang)} yang hilang.")
                pen_list = []
                if ops["produk"]["ada"]:
                    rr = [r for r in ops["produk"]["rows"] if r["dgm_v"] is not None]
                    if rr:
                        w = min(rr, key=lambda r: r["dgm_v"])
                        pen_list.append(f"Penurunan terbesar pada {w['nama']} (margin {w['gm']}, {w['dgm']}).")
                if ops["pemasok"]["ada"]:
                    top = max(ops["pemasok"]["rows"], key=lambda r: r["harga_v"] or 0)
                    pen_list.append(f"Harga beli rata-rata naik {ops['pemasok']['harga_rata']}; tertinggi {top['nama']} ({top['harga']}).")
                if ops["kpi"]["ada"]:
                    for r in ops["kpi"]["rows"]:
                        if r["status"] in ("kritis", "waspada") and any(s in r["kode"] for s in ("reject", "waste", "scrap", "oee", "potong")):
                            pen_list.append(f"{r['nama']}: {r['ly']} → {r['nilai'][-1]} {r['satuan']} (tahun lalu → kini).")
                            break
                pen = " ".join(pen_list) if pen_list else ("PERLU DATA: HPP di laporan keuangan adalah satu angka total, butuh "
                                                           "margin per produk, harga beli bahan, dan biaya reject/rework per proses.")
                add("kritis" if dgm <= -2.5 else "waspada", -dgm * 12, f"Profitabilitas | margin kotor {f.nilai(dgm, 'poin', True)}",
                    "Margin kotor tergerus", fakta, pen,
                    ["Hitung margin per produk/order dan tinjau harga jual produk bermargin terendah",
                     "Ukur biaya reject/rework/waste dalam rupiah per proses", "Negosiasikan kontrak harga bahan utama"],
                    "Margin per produk; harga beli per bahan; reject/waste per proses", f.uang(hilang), "margin")
        # 5. beban usaha / efisiensi
        if y and y["beban_usaha"] and y["pendapatan"]:
            go = (x["beban_usaha"] / y["beban_usaha"] - 1) * 100
            gp = (x["pendapatan"] / y["pendapatan"] - 1) * 100
            if go - gp >= 5:
                pen = "PERLU DATA: butuh KPI produktivitas (output per jam, utilisasi, downtime) dan rincian biaya per aktivitas."
                if ops["kpi"]["ada"]:
                    rr = [r for r in ops["kpi"]["rows"] if r["status"] in ("kritis", "waspada")]
                    if rr:
                        pen = "Indikator operasional memburuk: " + "; ".join(f"{r['nama']} {r['ly']} → {r['nilai'][-1]} {r['satuan']}" for r in rr[:3]) + "."
                add("kritis" if go - gp >= 10 else "waspada", (go - gp) * 4, "Efisiensi | beban usaha",
                    "Beban usaha tumbuh lebih cepat dari pendapatan",
                    f"Beban usaha {P} {f.nilai(go, '%', True)} sementara pendapatan {f.nilai(gp, '%', True)} (YoY).", pen,
                    ["Tetapkan anggaran beban usaha berbasis volume", "Pantau KPI produktivitas harian per lini"],
                    "KPI produktivitas harian; biaya per aktivitas", None, "efisiensi")
        # 6. utang & bunga
        icr, nde = k.get("icr"), k.get("net_debt_ebitda")
        ub0 = y["bs"]["utang_bank"] if y else None
        naik = (x["bs"]["utang_bank"] / ub0 - 1) * 100 if ub0 else None
        if (icr is not None and icr < 3) or (nde is not None and nde > 2.5) or (naik is not None and naik >= 25):
            sev = "kritis" if ((icr is not None and icr < 1.5) or (nde is not None and nde > 3.5)) else "waspada"
            fakta = (f"Utang bank {f.uang(x['bs']['utang_bank'])}" + (f" ({f.nilai(naik, '%', True)} YoY)" if naik is not None else "")
                     + f"; interest coverage {f.nilai(icr, 'x')}, utang bersih/EBITDA {f.nilai(nde, 'x')} (12 bulan).")
            serap_mk = max(-x.get("d_piutang", 0), 0) + max(-x.get("d_persediaan", 0), 0) - max(x.get("d_utang_usaha", 0), 0)
            pen = "PERLU DATA: tidak terlihat order, pelanggan, atau aset mana yang menyerap dana pinjaman."
            if (naik is None or naik > 0) and serap_mk > x["belanja_modal"]:
                # utang terutama menutup modal kerja
                if pp["ada"] or pr["ada"]:
                    pen = (f"Sejak awal tahun modal kerja menyerap sekitar {f.uang(serap_mk)}, lebih besar dari belanja modal "
                           f"{f.uang(x['belanja_modal'])}; pinjaman menutup kas yang tertahan di piutang"
                           + (f" (lewat 90 hari {pp['lewat90']})" if pp["ada"] else "") + " dan persediaan"
                           + (f" (berumur > 90 hari {pr['lebih90']})" if pr["ada"] else "") + ".")
            elif ops["kpi"]["ada"]:
                ut = [r for r in ops["kpi"]["rows"] if "utilisasi" in r["kode"] and r["status"] != "aman"]
                if ut:
                    pen = (f"{ut[0]['nama']} hanya {ut[0]['nilai'][-1]}{'%' if ut[0]['satuan'] == '%' else ' ' + ut[0]['satuan']}"
                           ", aset yang dibiayai pinjaman belum menghasilkan.")
            add(sev, 60 if sev == "kritis" else 30, f"Solvabilitas | ICR {f.nilai(icr, 'x')}", "Beban utang membatasi ruang gerak",
                fakta, pen, ["Susun rencana penurunan utang & uji covenant bulanan",
                             "Prioritaskan utilisasi aset yang sudah dibiayai sebelum investasi baru"],
                "Penggunaan fasilitas kredit; utilisasi aset yang dibiayai; proyeksi kas", None, "utang")
        # 7. konsentrasi pelanggan
        if pp["ada"] and float(pp["top3_omzet"].replace(",", ".")) >= 40:
            add("waspada", 20, f"Konsentrasi | {pp['top3_omzet']}% omzet di 3 pelanggan", "Ketergantungan pada sedikit pelanggan",
                f"{pp['top3_nama']} menyumbang {pp['top3_omzet']}% penjualan YTD.",
                "Posisi tawar termin & harga melemah bila satu pelanggan besar menunda bayar atau mengurangi order.",
                ["Tetapkan batas porsi omzet & piutang per pelanggan", "Diversifikasi ke segmen dengan termin lebih pendek"],
                "Penjualan & piutang per pelanggan", None, "konsentrasi")
        # 8. kabar baik
        if y and y["pendapatan"]:
            gp = (x["pendapatan"] / y["pendapatan"] - 1) * 100
            if gp >= 3:
                pen = ""
                if ops["produk"]["ada"]:
                    best = max(ops["produk"]["rows"], key=lambda r: float(r["tumbuh"].replace("%", "").replace("+", "").replace("-", "-").replace(",", ".")) if r["tumbuh"] != "-" else -999)
                    pen = f"Pertumbuhan tertinggi: {best['nama']} ({best['tumbuh']})."
                add("aman", 5, f"Pertumbuhan | pendapatan {f.nilai(gp, '%', True)}", "Penjualan tumbuh",
                    f"Pendapatan {P} {f.uang(x['pendapatan'])} ({f.nilai(gp, '%', True)} dibanding tahun lalu).",
                    pen or "Rincian pendorong pertumbuhan per produk/pelanggan butuh data penjualan per produk.",
                    ["Pastikan pertumbuhan tidak dibeli dengan termin lebih panjang atau potongan lebih besar"],
                    "Penjualan per produk & pelanggan", None, "tumbuh")
        urut = {"kritis": 0, "waspada": 1, "aman": 2}
        cand.sort(key=lambda c: (urut[c["sev"]], -c["skor"]))
        out = cand[:5]
        for i, c in enumerate(out, 1):
            c["id"] = f"C-{i:02d}"
            c["judul"] = f"{i}. {c['judul']}"
        return out

    # ===================================================== uji ketahanan ==
    def uji_ketahanan(self):
        d, B = self.d, self.d.aktif
        bl = rentang(B, 3)
        x = d.periode(bl)
        f = self.f
        rata = lambda k: x[k] / 3  # noqa: E731
        rev, bahan, sell = rata("pendapatan"), rata("hpp_bahan"), rata("beban_penjualan")
        tetap = rata("hpp_upah") + rata("hpp_overhead") + rata("beban_umum_adm")
        ebitda = rata("ebitda")
        kas = x["bs"]["kas"]
        kas_min = tetap
        dasar = (x["arus_kas_operasi"] - x["belanja_modal"] - x["pembayaran_pinjaman_panjang"]) / 3
        cm = (rev - bahan - sell) / rev if rev else 0
        ltm = x.get("ltm", {})
        debt = x["bs"]["utang_bank"]
        sk = []

        def tambah(nama, besaran, d_kas_3bln, ebitda_baru, rev_baru, catatan=""):
            akhir = kas + 3 * dasar + d_kas_3bln
            st = "kritis" if akhir < kas_min else ("waspada" if akhir < 1.5 * kas_min else "aman")
            sk.append({"nama": nama, "besaran": besaran, "ebitda_m": f.nilai(ebitda_baru / rev_baru * 100 if rev_baru else None, "%"),
                       "dampak": f.uang(d_kas_3bln, True), "kas_akhir": f.uang(akhir),
                       "tahan": f.nilai(akhir / tetap if tetap else None, "bulan"),
                       "status": st, "catatan": catatan})

        tambah("Dasar (tren 3 bulan terakhir berlanjut)", "Tanpa guncangan", 0, ebitda, rev)
        tambah("Penjualan turun 15% selama 3 bulan", "Permintaan -15%", -0.15 * rev * cm * 3, ebitda - 0.15 * rev * cm, rev * 0.85)
        tambah("Harga bahan naik 10% tanpa kenaikan harga jual", "Bahan +10%", -0.10 * bahan * 3, ebitda - 0.10 * bahan, rev)
        tambah("DSO molor 15 hari & penjualan turun 10%", "Penagihan +15 hari", -(15 / 30.4 * rev) - 0.10 * rev * cm * 3,
               ebitda - 0.10 * rev * cm, rev * 0.9, "Tambahan piutang tertahan dihitung sekali")
        if debt > 0 and ltm:
            icr_baru = Data.bagi(ltm["ebit"], ltm["bunga"] + 0.02 * debt)
            tambah("Suku bunga naik 2 poin", "Bunga +2 poin", -0.02 * debt / 12 * 3, ebitda, rev,
                   f"Interest coverage menjadi {f.nilai(icr_baru, 'x')}")
        return {"rows": sk, "kas_kini": f.uang(kas), "kas_min": f.uang(kas_min), "dasar": f.uang(dasar, True),
                "asumsi": ("Rata-rata 3 bulan terakhir, tanpa penarikan pinjaman baru. Kas minimum = 1 bulan beban kas tetap (upah, overhead, beban umum). "
                           "Arus kas dasar per bulan = arus kas operasi - belanja modal - cicilan pinjaman. "
                           "Biaya variabel = bahan + beban penjualan. Perhitungan deterministik sederhana, bukan simulasi.")}

    def kas13(self):
        """Ilustrasi 13 minggu dari rata-rata 3 bulan komponen kas aktual (termasuk perubahan modal kerja)."""
        d, B = self.d, self.d.aktif
        x = d.periode(rentang(B, 3))
        f = self.f
        dp = x.get("d_piutang", 0) / 3
        dinv = x.get("d_persediaan", 0) / 3
        dap = x.get("d_utang_usaha", 0) / 3
        masuk_bln = x["pendapatan"] / 3 + dp
        pemasok_bln = x["hpp_bahan"] / 3 - dinv - dap
        operasi_bln = (x["hpp_upah"] + x["hpp_overhead"] + x["beban_penjualan"] + x["beban_umum_adm"] + x["beban_pajak"]
                       - x["pendapatan_beban_lain"] + x["belanja_modal"]) / 3
        utang_bln = (x["pembayaran_pinjaman_panjang"] + x["beban_bunga"]) / 3
        kas_b = kas_l = x["bs"]["kas"]
        tetap = (x["hpp_upah"] + x["hpp_overhead"] + x["beban_umum_adm"]) / 3
        rows = []
        for w in range(1, 14):
            masuk, keluar_p, keluar_o = masuk_bln * 12 / 52, pemasok_bln * 12 / 52, operasi_bln * 12 / 52
            utang = utang_bln if w % 4 == 0 else 0
            net = masuk - keluar_p - keluar_o - utang
            kas_b += net
            kas_l += net - 0.10 * masuk
            rows.append({"mg": f"M-{w:02d}", "masuk": f.uang(masuk), "pemasok": f.uang(keluar_p), "operasi": f.uang(keluar_o + utang),
                         "neto": f.uang(net, True), "akhir": f.uang(kas_b), "akhir_rendah": f.uang(kas_l),
                         "v_b": round(kas_b, 1), "v_l": round(kas_l, 1)})
        return {"rows": rows, "kas_min": round(tetap, 1), "kas_min_teks": f.uang(tetap),
                "asumsi": ("Ilustrasi: pola rata-rata 3 bulan terakhir diteruskan 13 minggu. Penerimaan = pendapatan dikurangi "
                           "kenaikan piutang; bayar pemasok = bahan + kenaikan persediaan - kenaikan utang usaha; operasi = upah, "
                           "overhead, beban usaha, pajak, belanja modal. Cicilan & bunga tiap 4 minggu. Skenario rendah: penerimaan "
                           "-10%. Tanpa pinjaman baru. Bukan proyeksi resmi; perlu jadwal penagihan & pembayaran aktual.")}

    # ========================================================== lampiran ==
    def lampiran(self, pid, cid):
        H = self.hasil[pid]
        x, c = H["cur"], H["comps"].get(cid)
        f = self.f
        if c and c.get("target"):
            c = None
        bs, k = x["bs"], x["kpi"]
        lt = x.get("ltm", {})
        U = f.uang
        g = []

        def baris(nama, v, vc, unit, rumus, hitung):
            return {"nama": nama, "cur": f.nilai(v, unit), "comp": f.nilai(vc, unit) if c else "-",
                    "delta": f.delta(v, vc, unit) if (c and v is not None and vc is not None) else "-",
                    "rumus": rumus, "hitung": hitung}

        cb = c["bs"] if c else {}
        ck = c["kpi"] if c else {}
        g.append(("1. Posisi keuangan", [
            baris("Kas & setara kas", bs["kas"], cb.get("kas"), "uang", "Saldo kas + bank akhir periode", f"{U(bs['kas'])}"),
            baris("Piutang usaha neto", bs["piutang"], cb.get("piutang"), "uang", "Piutang bruto - cadangan kerugian", U(bs["piutang"])),
            baris("Persediaan", bs["persediaan"], cb.get("persediaan"), "uang", "Bahan + WIP + barang jadi", U(bs["persediaan"])),
            baris("Aset lancar", bs["aset_lancar"], cb.get("aset_lancar"), "uang", "Kas + piutang + persediaan + uang muka", U(bs["aset_lancar"])),
            baris("Aset tetap neto", bs["aset_tetap"], cb.get("aset_tetap"), "uang", "Harga perolehan - akumulasi penyusutan", U(bs["aset_tetap"])),
            baris("Total aset", bs["total_aset"], cb.get("total_aset"), "uang", "Aset lancar + aset tidak lancar", U(bs["total_aset"])),
            baris("Utang bank", bs["utang_bank"], cb.get("utang_bank"), "uang", "Pendek + bagian lancar + jangka panjang", U(bs["utang_bank"])),
            baris("Total liabilitas", bs["total_liabilitas"], cb.get("total_liabilitas"), "uang", "Liabilitas pendek + panjang", U(bs["total_liabilitas"])),
            baris("Ekuitas", bs["ekuitas"], cb.get("ekuitas"), "uang", "Modal disetor + saldo laba", U(bs["ekuitas"])),
            baris("Modal kerja", bs["modal_kerja"], cb.get("modal_kerja"), "uang", "Aset lancar - liabilitas jangka pendek",
                  f"{U(bs['aset_lancar'])} - {U(bs['ljp'])} = {U(bs['modal_kerja'])}"),
            baris("Utang bersih", bs["utang_bersih"], cb.get("utang_bersih"), "uang", "Utang bank - kas",
                  f"{U(bs['utang_bank'])} - {U(bs['kas'])} = {U(bs['utang_bersih'])}"),
        ]))
        pend = x["pendapatan"]
        g.append(("2. Profitabilitas & DuPont", [
            baris("Margin laba kotor", k["gross_margin"], ck.get("gross_margin"), "%", "Laba kotor ÷ Pendapatan × 100%",
                  f"{U(x['laba_kotor'])} ÷ {U(pend)} × 100% = {f.nilai(k['gross_margin'], '%')}"),
            baris("Margin laba usaha (EBIT)", k["ebit_margin"], ck.get("ebit_margin"), "%", "Laba usaha ÷ Pendapatan × 100%",
                  f"{U(x['ebit'])} ÷ {U(pend)} × 100% = {f.nilai(k['ebit_margin'], '%')}"),
            baris("Margin EBITDA", k["ebitda_margin"], ck.get("ebitda_margin"), "%", "(Laba usaha + Penyusutan) ÷ Pendapatan × 100%",
                  f"({U(x['ebit'])} + {U(x['penyusutan'])}) ÷ {U(pend)} × 100% = {f.nilai(k['ebitda_margin'], '%')}"),
            baris("Margin laba bersih", k["net_margin"], ck.get("net_margin"), "%", "Laba bersih ÷ Pendapatan × 100%",
                  f"{U(x['laba_bersih'])} ÷ {U(pend)} × 100% = {f.nilai(k['net_margin'], '%')}"),
            baris("Rasio beban usaha", k["opex_ratio"], ck.get("opex_ratio"), "%", "Beban usaha ÷ Pendapatan × 100%",
                  f"{U(x['beban_usaha'])} ÷ {U(pend)} × 100% = {f.nilai(k['opex_ratio'], '%')}"),
            baris("ROE (12 bulan)", k.get("roe_ltm"), ck.get("roe_ltm"), "%", "Laba bersih 12 bln ÷ Ekuitas × 100%",
                  f"{U(lt.get('laba_bersih'))} ÷ {U(bs['ekuitas'])} × 100% = {f.nilai(k.get('roe_ltm'), '%')}" if lt else "-"),
            baris("ROA (12 bulan)", k.get("roa_ltm"), ck.get("roa_ltm"), "%", "Laba bersih 12 bln ÷ Total aset × 100%",
                  f"{U(lt.get('laba_bersih'))} ÷ {U(bs['total_aset'])} × 100% = {f.nilai(k.get('roa_ltm'), '%')}" if lt else "-"),
            baris("DuPont: margin bersih 12 bln", k.get("net_margin_ltm"), ck.get("net_margin_ltm"), "%", "Laba bersih 12 bln ÷ Pendapatan 12 bln",
                  f"{U(lt.get('laba_bersih'))} ÷ {U(lt.get('pendapatan'))}" if lt else "-"),
            baris("DuPont: perputaran aset", k.get("asset_turn"), ck.get("asset_turn"), "x", "Pendapatan 12 bln ÷ Total aset",
                  f"{U(lt.get('pendapatan'))} ÷ {U(bs['total_aset'])} = {f.nilai(k.get('asset_turn'), 'x')}" if lt else "-"),
            baris("DuPont: pengali ekuitas", k.get("eq_mult"), ck.get("eq_mult"), "x", "Total aset ÷ Ekuitas",
                  f"{U(bs['total_aset'])} ÷ {U(bs['ekuitas'])} = {f.nilai(k.get('eq_mult'), 'x')}"),
        ]))
        g.append(("3. Likuiditas", [
            baris("Rasio lancar", k["current_ratio"], ck.get("current_ratio"), "x", "Aset lancar ÷ Liabilitas jangka pendek",
                  f"{U(bs['aset_lancar'])} ÷ {U(bs['ljp'])} = {f.nilai(k['current_ratio'], 'x')}"),
            baris("Rasio cepat", k["quick_ratio"], ck.get("quick_ratio"), "x", "(Kas + Piutang) ÷ Liabilitas jangka pendek",
                  f"({U(bs['kas'])} + {U(bs['piutang'])}) ÷ {U(bs['ljp'])} = {f.nilai(k['quick_ratio'], 'x')}"),
            baris("Rasio kas", k["cash_ratio"], ck.get("cash_ratio"), "x", "Kas ÷ Liabilitas jangka pendek",
                  f"{U(bs['kas'])} ÷ {U(bs['ljp'])} = {f.nilai(k['cash_ratio'], 'x')}"),
        ]))
        h = x["hari"]
        g.append(("4. Aktivitas & modal kerja", [
            baris("DSO", k["dso"], ck.get("dso"), "hari", "Piutang ÷ Pendapatan × hari periode",
                  f"{U(bs['piutang'])} ÷ {U(pend)} × {h} = {f.nilai(k['dso'], 'hari')}"),
            baris("DIO", k["dio"], ck.get("dio"), "hari", "Persediaan ÷ HPP × hari periode",
                  f"{U(bs['persediaan'])} ÷ {U(x['hpp'])} × {h} = {f.nilai(k['dio'], 'hari')}"),
            baris("DPO", k["dpo"], ck.get("dpo"), "hari", "Utang usaha ÷ HPP × hari periode",
                  f"{U(bs['utang_usaha'])} ÷ {U(x['hpp'])} × {h} = {f.nilai(k['dpo'], 'hari')}"),
            baris("Siklus konversi kas", k["ccc"], ck.get("ccc"), "hari", "DSO + DIO - DPO",
                  f"{f.nilai(k['dso'], 'hari')} + {f.nilai(k['dio'], 'hari')} - {f.nilai(k['dpo'], 'hari')} = {f.nilai(k['ccc'], 'hari')}"),
        ]))
        g.append(("5. Solvabilitas", [
            baris("DER (liabilitas ÷ ekuitas)", k["der"], ck.get("der"), "x", "Total liabilitas ÷ Ekuitas",
                  f"{U(bs['total_liabilitas'])} ÷ {U(bs['ekuitas'])} = {f.nilai(k['der'], 'x')}"),
            baris("Utang bank ÷ ekuitas", k["bank_der"], ck.get("bank_der"), "x", "Utang bank ÷ Ekuitas",
                  f"{U(bs['utang_bank'])} ÷ {U(bs['ekuitas'])} = {f.nilai(k['bank_der'], 'x')}"),
            baris("Utang bersih ÷ EBITDA", k.get("net_debt_ebitda"), ck.get("net_debt_ebitda"), "x", "(Utang bank - Kas) ÷ EBITDA 12 bln",
                  f"{U(bs['utang_bersih'])} ÷ {U(lt.get('ebitda'))} = {f.nilai(k.get('net_debt_ebitda'), 'x')}" if lt else "-"),
            baris("Interest coverage", k.get("icr"), ck.get("icr"), "x", "Laba usaha 12 bln ÷ Beban bunga 12 bln",
                  f"{U(lt.get('ebit'))} ÷ {U(lt.get('bunga'))} = {f.nilai(k.get('icr'), 'x')}" if lt else "-"),
        ]))
        g.append(("6. Arus kas & kualitas laba", [
            baris("Arus kas operasi", x["arus_kas_operasi"], c.get("arus_kas_operasi") if c else None, "uang", "Dari laporan arus kas", U(x["arus_kas_operasi"])),
            baris("Belanja modal", x["belanja_modal"], c.get("belanja_modal") if c else None, "uang", "Perolehan aset tetap", U(x["belanja_modal"])),
            baris("Arus kas bebas", x["fcf"], c.get("fcf") if c else None, "uang", "Arus kas operasi - belanja modal",
                  f"{U(x['arus_kas_operasi'])} - {U(x['belanja_modal'])} = {U(x['fcf'])}"),
            baris("Konversi laba ke kas", k.get("cash_conversion"), ck.get("cash_conversion"), "%", "Arus kas operasi ÷ Laba bersih × 100%",
                  f"{U(x['arus_kas_operasi'])} ÷ {U(x['laba_bersih'])} × 100% = {f.nilai(k.get('cash_conversion'), '%')}"),
            baris("Belanja modal ÷ penyusutan", k.get("capex_dep"), ck.get("capex_dep"), "x", "Belanja modal ÷ Penyusutan",
                  f"{U(x['belanja_modal'])} ÷ {U(x['penyusutan'])} = {f.nilai(k.get('capex_dep'), 'x')}"),
        ]))
        return [{"grup": a, "rows": b} for a, b in g]

    # =========================================================== rakit ===
    def rakit(self) -> dict:
        info = self.p.get("info", {})
        ops = {"piutang": self.ops_piutang(), "pemasok": self.ops_pemasok(), "persediaan": self.ops_persediaan(),
               "kpi": self.ops_kpi(), "lini": self.ops_lini(), "produk": self.ops_produk("ytd")}
        cerita = self.cerita(ops)
        kpi, skor, putusan, pos, sel, lamp, jem, produk = {}, {}, {}, {}, {}, {}, {}, {}
        for pid in self.periode:
            kpi[pid], pos[pid], sel[pid], lamp[pid] = {}, {}, {}, {}
            for cid in ("prev", "yoy", "target"):
                kpi[pid][cid] = self.tabel_kpi(pid, cid)
                pos[pid][cid] = self.laporan_pos(pid, cid)
                sel[pid][cid] = self.selisih(pid, cid)
                lamp[pid][cid] = self.lampiran(pid, cid)
            sk, gr = self.skor(kpi[pid]["yoy"])
            skor[pid] = {"nilai": sk, "grade": gr}
            putusan[pid] = self.putusan(pid, kpi[pid]["yoy"], gr)
            jem[pid] = self.jembatan(pid)
            produk[pid] = self.ops_produk(pid)
        for o in ops.values():
            o.pop("_raw", None)
        ops["produk"] = produk
        risiko = []
        for c in cerita:
            if c["sev"] in ("kritis", "waspada"):
                risiko.append({"id": f"R-{len(risiko) + 1:02d}", "judul": c["judul"].split(". ", 1)[-1], "sev": c["sev"],
                               "dampak": c["dampak"] or "-", "mitigasi": c["opsi"][0], "pic": "[DIISI DIREKSI]"})
        rencana = []
        for c in cerita:
            if c["sev"] in ("kritis", "waspada"):
                rencana.append({"no": f"KEP-{len(rencana) + 1:02d}", "prio": "P1" if c["sev"] == "kritis" else "P2",
                                "pemicu": c["kind"], "isu": c["judul"].split(". ", 1)[-1], "opsi": " / ".join(c["opsi"][:2]),
                                "dampak": (f"sekitar {c['dampak']}" if c["dampak"] else "-"), "pemilik": "[DIISI DIREKSI]",
                                "tenggat": "[DIISI DIREKSI]", "data": c["butuh"]})
        kelengkapan = [
            {"bagian": "KPI, laporan pos, selisih, lampiran rasio", "sumber": "LK bulanan", "ada": True},
            {"bagian": "Target / anggaran", "sumber": "Sheet Target", "ada": bool(self.p.get("target"))},
            {"bagian": "Piutang per pelanggan & wilayah", "sumber": "Piutang_Pelanggan", "ada": ops["piutang"]["ada"]},
            {"bagian": "Margin per produk", "sumber": "Penjualan_Produk", "ada": produk["ytd"]["ada"]},
            {"bagian": "Pemasok & harga beli", "sumber": "Pemasok", "ada": ops["pemasok"]["ada"]},
            {"bagian": "Umur persediaan per item", "sumber": "Persediaan_Rincian", "ada": ops["persediaan"]["ada"]},
            {"bagian": "KPI operasional bulanan", "sumber": "Operasional", "ada": ops["kpi"]["ada"]},
            {"bagian": "Produksi per lini / gudang", "sumber": "Produksi_Lini", "ada": ops["lini"]["ada"]},
        ]
        jml_ops = sum(1 for z in kelengkapan[2:] if z["ada"])
        sat = info.get("satuan", "juta")
        return {
            "meta": {"perusahaan": info.get("perusahaan", "(tanpa nama)"), "industri": info.get("industri", ""),
                     "satuan": "unit samaran" if self.f.samaran else f"{sat} {'Rupiah' if self.f.rp else info.get('mata_uang', '')}".strip(),
                     "bulan_aktif": lbl(self.d.aktif), "sumber": info.get("sumber", ""),
                     "dibuat": _dt.date.today().strftime("%d-%m-%Y"), "versi": f"susun_laporan / analisa.py v{VERSI}",
                     "tingkat_data": "LK + data operasional" if jml_ops >= 4 else ("LK + sebagian data operasional" if jml_ops else "LK bulanan saja"),
                     "ops_terisi": jml_ops, "samaran": self.f.samaran,
                     "label_data": ("DATA DISAMARKAN" if self.f.samaran else
                                    ("DATA FIKTIF | PELATIHAN" if "FIKTIF" in str(info.get("perusahaan", "")).upper()
                                     else "RAHASIA | INTERNAL DIREKSI"))},
            "periode": {pid: {"label": P["label"], "short": P["short"], "range": P["range"],
                              "comps": {cid: {"label": lab, "ada": self.hasil[pid]["comps"].get(cid) is not None}
                                        for cid, (_, lab) in P["comps"].items()}} for pid, P in self.periode.items()},
            "skor": skor, "putusan": putusan, "kpi": kpi, "cerita": cerita, "jembatan": jem, "seri": self.seri(),
            "bulanan": self.bulanan_tahun_ini(), "pos": pos, "selisih": sel, "ops": ops,
            "uji": self.uji_ketahanan(), "kas13": self.kas13(), "risiko": risiko, "rencana": rencana,
            "lampiran": lamp, "gerbang": self.gates, "kelengkapan": kelengkapan,
            "narasi": {"surat": self.narasi.get("surat_direksi") or "", "catatan": self.narasi.get("catatan_analis") or ""},
        }

    def putusan(self, pid, rows, grade):
        H = self.hasil[pid]
        x, y = H["cur"], H["comps"].get("yoy")
        f = self.f
        bag = []
        if y and y["pendapatan"]:
            bag.append(f"pendapatan {f.nilai((x['pendapatan'] / y['pendapatan'] - 1) * 100, '%', True)} YoY")
        if y and y["laba_bersih"] > 0:
            bag.append(f"laba bersih {f.nilai((x['laba_bersih'] / y['laba_bersih'] - 1) * 100, '%', True)}")
        bag.append(f"arus kas operasi {f.uang(x['arus_kas_operasi'])}")
        kritis = [r["nama"] for r in rows if r["status"] == "kritis"]
        waspada = [r["nama"] for r in rows if r["status"] == "waspada"]
        s = f"{self.periode[pid]['short']}: " + ", ".join(bag) + "."
        if kritis:
            s += f" {len(kritis)} indikator kritis ({', '.join(kritis[:3])})."
        if waspada:
            s += f" {len(waspada)} waspada."
        if not kritis and not waspada:
            s += " Tidak ada indikator di zona waspada/kritis."
        return {"teks": s, "kritis": len(kritis), "waspada": len(waspada), "grade": grade}
