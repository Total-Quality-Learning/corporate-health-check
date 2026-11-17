#!/usr/bin/env python3
"""Hitung rasio keuangan secara deterministik dari LK format standar (JSON).

Pemakaian:
    python scripts/hitung_rasio.py lk.json --out-json rasio.json --out-md rasio.md

- Input  : JSON format standar (lihat references/skema-input.md).
- Output : ringkasan Markdown ke stdout; JSON lengkap ke --out-json (dipakai skill lain).
- Exit   : 0 = sukses, 1 = input tidak bisa dibaca / kolom wajib kosong,
           2 = validasi gagal (mis. neraca tidak seimbang) -> TIDAK ada rasio yang dihitung.

Hanya memakai pustaka standar Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERSI = "1.1.0"

WAJIB = {
    "neraca": ["kas_dan_setara_kas", "piutang_usaha", "persediaan", "total_aset_lancar", "total_aset",
               "utang_usaha", "total_liabilitas_jangka_pendek", "total_liabilitas", "total_ekuitas"],
    "laba_rugi": ["pendapatan", "beban_pokok_penjualan", "laba_bersih"],
    "arus_kas": ["arus_kas_operasi"],
}
# Pos beban yang harus positif. Jika negatif (gaya penyajian "(123)"), dibalik + peringatan.
POS_BEBAN = {
    "laba_rugi": ["beban_pokok_penjualan", "beban_penjualan", "beban_umum_administrasi", "beban_usaha",
                  "beban_bunga", "beban_pajak", "penyusutan"],
    "arus_kas": ["belanja_modal"],
}

POS_UTAMA = [  # (bagian, kunci, label)
    ("laba_rugi", "pendapatan", "Pendapatan"),
    ("laba_rugi", "laba_kotor", "Laba kotor"),
    ("laba_rugi", "beban_usaha", "Beban usaha"),
    ("laba_rugi", "laba_usaha", "Laba usaha"),
    ("laba_rugi", "laba_bersih", "Laba bersih"),
    ("arus_kas", "arus_kas_operasi", "Arus kas operasi"),
    ("arus_kas", "arus_kas_bebas", "Arus kas bebas (operasi - belanja modal)"),
    ("neraca", "kas_dan_setara_kas", "Kas dan setara kas"),
    ("neraca", "piutang_usaha", "Piutang usaha"),
    ("neraca", "persediaan", "Persediaan"),
    ("neraca", "utang_usaha", "Utang usaha"),
    ("neraca", "utang_bank_total", "Utang bank (pendek + panjang)"),
    ("neraca", "total_aset", "Total aset"),
    ("neraca", "total_ekuitas", "Total ekuitas"),
]

RASIO = [  # (kunci, label, kelompok, satuan, rumus)
    ("current_ratio", "Current ratio", "Likuiditas", "kali", "Aset lancar / Liabilitas jangka pendek"),
    ("quick_ratio", "Quick ratio", "Likuiditas", "kali", "(Aset lancar - Persediaan) / Liabilitas jangka pendek"),
    ("cash_ratio", "Rasio kas", "Likuiditas", "kali", "Kas dan setara kas / Liabilitas jangka pendek"),
    ("gross_margin", "Margin laba kotor", "Profitabilitas", "persen", "Laba kotor / Pendapatan"),
    ("operating_margin", "Margin laba usaha", "Profitabilitas", "persen", "Laba usaha / Pendapatan"),
    ("ebitda_margin", "Margin EBITDA", "Profitabilitas", "persen", "(Laba usaha + Penyusutan) / Pendapatan"),
    ("net_margin", "Margin laba bersih", "Profitabilitas", "persen", "Laba bersih / Pendapatan"),
    ("opex_ratio", "Rasio beban usaha", "Profitabilitas", "persen", "Beban usaha / Pendapatan"),
    ("effective_tax", "Tarif pajak efektif", "Profitabilitas", "persen", "Beban pajak / Laba sebelum pajak"),
    ("roa", "ROA", "Profitabilitas", "persen", "Laba bersih (disetahunkan) / Total aset"),
    ("roe", "ROE", "Profitabilitas", "persen", "Laba bersih (disetahunkan) / Total ekuitas"),
    ("equity_multiplier", "Pengali ekuitas (DuPont)", "Profitabilitas", "kali", "Total aset / Total ekuitas"),
    ("der", "DER (total liabilitas / ekuitas)", "Leverage", "kali", "Total liabilitas / Total ekuitas"),
    ("der_berbunga", "Utang bank / ekuitas", "Leverage", "kali", "(Utang bank pendek + panjang) / Total ekuitas"),
    ("debt_to_assets", "Liabilitas / aset", "Leverage", "persen", "Total liabilitas / Total aset"),
    ("net_debt_ebitda", "Utang bank bersih / EBITDA", "Leverage", "kali", "(Utang bank - Kas) / EBITDA (disetahunkan)"),
    ("interest_coverage", "Interest coverage", "Leverage", "kali", "Laba usaha / Beban bunga"),
    ("dio", "DIO (hari persediaan)", "Efisiensi", "hari", "Persediaan / Beban pokok penjualan x hari periode"),
    ("dso", "DSO (hari piutang)", "Efisiensi", "hari", "Piutang usaha / Pendapatan x hari periode"),
    ("dpo", "DPO (hari utang usaha)", "Efisiensi", "hari", "Utang usaha / Beban pokok penjualan x hari periode"),
    ("ccc", "Cash conversion cycle", "Efisiensi", "hari", "DIO + DSO - DPO"),
    ("inventory_turnover", "Perputaran persediaan", "Efisiensi", "kali", "HPP (disetahunkan) / Persediaan"),
    ("receivable_turnover", "Perputaran piutang", "Efisiensi", "kali", "Pendapatan (disetahunkan) / Piutang usaha"),
    ("asset_turnover", "Perputaran aset", "Efisiensi", "kali", "Pendapatan (disetahunkan) / Total aset"),
    ("cfo_to_ni", "Arus kas operasi / laba bersih", "Kualitas laba & kas", "kali", "Arus kas operasi / Laba bersih"),
    ("fcf_margin", "Margin arus kas bebas", "Kualitas laba & kas", "persen", "(Arus kas operasi - Belanja modal) / Pendapatan"),
    ("capex_to_dep", "Belanja modal / penyusutan", "Kualitas laba & kas", "kali", "Belanja modal / Penyusutan"),
    ("altman_z", "Skor Altman Z'' (indikatif)", "Kesehatan keuangan", "skor",
     "6,56 x (Aset lancar - Liab. pendek)/Aset + 3,26 x Saldo laba/Aset + 6,72 x Laba usaha/Aset + 1,05 x Ekuitas/Liabilitas"),
]


class GagalValidasi(Exception):
    pass


# ----------------------------------------------------------------- format ---
def fmt_angka(x, desimal=0):
    if x is None:
        return "-"
    s = f"{abs(x):,.{desimal}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return f"({s})" if x < 0 else s


def fmt_nilai(x, satuan):
    if x is None:
        return "-"
    tanda = "-" if x < 0 else ""
    if satuan == "persen":
        return tanda + fmt_angka(abs(x), 1) + "%"
    if satuan == "hari":
        return tanda + fmt_angka(abs(x), 0) + " hari"
    if satuan == "kali":
        return tanda + fmt_angka(abs(x), 2) + "x"
    if satuan == "skor":
        return tanda + fmt_angka(abs(x), 2)
    return fmt_angka(x, 0)


def fmt_perubahan(p, satuan):
    if not p:
        return "-"
    d = p.get("selisih")
    if d is None:
        return "-"
    tanda = "+" if d > 0 else ("-" if d < 0 else "sekitar ")
    if satuan == "persen":
        return f"{tanda}{fmt_angka(abs(d), 1)} poin"
    if satuan == "hari":
        return f"{tanda}{fmt_angka(abs(d), 0)} hari"
    if satuan == "kali":
        return f"{tanda}{fmt_angka(abs(d), 2)}x"
    if satuan == "skor":
        return f"{tanda}{fmt_angka(abs(d), 2)}"
    pct = p.get("persen")
    teks = f"{tanda}{fmt_angka(abs(d), 0)}"
    if pct is not None:
        teks += f" ({'+' if pct > 0 else ('-' if pct < 0 else '')}{fmt_angka(abs(pct), 1)}%)"
    elif p.get("catatan"):
        teks += f" ({p['catatan']})"
    return teks


# ------------------------------------------------------------- pemrosesan ---
def angka(v):
    """Terima int/float atau string angka sederhana. None/'' -> None."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        raise ValueError("nilai boolean bukan angka")
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if s in ("", "-"):
        return None
    # Format Indonesia "1.234.567,89" atau internasional "1,234,567.89"
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif s.count(",") > 1:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    x = float(s)
    return -x if neg else x


def muat(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"File tidak ditemukan: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"JSON tidak valid ({path}): {e}")
    if not isinstance(data.get("periode"), list) or len(data["periode"]) < 1:
        raise SystemExit("Kunci 'periode' wajib berupa daftar label periode, urut dari terlama. Contoh: [\"2024\", \"2025\"]")
    return data


def normalisasi(data: dict, peringatan: list) -> dict:
    periode = [str(p) for p in data["periode"]]
    hasil = {"neraca": {}, "laba_rugi": {}, "arus_kas": {}}
    for bagian in hasil:
        sumber = data.get(bagian) or {}
        for kunci, nilai in sumber.items():
            if not isinstance(nilai, dict):
                raise SystemExit(f"{bagian}.{kunci} harus berupa objek {{periode: angka}}.")
            baris = {}
            for p in periode:
                try:
                    baris[p] = angka(nilai.get(p))
                except ValueError:
                    raise SystemExit(f"{bagian}.{kunci}[{p}] bukan angka: {nilai.get(p)!r}")
            if kunci in POS_BEBAN.get(bagian, []):
                for p, v in baris.items():
                    if v is not None and v < 0:
                        baris[p] = -v
                        peringatan.append(f"{bagian}.{kunci} periode {p} bernilai negatif; dianggap beban "
                                          f"dan diubah menjadi positif ({fmt_angka(-v)}).")
            hasil[bagian][kunci] = baris
    # kolom wajib
    kosong = []
    for bagian, daftar in WAJIB.items():
        for k in daftar:
            for p in periode:
                if hasil[bagian].get(k, {}).get(p) is None:
                    kosong.append(f"{bagian}.{k} [{p}]")
    if kosong:
        raise SystemExit("Kolom wajib belum terisi:\n  - " + "\n  - ".join(kosong))
    return hasil


def turunkan(lk: dict, periode: list) -> None:
    """Lengkapi pos turunan yang tidak disajikan."""
    n, lr, ak = lk["neraca"], lk["laba_rugi"], lk["arus_kas"]

    def isi(bagian, kunci, fn):
        baris = bagian.setdefault(kunci, {})
        for p in periode:
            if baris.get(p) is None:
                try:
                    baris[p] = fn(p)
                except (TypeError, KeyError):  # komponen tidak disajikan / None
                    baris[p] = None

    isi(lr, "laba_kotor", lambda p: lr["pendapatan"][p] - lr["beban_pokok_penjualan"][p])
    isi(lr, "beban_usaha", lambda p: lr["beban_penjualan"][p] + lr["beban_umum_administrasi"][p])
    isi(lr, "laba_usaha", lambda p: lr["laba_kotor"][p] - lr["beban_usaha"][p])
    isi(n, "utang_bank_total",
        lambda p: (n.get("utang_bank_jangka_pendek", {}).get(p) or 0) + (n.get("utang_bank_jangka_panjang", {}).get(p) or 0)
        if (n.get("utang_bank_jangka_pendek", {}).get(p) is not None or n.get("utang_bank_jangka_panjang", {}).get(p) is not None)
        else None)
    isi(ak, "arus_kas_bebas", lambda p: ak["arus_kas_operasi"][p] - ak["belanja_modal"][p])


def toleransi(nilai):
    return max(2.0, abs(nilai) * 0.001)


def validasi(lk: dict, periode: list, peringatan: list) -> None:
    n, lr, ak = lk["neraca"], lk["laba_rugi"], lk["arus_kas"]
    error = []
    for p in periode:
        ta = n["total_aset"][p]
        tl, te = n["total_liabilitas"][p], n["total_ekuitas"][p]
        if abs(ta - (tl + te)) > toleransi(ta):
            error.append(f"[{p}] Neraca tidak seimbang: total aset {fmt_angka(ta)} vs liabilitas + ekuitas "
                         f"{fmt_angka(tl + te)} (selisih {fmt_angka(ta - tl - te)}).")
        tle = n.get("total_liabilitas_dan_ekuitas", {}).get(p)
        if tle is not None and abs(ta - tle) > toleransi(ta):
            error.append(f"[{p}] Total aset {fmt_angka(ta)} tidak sama dengan total liabilitas dan ekuitas "
                         f"yang disajikan {fmt_angka(tle)}.")
        tal = n["total_aset_lancar"][p]
        if tal > ta + toleransi(ta):
            error.append(f"[{p}] Aset lancar ({fmt_angka(tal)}) lebih besar dari total aset ({fmt_angka(ta)}).")
        if n["total_liabilitas_jangka_pendek"][p] > tl + toleransi(tl):
            error.append(f"[{p}] Liabilitas jangka pendek lebih besar dari total liabilitas.")
        if lr["pendapatan"][p] <= 0:
            error.append(f"[{p}] Pendapatan nol/negatif; rasio margin dan hari tidak bisa dihitung.")

        # --- peringatan (tidak menghentikan perhitungan)
        komponen = [n[k][p] for k in ("kas_dan_setara_kas", "piutang_usaha", "persediaan")]
        lain = n.get("aset_lancar_lainnya", {}).get(p)
        if lain is not None:
            jml = sum(komponen) + lain
            if abs(jml - tal) > toleransi(tal):
                peringatan.append(f"[{p}] Rincian aset lancar ({fmt_angka(jml)}) tidak sama dengan total aset lancar "
                                  f"({fmt_angka(tal)}). Periksa pemetaan akun.")
        elif sum(komponen) > tal + toleransi(tal):
            error.append(f"[{p}] Kas + piutang + persediaan melebihi total aset lancar.")
        lk_saji = lr.get("laba_kotor", {}).get(p)
        if lk_saji is not None:
            hitung = lr["pendapatan"][p] - lr["beban_pokok_penjualan"][p]
            if abs(lk_saji - hitung) > toleransi(lr["pendapatan"][p]):
                peringatan.append(f"[{p}] Laba kotor disajikan {fmt_angka(lk_saji)}, hasil hitung pendapatan - HPP "
                                  f"{fmt_angka(hitung)}.")
        kas_akhir = ak.get("kas_akhir", {}).get(p)
        if kas_akhir is not None and abs(kas_akhir - n["kas_dan_setara_kas"][p]) > toleransi(n["total_aset"][p]):
            peringatan.append(f"[{p}] Kas akhir di arus kas ({fmt_angka(kas_akhir)}) berbeda dengan kas di neraca "
                              f"({fmt_angka(n['kas_dan_setara_kas'][p])}). Bisa karena cerukan bank atau salah ekstraksi.")
        if te <= 0:
            peringatan.append(f"[{p}] Ekuitas nol/negatif; ROE dan DER tidak bermakna dan tidak dihitung.")
    if error:
        raise GagalValidasi("\n".join(error))


def bagi(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def hitung(lk: dict, periode: list, hari: dict, metode: str = "akhir") -> tuple:
    """Kembalikan (nilai, teks_perhitungan).

    metode 'akhir'     : saldo neraca akhir periode (bawaan).
    metode 'rata-rata' : rata-rata saldo awal & akhir untuk ROA, ROE, perputaran, DIO/DSO/DPO. Periode pertama tetap
                         memakai saldo akhir karena saldo awalnya tidak ada.
    """
    n, lr, ak = lk["neraca"], lk["laba_rugi"], lk["arus_kas"]
    out = {k: {} for k, *_ in RASIO}
    teks = {k: {} for k, *_ in RASIO}
    U = lambda x: fmt_angka(x, 0)  # noqa: E731
    for i, p in enumerate(periode):
        h = hari[p]
        tahun = 365.0 / h
        prev = periode[i - 1] if i > 0 else None

        def g(bag, k, pp=p):
            return bag.get(k, {}).get(pp)

        def saldo(k):
            v = g(n, k)
            if metode == "rata-rata" and prev is not None and v is not None and g(n, k, prev) is not None:
                return (v + g(n, k, prev)) / 2, f"rata-rata({U(g(n, k, prev))}; {U(v)})"
            return v, U(v)

        def catat(k, nilai, rumus_teks, satuan):
            out[k][p] = nilai
            teks[k][p] = f"{rumus_teks} = {fmt_nilai(nilai, satuan)}" if nilai is not None else "tidak dapat dihitung"

        def pct(x):
            return None if x is None else x * 100

        pend, hpp = g(lr, "pendapatan"), g(lr, "beban_pokok_penjualan")
        lb, lu, lkt = g(lr, "laba_bersih"), g(lr, "laba_usaha"), g(lr, "laba_kotor")
        ta, te, tl = g(n, "total_aset"), g(n, "total_ekuitas"), g(n, "total_liabilitas")
        tal, tljp = g(n, "total_aset_lancar"), g(n, "total_liabilitas_jangka_pendek")
        pers, kas = g(n, "persediaan"), g(n, "kas_dan_setara_kas")
        dep = g(lr, "penyusutan")
        ebitda = (lu + dep) if (lu is not None and dep is not None) else None
        tag = " × 365/hari" if tahun != 1 else ""

        catat("current_ratio", bagi(tal, tljp), f"{U(tal)} ÷ {U(tljp)}", "kali")
        catat("quick_ratio", bagi(tal - pers, tljp), f"({U(tal)} - {U(pers)}) ÷ {U(tljp)}", "kali")
        catat("cash_ratio", bagi(kas, tljp), f"{U(kas)} ÷ {U(tljp)}", "kali")
        catat("gross_margin", pct(bagi(lkt, pend)), f"{U(lkt)} ÷ {U(pend)} × 100%", "persen")
        catat("operating_margin", pct(bagi(lu, pend)), f"{U(lu)} ÷ {U(pend)} × 100%", "persen")
        catat("ebitda_margin", pct(bagi(ebitda, pend)), f"({U(lu)} + {U(dep)}) ÷ {U(pend)} × 100%", "persen")
        catat("net_margin", pct(bagi(lb, pend)), f"{U(lb)} ÷ {U(pend)} × 100%", "persen")
        bu = g(lr, "beban_usaha")
        catat("opex_ratio", pct(bagi(bu, pend)), f"{U(bu)} ÷ {U(pend)} × 100%", "persen")
        lsp, pjk = g(lr, "laba_sebelum_pajak"), g(lr, "beban_pajak")
        catat("effective_tax", pct(bagi(pjk, lsp)) if (lsp and lsp > 0) else None, f"{U(pjk)} ÷ {U(lsp)} × 100%", "persen")
        sta, tta = saldo("total_aset")
        ste, tte = saldo("total_ekuitas")
        catat("roa", pct(bagi(lb * tahun, sta)) if lb is not None else None, f"{U(lb)}{tag} ÷ {tta} × 100%", "persen")
        catat("roe", pct(bagi(lb * tahun, ste)) if (lb is not None and te > 0) else None,
              f"{U(lb)}{tag} ÷ {tte} × 100%", "persen")
        catat("equity_multiplier", bagi(ta, te) if te > 0 else None, f"{U(ta)} ÷ {U(te)}", "kali")
        catat("der", bagi(tl, te) if te > 0 else None, f"{U(tl)} ÷ {U(te)}", "kali")
        ub = g(n, "utang_bank_total")
        catat("der_berbunga", bagi(ub, te) if (te > 0 and ub is not None) else None, f"{U(ub)} ÷ {U(te)}", "kali")
        catat("debt_to_assets", pct(bagi(tl, ta)), f"{U(tl)} ÷ {U(ta)} × 100%", "persen")
        nde = bagi(ub - kas, ebitda * tahun) if (ub is not None and ebitda and ebitda > 0) else None
        catat("net_debt_ebitda", nde, f"({U(ub)} - {U(kas)}) ÷ {U(ebitda)}{tag}", "kali")
        bunga = g(lr, "beban_bunga")
        catat("interest_coverage", bagi(lu, bunga) if bunga else None, f"{U(lu)} ÷ {U(bunga)}", "kali")
        sp, tp = saldo("persediaan")
        spi, tpi = saldo("piutang_usaha")
        sua, tua = saldo("utang_usaha")
        catat("dio", bagi(sp * h, hpp) if sp is not None else None, f"{tp} ÷ {U(hpp)} × {h:.0f}", "hari")
        catat("dso", bagi(spi * h, pend) if spi is not None else None, f"{tpi} ÷ {U(pend)} × {h:.0f}", "hari")
        catat("dpo", bagi(sua * h, hpp) if sua is not None else None, f"{tua} ÷ {U(hpp)} × {h:.0f}", "hari")
        komp = [out["dio"][p], out["dso"][p], out["dpo"][p]]
        if None in komp:
            catat("ccc", None, "", "hari")
        else:
            catat("ccc", komp[0] + komp[1] - komp[2],
                  f"{fmt_nilai(komp[0], 'hari')} + {fmt_nilai(komp[1], 'hari')} - {fmt_nilai(komp[2], 'hari')}", "hari")
        catat("inventory_turnover", bagi(hpp * tahun, sp) if hpp is not None else None, f"{U(hpp)}{tag} ÷ {tp}", "kali")
        catat("receivable_turnover", bagi(pend * tahun, spi), f"{U(pend)}{tag} ÷ {tpi}", "kali")
        catat("asset_turnover", bagi(pend * tahun, sta), f"{U(pend)}{tag} ÷ {tta}", "kali")
        cfo = g(ak, "arus_kas_operasi")
        catat("cfo_to_ni", bagi(cfo, lb) if (lb is not None and lb > 0) else None, f"{U(cfo)} ÷ {U(lb)}", "kali")
        capex = g(ak, "belanja_modal")
        catat("fcf_margin", pct(bagi(cfo - capex, pend)) if capex is not None else None,
              f"({U(cfo)} - {U(capex)}) ÷ {U(pend)} × 100%", "persen")
        catat("capex_to_dep", bagi(capex, dep) if (capex is not None and dep) else None, f"{U(capex)} ÷ {U(dep)}", "kali")
        sl = g(n, "saldo_laba")
        if sl is not None and lu is not None and ta and tl and tl > 0:
            x1, x2, x3, x4 = (tal - tljp) / ta, sl / ta, lu * tahun / ta, te / tl
            catat("altman_z", 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4,
                  f"6,56×{fmt_angka(x1, 3)} + 3,26×{fmt_angka(x2, 3)} + 6,72×{fmt_angka(x3, 3)} + 1,05×{fmt_angka(x4, 3)}",
                  "skor")
        else:
            out["altman_z"][p] = None
            teks["altman_z"][p] = "butuh saldo_laba di neraca"
    return out, teks


def perubahan(nilai: dict, periode: list, satuan: str) -> dict:
    hasil = {}
    pasangan = [(periode[i - 1], periode[i]) for i in range(1, len(periode))]
    if len(periode) > 2:
        pasangan.append((periode[0], periode[-1]))
    for a, b in pasangan:
        va, vb = nilai.get(a), nilai.get(b)
        kunci = f"{a}->{b}"
        if va is None or vb is None:
            hasil[kunci] = None
            continue
        p = {"dari": va, "ke": vb, "selisih": vb - va}
        if satuan in ("uang", "kali"):
            if va > 0:
                p["persen"] = (vb - va) / va * 100
            else:
                p["persen"] = None
                p["catatan"] = "berbalik dari negatif" if va < 0 and vb > 0 else (
                    "dasar nol/negatif, persentase tidak bermakna")
        hasil[kunci] = p
    return hasil


def bulatkan(x, d=4):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return round(x, d)
    return x


def susun_output(data, lk, periode, hari, rasio, peringatan, teks=None, metode="akhir") -> dict:
    pos = {}
    for bagian, k, label in POS_UTAMA:
        nilai = lk[bagian].get(k)
        if not nilai or all(v is None for v in nilai.values()):
            continue
        pos[k] = {"label": label, "satuan": "uang",
                  "nilai": {p: bulatkan(nilai.get(p), 2) for p in periode},
                  "perubahan": {kk: ({x: bulatkan(y) for x, y in vv.items()} if isinstance(vv, dict) else vv)
                                for kk, vv in perubahan(nilai, periode, "uang").items()}}
    rs = {}
    for k, label, kelompok, satuan, rumus in RASIO:
        nilai = rasio[k]
        rs[k] = {"label": label, "kelompok": kelompok, "satuan": satuan, "rumus": rumus,
                 "nilai": {p: bulatkan(nilai.get(p)) for p in periode},
                 "perhitungan": (teks or {}).get(k, {}),
                 "perubahan": {kk: ({x: bulatkan(y) for x, y in vv.items()} if isinstance(vv, dict) else vv)
                               for kk, vv in perubahan(nilai, periode, satuan).items()}}
    return {
        "meta": {
            "perusahaan": data.get("perusahaan", "(tanpa nama)"),
            "mata_uang": data.get("mata_uang", "IDR"),
            "satuan": data.get("satuan", ""),
            "periode": periode,
            "hari_periode": hari,
            "metode": ("Saldo neraca akhir periode (bukan rata-rata)" if metode == "akhir" else
                       "Rata-rata saldo awal & akhir untuk ROA, ROE, perputaran, DIO/DSO/DPO (periode pertama: saldo akhir)")
                      + ". Laba disetahunkan bila periode < 365 hari.",
            "metode_kode": metode,
            "sumber": data.get("sumber", ""),
            "skrip": f"hitung_rasio.py v{VERSI}",
        },
        "validasi": {"status": "lolos", "peringatan": peringatan},
        "pos_utama": pos,
        "rasio": rs,
        "laporan_terstandar": {b: {k: {p: bulatkan(v.get(p), 2) for p in periode} for k, v in lk[b].items()}
                               for b in ("neraca", "laba_rugi", "arus_kas")},
    }


KUNCI_RINGKAS = ["current_ratio", "gross_margin", "net_margin", "roe", "der", "dso", "dio", "cfo_to_ni"]


def nilai_akhir(out, k):
    per = out["meta"]["periode"]
    v = out["rasio"][k]["nilai"]
    b = v.get(per[-1])
    a = v.get(per[-2]) if len(per) > 1 else None
    return a, b


def daftar_periksa(out):
    """Checklist kesehatan: (judul, status, teks_nilai, teks_ambang). Status: aman / perhatian / kritis."""
    per = out["meta"]["periode"]
    R = lambda k: nilai_akhir(out, k)  # noqa: E731
    F = fmt_nilai
    items = []

    def abs_tinggi(k, judul, w, c, sat):
        a, b = R(k)
        if b is None:
            return
        st = "aman" if b >= w else ("perhatian" if b >= c else "kritis")
        items.append((judul, st, F(b, sat), f"aman ≥ {F(w, sat)}; kritis < {F(c, sat)}"))

    def abs_rendah(k, judul, w, c, sat):
        a, b = R(k)
        if b is None:
            return
        st = "aman" if b <= w else ("perhatian" if b <= c else "kritis")
        items.append((judul, st, F(b, sat), f"aman ≤ {F(w, sat)}; kritis > {F(c, sat)}"))

    def tren(k, judul, w, c, sat, arah):
        a, b = R(k)
        if a is None or b is None:
            return
        d = b - a
        buruk = d if arah == "rendah" else -d
        st = "aman" if buruk < w else ("perhatian" if buruk < c else "kritis")
        satd = "poin" if sat == "persen" else sat
        teks_d = (f"{'+' if d >= 0 else '-'}{fmt_angka(abs(d), 1 if sat == 'persen' else 0)} "
                  f"{'poin' if sat == 'persen' else 'hari'}")
        arah_teks = "naik" if arah == "rendah" else "turun"
        items.append((judul, st, f"{F(a, sat)} → {F(b, sat)} ({teks_d})",
                      f"aman bila {arah_teks} < {fmt_angka(w, 0 if satd == 'hari' else 1)} {'poin' if sat == 'persen' else 'hari'}"))

    abs_tinggi("current_ratio", "Rasio lancar", 1.5, 1.0, "kali")
    abs_tinggi("quick_ratio", "Quick ratio", 1.0, 0.7, "kali")
    a, b = R("cfo_to_ni")
    if b is not None:
        st = "aman" if b >= 1 else ("perhatian" if b >= 0.5 else "kritis")
        items.append(("Laba menjadi kas (arus kas operasi ÷ laba)", st, F(b, "kali"), "aman ≥ 1,00x; kritis < 0,50x"))
    tren("gross_margin", "Margin laba kotor", 1.0, 2.5, "persen", "tinggi")
    tren("net_margin", "Margin laba bersih", 1.0, 2.0, "persen", "tinggi")
    tren("dso", "Hari piutang (DSO)", 10, 20, "hari", "rendah")
    tren("dio", "Hari persediaan (DIO)", 10, 20, "hari", "rendah")
    tren("ccc", "Siklus konversi kas", 15, 30, "hari", "rendah")
    abs_rendah("der", "DER (liabilitas ÷ ekuitas)", 1.0, 2.0, "kali")
    abs_tinggi("interest_coverage", "Interest coverage", 3.0, 1.5, "kali")
    abs_rendah("net_debt_ebitda", "Utang bank bersih ÷ EBITDA", 2.5, 3.5, "kali")
    a, b = R("altman_z")
    if b is not None:
        st = "aman" if b > 2.6 else ("perhatian" if b >= 1.1 else "kritis")
        items.append(("Skor Altman Z'' (indikatif)", st, F(b, "skor"), "aman > 2,60; zona abu-abu 1,10-2,60; kritis < 1,10"))
    pend = out["pos_utama"].get("pendapatan", {}).get("nilai", {})
    if len(per) > 1 and pend.get(per[-2]):
        g_ = (pend[per[-1]] / pend[per[-2]] - 1) * 100
        st = "aman" if g_ >= 0 else ("perhatian" if g_ >= -5 else "kritis")
        items.append(("Pertumbuhan pendapatan", st, F(g_, "persen"), "aman ≥ 0%; kritis < -5%"))
    return items


def kepala(out):
    m = out["meta"]
    L = [f"# Ringkasan Rasio: {m['perusahaan']}", "",
         f"Satuan pos keuangan: {m['mata_uang']} {m['satuan']}. Metode: {m['metode']}", ""]
    if out["validasi"]["peringatan"]:
        L += ["**Peringatan validasi:**", ""] + [f"- {w}" for w in out["validasi"]["peringatan"]] + [""]
    return L


KAKI = ["", "_Angka dihitung oleh skrip deterministik. Ambang status adalah ambang umum, bukan benchmark industri. "
        "Alat bantu analisis, bukan nasihat investasi atau hasil audit._", "",
        "Disusun dengan TQ Board Insight | totalquality.co.id", ""]
LABEL_ST = {"aman": "aman", "perhatian": "perlu perhatian", "kritis": "kritis"}


def md_checklist(out):
    items = daftar_periksa(out)
    aman = sum(1 for i in items if i[1] == "aman")
    L = kepala(out) + [f"## Checklist kesehatan keuangan, {aman} dari {len(items)} aman", ""]
    urut = {"kritis": 0, "perhatian": 1, "aman": 2}
    for judul, st, nilai, ambang in sorted(items, key=lambda x: urut[x[1]]):
        L.append(f"- [{'x' if st == 'aman' else ' '}] **{judul}: {nilai}** ({LABEL_ST[st]}; {ambang})")
    L += ["", "Kotak tercentang = sudah dalam batas aman. Kotak kosong = perlu dibahas dengan tim."]
    return "\n".join(L + KAKI)


def md_ringkas(out):
    per = out["meta"]["periode"]
    p0, p1 = (per[-2], per[-1]) if len(per) > 1 else (None, per[-1])
    L = kepala(out) + ["## Rasio kunci", "", f"| Rasio | {p0 or ''} | {p1} | Perubahan |", "|---|---:|---:|---:|"]
    kunci_ubah = f"{p0}->{p1}" if p0 else None
    for k in KUNCI_RINGKAS:
        v = out["rasio"][k]
        L.append(f"| {v['label']} | {fmt_nilai(v['nilai'].get(p0), v['satuan']) if p0 else ''} | "
                 f"{fmt_nilai(v['nilai'].get(p1), v['satuan'])} | "
                 f"{fmt_perubahan(v['perubahan'].get(kunci_ubah), v['satuan']) if kunci_ubah else '-'} |")
    items = [i for i in daftar_periksa(out) if i[1] != "aman"]
    items.sort(key=lambda x: 0 if x[1] == "kritis" else 1)
    L += ["", "## Tiga hal yang perlu perhatian", ""]
    if items:
        L += [f"{n}. **{j}**: {nil} ({LABEL_ST[st]})" for n, (j, st, nil, _) in enumerate(items[:3], 1)]
    else:
        L.append("Tidak ada indikator di luar batas aman.")
    return "\n".join(L + KAKI)


def md_detail(out):
    m = out["meta"]
    per = m["periode"]
    kunci_ubah = f"{per[-2]}->{per[-1]}" if len(per) > 1 else None
    L = kepala(out)
    head = "| Pos | " + " | ".join(per) + (" | Perubahan |" if kunci_ubah else " |")
    sep = "|---|" + "---:|" * len(per) + ("---:|" if kunci_ubah else "")
    L += ["## Pos utama", "", head, sep]
    for k, v in out["pos_utama"].items():
        baris = [fmt_nilai(v["nilai"][p], "uang") for p in per]
        ubah = fmt_perubahan(v["perubahan"].get(kunci_ubah), "uang") if kunci_ubah else None
        L.append(f"| {v['label']} | " + " | ".join(baris) + (f" | {ubah} |" if kunci_ubah else " |"))
    kelompok = None
    head_r = "| Rasio | " + " | ".join(per) + (" | Perubahan" if kunci_ubah else "") + f" | Perhitungan {per[-1]} |"
    sep_r = "|---|" + "---:|" * len(per) + ("---:|" if kunci_ubah else "") + "---|"
    for k, v in out["rasio"].items():
        if v["kelompok"] != kelompok:
            kelompok = v["kelompok"]
            L += ["", f"## {kelompok}", "", head_r, sep_r]
        baris = [fmt_nilai(v["nilai"][p], v["satuan"]) for p in per]
        ubah = fmt_perubahan(v["perubahan"].get(kunci_ubah), v["satuan"]) if kunci_ubah else None
        hit = v.get("perhitungan", {}).get(per[-1], "")
        L.append(f"| {v['label']} | " + " | ".join(baris) + (f" | {ubah}" if kunci_ubah else "") + f" | {hit} |")
    # DuPont
    nm, at, em, roe = (nilai_akhir(out, k)[1] for k in ("net_margin", "asset_turnover", "equity_multiplier", "roe"))
    if None not in (nm, at, em):
        L += ["", "## Dekomposisi DuPont (periode terakhir)", "",
              f"ROE {fmt_nilai(roe, 'persen')} = margin laba bersih {fmt_nilai(nm, 'persen')} × perputaran aset "
              f"{fmt_nilai(at, 'kali')} × pengali ekuitas {fmt_nilai(em, 'kali')}. "
              "Artinya: imbal hasil pemilik datang dari seberapa besar laba per penjualan, seberapa produktif aset, "
              "dan seberapa besar dibiayai utang."]
    z = nilai_akhir(out, "altman_z")[1]
    if z is not None:
        zona = "aman" if z > 2.6 else ("abu-abu" if z >= 1.1 else "rawan")
        L += ["", "## Skor Altman Z'' (indikatif)", "",
              f"Skor {fmt_nilai(z, 'skor')} → zona **{zona}** (aman > 2,60; abu-abu 1,10-2,60; rawan < 1,10). "
              "Model statistik untuk perusahaan non-publik; dipakai sebagai sinyal awal, bukan vonis."]
    return "\n".join(L + KAKI)


def ke_markdown(out: dict, gaya: str = "detail") -> str:
    return {"ringkas": md_ringkas, "checklist": md_checklist}.get(gaya, md_detail)(out)


def baca_preferensi(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Hitung rasio keuangan dari LK format standar (JSON).")
    ap.add_argument("input", type=Path, help="File JSON format standar")
    ap.add_argument("--out-json", type=Path, help="Tulis hasil lengkap (JSON) ke file ini")
    ap.add_argument("--out-md", type=Path, help="Tulis ringkasan Markdown ke file ini")
    ap.add_argument("--gaya", choices=["ringkas", "detail", "checklist"],
                    help="Gaya ringkasan Markdown (bawaan: dari preferensi, atau detail)")
    ap.add_argument("--metode", choices=["akhir", "rata-rata"],
                    help="Saldo neraca akhir periode (bawaan) atau rata-rata awal & akhir")
    ap.add_argument("--preferensi", type=Path, help="preferensi.json dari skill tampilan-direksi")
    ap.add_argument("--diam", action="store_true", help="Jangan cetak Markdown ke layar")
    a = ap.parse_args(argv)

    pref = {}
    if a.preferensi:
        pref = baca_preferensi(a.preferensi)
    elif Path("preferensi.json").exists():
        pref = baca_preferensi("preferensi.json")
        print("Memakai preferensi.json di folder ini.", file=sys.stderr)
    gaya = a.gaya or pref.get("gaya_narasi") or "detail"
    metode = a.metode or pref.get("metode_rasio") or "akhir"

    data = muat(a.input)
    periode = [str(p) for p in data["periode"]]
    peringatan: list = []
    lk = normalisasi(data, peringatan)
    hari_input = data.get("hari_periode") or {}
    hari = {}
    for p in periode:
        h = angka(hari_input.get(p)) if isinstance(hari_input, dict) else None
        hari[p] = h if h and h > 0 else 365.0
    turunkan(lk, periode)
    try:
        validasi(lk, periode, peringatan)
    except GagalValidasi as e:
        print("VALIDASI GAGAL - rasio TIDAK dihitung.\n", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print("\nPeriksa kembali angka hasil ekstraksi, perbaiki file input, lalu jalankan ulang. "
              "Jangan menebak angka.", file=sys.stderr)
        return 2
    rasio, teks = hitung(lk, periode, hari, metode)
    out = susun_output(data, lk, periode, hari, rasio, peringatan, teks, metode)
    out["meta"]["gaya"] = gaya
    out["checklist"] = [{"judul": j, "status": s, "nilai": v, "ambang": am} for j, s, v, am in daftar_periksa(out)]
    md = ke_markdown(out, gaya)
    if a.out_json:
        a.out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    if a.out_md:
        a.out_md.write_text(md, encoding="utf-8")
    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
