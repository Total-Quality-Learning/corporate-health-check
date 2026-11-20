#!/usr/bin/env python3
"""Ekstraktor Trial Balance (Neraca Saldo) & penghitung Arus Kas Tidak Langsung otomatis.

Digunakan oleh `tools/konversi_data.py` ketika input berupa Neraca Saldo (Debit/Kredit)
atau laporan Neraca + Laba Rugi tanpa sheet ArusKas.
"""
from __future__ import annotations

import re
from typing import Any

# Saldo normal positif pada laporan keuangan:
# "D" = Debit - Kredit | "K" = Kredit - Debit
SALDO_NORMAL = {
    "tahunan": {
        "neraca": {
            "kas_dan_setara_kas": "D", "piutang_usaha": "D", "persediaan": "D",
            "aset_lancar_lainnya": "D", "aset_tetap_neto": "D", "aset_tidak_lancar_lainnya": "D",
            "utang_bank_jangka_pendek": "K", "utang_usaha": "K", "liabilitas_jangka_pendek_lainnya": "K",
            "utang_bank_jangka_panjang": "K", "liabilitas_jangka_panjang_lainnya": "K",
            "total_ekuitas": "K", "saldo_laba": "K",
        },
        "laba_rugi": {
            "pendapatan": "K", "beban_pokok_penjualan": "D", "beban_penjualan": "D",
            "beban_umum_administrasi": "D", "beban_usaha": "D", "beban_bunga": "D",
            "pendapatan_beban_lain": "K", "beban_pajak": "D", "penyusutan": "D",
        },
    },
    "bulanan": {
        "neraca": {
            "kas": "D", "piutang_usaha_bruto": "D", "cadangan_kerugian_piutang": "K",
            "persediaan_bahan_baku": "D", "persediaan_barang_dalam_proses": "D",
            "persediaan_barang_jadi": "D", "uang_muka_dan_dibayar_dimuka": "D",
            "aset_tetap_perolehan": "D", "akumulasi_penyusutan": "K", "aset_tidak_lancar_lain": "D",
            "utang_usaha": "K", "utang_bank_pendek": "K", "bagian_lancar_utang_panjang": "K",
            "beban_akrual": "K", "utang_pajak": "K", "utang_bank_panjang": "K",
            "liabilitas_imbalan_kerja": "K", "modal_disetor": "K", "saldo_laba": "K",
        },
        "laba_rugi": {
            "penjualan_bruto": "K", "potongan_dan_retur": "D", "pendapatan": "K",
            "hpp_bahan": "D", "hpp_upah": "D", "hpp_overhead": "D", "hpp_penyusutan": "D",
            "beban_penjualan": "D", "beban_umum_adm": "D", "beban_penyusutan_usaha": "D",
            "pendapatan_beban_lain": "K", "beban_bunga": "D", "beban_pajak": "D",
        },
    },
}

SINONIM_TB_EKSTRA = {
    "tahunan": [
        ("neraca", "total_ekuitas", (
            "modal disetor", "modal saham", "tambahan modal disetor", "agio saham",
            "ekuitas pemilik", "modal pemilik", "prive", "ikhtisar modal",
        )),
        ("neraca", "aset_tetap_neto", (
            "akumulasi penyusutan", "akumulasi depresiasi", "peralatan", "mesin",
            "kendaraan", "bangunan", "tanah", "inventaris kantor",
        )),
        ("neraca", "piutang_usaha", (
            "cadangan kerugian piutang", "penyisihan piutang",
        )),
    ],
    "bulanan": [
        ("neraca", "modal_disetor", (
            "tambahan modal disetor", "agio saham", "modal pemilik",
        )),
        ("neraca", "aset_tetap_perolehan", (
            "tanah", "bangunan", "mesin dan peralatan", "mesin", "kendaraan", "inventaris kantor",
        )),
    ],
}


def tebak_bagian_coa(kode_coa: str | None) -> str | None:
    """Tebak bagian laporan dari digit awal kode akun standar Indonesia."""
    if not kode_coa:
        return None
    m = re.match(r"^\s*([1-9])", str(kode_coa))
    if not m:
        return None
    d = m.group(1)
    if d in ("1", "2", "3"):
        return "neraca"
    if d in ("4", "5", "6", "7", "8"):
        return "laba_rugi"
    return None


def deteksi_kolom_tb(rows: list[list[Any]], parse_periode_fn, bersihkan_fn) -> dict[str, Any] | None:
    """Deteksi header Trial Balance (single-periode Debit/Kredit, multi-periode D/K, atau tidy D/K)."""
    for idx, r in enumerate(rows[:20]):
        if not r:
            continue
        kode_col = None
        akun_col = None
        periode_col = None
        dk_pairs: dict[str, dict[str, int]] = {}
        plain_d: int | None = None
        plain_k: int | None = None

        for c, val in enumerate(r):
            if val is None or str(val).strip() == "":
                continue
            raw_s = str(val).strip()
            low = bersihkan_fn(raw_s)

            if kode_col is None and low in ("kode", "kode akun", "no akun", "coa", "account code", "acct no"):
                kode_col = c
                continue
            if akun_col is None and low in ("nama akun", "akun", "uraian", "keterangan", "account name", "account", "description"):
                akun_col = c
                continue
            if periode_col is None and low in ("periode", "bulan", "tahun", "period", "tanggal", "date"):
                periode_col = c
                continue
            if low in ("debit", "debet", "dr"):
                plain_d = c
                continue
            if low in ("kredit", "credit", "cr"):
                plain_k = c
                continue

            # Cek pola multi-periode mis. "debit_2025", "2025 debit", "kredit Jan 2025"
            m_dk = re.match(r"^(debit|debet|dr|kredit|credit|cr)[\s_\-:]+(.+)$", raw_s, flags=re.IGNORECASE)
            if not m_dk:
                m_dk = re.match(r"^(.+?)[\s_\-:]+(debit|debet|dr|kredit|credit|cr)$", raw_s, flags=re.IGNORECASE)
                if m_dk:
                    sisi_raw, p_raw = m_dk.group(2), m_dk.group(1)
                else:
                    sisi_raw, p_raw = None, None
            else:
                sisi_raw, p_raw = m_dk.group(1), m_dk.group(2)

            if sisi_raw and p_raw:
                pp = parse_periode_fn(p_raw)
                if pp:
                    sisi = "D" if sisi_raw.lower() in ("debit", "debet", "dr") else "K"
                    dk_pairs.setdefault(pp[0], {})[sisi] = c
                    dk_pairs[pp[0]]["_meta"] = pp  # type: ignore[assignment]

        if akun_col is None and kode_col is not None:
            akun_col = kode_col
        if akun_col is None:
            # Cari kolom teks sebelum kolom angka pertama
            for c, val in enumerate(r):
                if c not in (kode_col, periode_col, plain_d, plain_k) and val not in (None, ""):
                    akun_col = c
                    break

        if akun_col is None:
            continue

        valid_multi = {k: v for k, v in dk_pairs.items() if "D" in v and "K" in v}
        if valid_multi:
            return {
                "mode": "multi_dk", "header_idx": idx, "kode_col": kode_col,
                "akun_col": akun_col, "pairs": valid_multi,
            }
        if plain_d is not None and plain_k is not None:
            return {
                "mode": "tidy_dk" if periode_col is not None else "single_dk",
                "header_idx": idx, "kode_col": kode_col, "akun_col": akun_col,
                "periode_col": periode_col, "d_col": plain_d, "k_col": plain_k,
            }
    return None


def ekstrak_baris_tb(
    tabel: list[tuple[str, str | None, list[list[Any]]]],
    parse_angka_fn,
    parse_periode_fn,
    bersihkan_fn,
    default_periode: str = "2025",
) -> tuple[list[dict[str, Any]], dict[str, tuple[float, float]]]:
    """Ekstrak baris Trial Balance menjadi daftar akun + total Debit/Kredit per periode."""
    baris_tb: list[dict[str, Any]] = []
    totals: dict[str, list[float]] = {}

    for sumber, _, rows in tabel:
        if not rows:
            continue
        hdr = deteksi_kolom_tb(rows, parse_periode_fn, bersihkan_fn)
        if not hdr:
            continue

        # Coba cari periode dari judul atas atau nama file jika single_dk
        p_fallback = parse_periode_fn(sumber.rsplit(".", 1)[0])
        if not p_fallback:
            for r in rows[:hdr["header_idx"]]:
                for val in r:
                    m = re.search(r"(\d{4}-\d{2}|\b(?:19|20)\d{2}\b)", str(val or ""))
                    if m:
                        p_fallback = parse_periode_fn(m.group(1))
                        if p_fallback:
                            break
                if p_fallback:
                    break
        if not p_fallback:
            p_fallback = parse_periode_fn(default_periode) or (default_periode, False, (2025, 12, 31))

        h_idx = hdr["header_idx"]
        kode_col = hdr["kode_col"]
        akun_col = hdr["akun_col"]
        tidy_map: dict[tuple[str | None, str], dict[str, Any]] = {}

        for r in rows[h_idx + 1:]:
            if not r or all(x in (None, "") for x in r):
                continue
            kode_coa = str(r[kode_col]).strip() if kode_col is not None and kode_col < len(r) and r[kode_col] not in (None, "") else None
            akun = str(r[akun_col]).strip() if akun_col < len(r) and r[akun_col] not in (None, "") else (kode_coa or "")
            if not akun:
                continue
            low = bersihkan_fn(akun)
            if low in ("total", "jumlah", "total debit kredit", "grand total") or low.startswith(("total ", "jumlah ")):
                continue

            if hdr["mode"] == "multi_dk":
                nilai_dk: dict[str, tuple[float, float]] = {}
                p_meta: dict[str, Any] = {}
                for p_lbl, cols in hdr["pairs"].items():
                    dv = parse_angka_fn(r[cols["D"]] if cols["D"] < len(r) else None) or 0.0
                    kv = parse_angka_fn(r[cols["K"]] if cols["K"] < len(r) else None) or 0.0
                    if dv != 0.0 or kv != 0.0:
                        nilai_dk[p_lbl] = (dv, kv)
                        p_meta[p_lbl] = cols["_meta"]
                        t = totals.setdefault(p_lbl, [0.0, 0.0])
                        t[0] += dv
                        t[1] += kv
                if nilai_dk:
                    baris_tb.append({
                        "sumber": sumber, "kode_coa": kode_coa, "akun": akun,
                        "nilai_dk": nilai_dk, "periode_meta": p_meta,
                    })
            else:
                dv = parse_angka_fn(r[hdr["d_col"]] if hdr["d_col"] < len(r) else None) or 0.0
                kv = parse_angka_fn(r[hdr["k_col"]] if hdr["k_col"] < len(r) else None) or 0.0
                if dv == 0.0 and kv == 0.0:
                    continue
                if hdr["mode"] == "tidy_dk":
                    pp = parse_periode_fn(r[hdr["periode_col"]] if hdr["periode_col"] < len(r) else None) or p_fallback
                else:
                    pp = p_fallback
                t = totals.setdefault(pp[0], [0.0, 0.0])
                t[0] += dv
                t[1] += kv
                key = (kode_coa, akun)
                item = tidy_map.setdefault(key, {
                    "sumber": sumber, "kode_coa": kode_coa, "akun": akun,
                    "nilai_dk": {}, "periode_meta": {},
                })
                old_d, old_k = item["nilai_dk"].get(pp[0], (0.0, 0.0))
                item["nilai_dk"][pp[0]] = (old_d + dv, old_k + kv)
                item["periode_meta"][pp[0]] = pp

        if tidy_map:
            baris_tb.extend(tidy_map.values())

    return baris_tb, {k: (v[0], v[1]) for k, v in totals.items()}


def konversi_tb_ke_mapped(
    baris_tb: list[dict[str, Any]],
    jenis: str,
    pemetaan_kustom: dict[tuple[str | None, str], tuple[str | None, str | None, int]],
    kode_valid: dict[str, set[str]],
    sinonim: list[tuple[str, str, tuple[str, ...]]],
    bersihkan_fn,
    cocok_sinonim_fn,
    fallback_bulanan: dict[tuple[str, str], tuple[str, str]],
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, Any], list[str]]:
    """Petakan Trial Balance ke Neraca + Laba Rugi dan hitung subtotal laporan."""
    sin_lengkap = SINONIM_TB_EKSTRA[jenis] + sinonim
    saldo_map = SALDO_NORMAL[jenis]
    hasil: dict[str, dict[str, dict[str, float]]] = {bag: {} for bag in kode_valid}
    terpetakan: list[dict[str, Any]] = []
    tidak_terpetakan: list[dict[str, Any]] = []
    periode_set: set[str] = set()

    for b in baris_tb:
        akun = b["akun"]
        kode_coa = b.get("kode_coa")
        bag_hint = tebak_bagian_coa(kode_coa)
        label_norm = bersihkan_fn(akun)
        periode_set.update(b["nilai_dk"].keys())

        bag_t: str | None = None
        kode_t: str | None = None
        cara = ""

        if (bag_hint, label_norm) in pemetaan_kustom:
            bag_t, kode_t, _ = pemetaan_kustom[(bag_hint, label_norm)]
            cara = "kustom"
        elif (None, label_norm) in pemetaan_kustom:
            bag_t, kode_t, _ = pemetaan_kustom[(None, label_norm)]
            cara = "kustom"
        else:
            cocok = cocok_sinonim_fn(label_norm, bag_hint, sin_lengkap)
            if cocok:
                bag_t, kode_t = cocok
                cara = "sinonim_tb"
            elif jenis == "bulanan" and bag_hint and (bag_hint, label_norm) in fallback_bulanan:
                bag_t, kode_t = fallback_bulanan[(bag_hint, label_norm)]
                cara = "sinonim_ringkas"

        if cara == "kustom" and kode_t is None:
            continue
        if kode_t is None or bag_t not in hasil or kode_t not in kode_valid[bag_t]:
            contoh = next(iter(b["nilai_dk"].items()), None)
            tidak_terpetakan.append({
                "bagian": bag_hint or "-", "akun": f"{kode_coa + ' ' if kode_coa else ''}{akun}",
                "sumber": b["sumber"],
                "contoh": f"{contoh[0]}: D={contoh[1][0]}, K={contoh[1][1]}" if contoh else "-",
            })
            continue

        norm_dir = saldo_map.get(bag_t, {}).get(kode_t, "D")
        baris_target = hasil[bag_t].setdefault(kode_t, {})
        for p, (dv, kv) in b["nilai_dk"].items():
            val = (dv - kv) if norm_dir == "D" else (kv - dv)
            baris_target[p] = (baris_target.get(p) or 0.0) + val
        terpetakan.append({"bagian": bag_t, "akun": akun, "kode": kode_t, "cara": cara})

    periode = sorted(periode_set)
    # Lengkapi subtotal laporan deterministik dari akun TB
    if jenis == "tahunan":
        n, lr = hasil["neraca"], hasil["laba_rugi"]
        for p in periode:
            def vn(k: str) -> float:
                return n.get(k, {}).get(p, 0.0) or 0.0

            def vlr(k: str) -> float:
                return lr.get(k, {}).get(p, 0.0) or 0.0

            laba_kotor = vlr("pendapatan") - vlr("beban_pokok_penjualan")
            beban_usaha = vlr("beban_usaha") if lr.get("beban_usaha", {}).get(p) is not None else (
                vlr("beban_penjualan") + vlr("beban_umum_administrasi")
            )
            laba_bersih = laba_kotor - beban_usaha - vlr("beban_bunga") + vlr("pendapatan_beban_lain") - vlr("beban_pajak")
            lr.setdefault("laba_kotor", {})[p] = laba_kotor
            lr.setdefault("beban_usaha", {})[p] = beban_usaha
            lr.setdefault("laba_bersih", {})[p] = laba_bersih

            tal = vn("kas_dan_setara_kas") + vn("piutang_usaha") + vn("persediaan") + vn("aset_lancar_lainnya")
            ta = tal + vn("aset_tetap_neto") + vn("aset_tidak_lancar_lainnya")
            tljp = vn("utang_bank_jangka_pendek") + vn("utang_usaha") + vn("liabilitas_jangka_pendek_lainnya")
            tl = tljp + vn("utang_bank_jangka_panjang") + vn("liabilitas_jangka_panjang_lainnya")
            n.setdefault("total_aset_lancar", {})[p] = tal
            n.setdefault("total_aset", {})[p] = ta
            n.setdefault("total_liabilitas_jangka_pendek", {})[p] = tljp
            n.setdefault("total_liabilitas", {})[p] = tl
            # Pada Trial Balance pra-penutup, laba tahun berjalan belum ditutup ke ekuitas -> tambahkan ke total_ekuitas.
            eq_dasar = vn("total_ekuitas") + vn("saldo_laba")
            if abs(ta - tl - eq_dasar) > max(2.0, abs(ta) * 0.001) and abs(ta - tl - (eq_dasar + laba_bersih)) <= max(2.0, abs(ta) * 0.001):
                n.setdefault("total_ekuitas", {})[p] = eq_dasar + laba_bersih
                n.setdefault("saldo_laba", {})[p] = vn("saldo_laba") + laba_bersih
            elif "total_ekuitas" not in n or p not in n["total_ekuitas"]:
                n.setdefault("total_ekuitas", {})[p] = eq_dasar

    else:
        n, lr = hasil["neraca"], hasil["laba_rugi"]
        for p in periode:
            def vnl(k: str) -> float:
                return n.get(k, {}).get(p, 0.0) or 0.0

            def vlrl(k: str) -> float:
                return lr.get(k, {}).get(p, 0.0) or 0.0

            hpp = sum(vlrl(k) for k in ("hpp_bahan", "hpp_upah", "hpp_overhead", "hpp_penyusutan"))
            bu = vlrl("beban_penjualan") + vlrl("beban_umum_adm") + vlrl("beban_penyusutan_usaha")
            lb = vlrl("pendapatan") - hpp - bu + vlrl("pendapatan_beban_lain") - vlrl("beban_bunga") - vlrl("beban_pajak")
            if p in lr.get("pendapatan", {}):
                lr.setdefault("laba_bersih", {})[p] = lb
            piutang = vnl("piutang_usaha_bruto") - vnl("cadangan_kerugian_piutang")
            persediaan = vnl("persediaan_bahan_baku") + vnl("persediaan_barang_dalam_proses") + vnl("persediaan_barang_jadi")
            ta = vnl("kas") + piutang + persediaan + vnl("uang_muka_dan_dibayar_dimuka") + (vnl("aset_tetap_perolehan") - vnl("akumulasi_penyusutan")) + vnl("aset_tidak_lancar_lain")
            tl = vnl("utang_usaha") + vnl("utang_bank_pendek") + vnl("bagian_lancar_utang_panjang") + vnl("beban_akrual") + vnl("utang_pajak") + vnl("utang_bank_panjang") + vnl("liabilitas_imbalan_kerja")
            eq = vnl("modal_disetor") + vnl("saldo_laba")
            if p in lr.get("pendapatan", {}) and abs(ta - tl - eq) > max(2.0, abs(ta) * 0.001) and abs(ta - tl - (eq + lb)) <= max(2.0, abs(ta) * 0.001):
                n.setdefault("saldo_laba", {})[p] = vnl("saldo_laba") + lb

    audit = {"terpetakan": terpetakan, "tidak_terpetakan": tidak_terpetakan, "catatan_tanda": []}
    return hasil, audit, periode


def hitung_arus_kas_tidak_langsung(hasil: dict[str, Any], jenis: str) -> list[str]:
    """Hitung Arus Kas metode tidak langsung dari perubahan Neraca & Laba Rugi bila ArusKas kosong."""
    peringatan: list[str] = []
    if jenis == "tahunan":
        periode = hasil["periode"]
        n, lr, ak = hasil["neraca"], hasil["laba_rugi"], hasil["arus_kas"]
        if ak.get("arus_kas_operasi"):
            return peringatan

        def vn(k: str, p: str) -> float:
            return n.get(k, {}).get(p, 0.0) or 0.0

        def vlr(k: str, p: str) -> float:
            return lr.get(k, {}).get(p, 0.0) or 0.0

        for i, p in enumerate(periode):
            lb = vlr("laba_bersih", p)
            dep = vlr("penyusutan", p)
            if i == 0:
                ocf = lb + dep
                capex = 0.0
                inv_cf = 0.0
                fin_cf = 0.0
                peringatan.append(
                    f"Arus kas periode awal [{p}] memakai estimasi laba bersih + penyusutan (tanpa neraca awal)."
                )
            else:
                p0 = periode[i - 1]
                d_piut = vn("piutang_usaha", p) - vn("piutang_usaha", p0)
                d_pers = vn("persediaan", p) - vn("persediaan", p0)
                d_al = vn("aset_lancar_lainnya", p) - vn("aset_lancar_lainnya", p0)
                d_ut = vn("utang_usaha", p) - vn("utang_usaha", p0)
                d_ljp = vn("liabilitas_jangka_pendek_lainnya", p) - vn("liabilitas_jangka_pendek_lainnya", p0)
                d_ljpj = vn("liabilitas_jangka_panjang_lainnya", p) - vn("liabilitas_jangka_panjang_lainnya", p0)
                ocf = lb + dep - d_piut - d_pers - d_al + d_ut + d_ljp + d_ljpj

                d_at = vn("aset_tetap_neto", p) - vn("aset_tetap_neto", p0)
                d_atl = vn("aset_tidak_lancar_lainnya", p) - vn("aset_tidak_lancar_lainnya", p0)
                capex = max(0.0, d_at + dep)
                inv_cf = -(d_at + dep + d_atl)

                d_bank_p = vn("utang_bank_jangka_pendek", p) - vn("utang_bank_jangka_pendek", p0)
                d_bank_pj = vn("utang_bank_jangka_panjang", p) - vn("utang_bank_jangka_panjang", p0)
                d_eq_non_lb = (vn("total_ekuitas", p) - vn("total_ekuitas", p0)) - lb
                fin_cf = d_bank_p + d_bank_pj + d_eq_non_lb

            ak.setdefault("arus_kas_operasi", {})[p] = ocf
            ak.setdefault("arus_kas_investasi", {})[p] = inv_cf
            ak.setdefault("arus_kas_pendanaan", {})[p] = fin_cf
            ak.setdefault("belanja_modal", {})[p] = capex
            ak.setdefault("kas_akhir", {})[p] = vn("kas_dan_setara_kas", p)

        peringatan.append("Arus kas dihitung otomatis dengan metode tidak langsung dari perubahan Neraca & Laba Rugi.")
        return peringatan

    # Bulanan
    n, lr, ak = hasil["neraca"], hasil["laba_rugi"], hasil["arus_kas"]
    if ak.get("arus_kas_operasi"):
        return peringatan
    bulan_lr = hasil["bulan"]
    bulan_n = sorted(n.get("kas", {}).keys())

    def vnb(k: str, b: str) -> float:
        return n.get(k, {}).get(b, 0.0) or 0.0

    def vlrb(k: str, b: str) -> float:
        return lr.get(k, {}).get(b, 0.0) or 0.0

    for i, b in enumerate(bulan_lr):
        idx_n = bulan_n.index(b) if b in bulan_n else -1
        b0 = bulan_n[idx_n - 1] if idx_n > 0 else None
        lb = vlrb("laba_bersih", b)
        dep_lr = vlrb("hpp_penyusutan", b) + vlrb("beban_penyusutan_usaha", b)
        if not b0:
            ocf = lb + dep_lr
            capex = 0.0
            tarik_pj = bayar_pj = d_bank_p = div = 0.0
            peringatan.append(f"Arus kas bulan [{b}] tanpa neraca awal memakai laba bersih + penyusutan.")
        else:
            d_akum = max(0.0, vnb("akumulasi_penyusutan", b) - vnb("akumulasi_penyusutan", b0))
            dep = d_akum if d_akum > 0 else dep_lr
            piut_1 = vnb("piutang_usaha_bruto", b) - vnb("cadangan_kerugian_piutang", b)
            piut_0 = vnb("piutang_usaha_bruto", b0) - vnb("cadangan_kerugian_piutang", b0)
            pers_1 = vnb("persediaan_bahan_baku", b) + vnb("persediaan_barang_dalam_proses", b) + vnb("persediaan_barang_jadi", b)
            pers_0 = vnb("persediaan_bahan_baku", b0) + vnb("persediaan_barang_dalam_proses", b0) + vnb("persediaan_barang_jadi", b0)
            ljp_1 = vnb("utang_usaha", b) + vnb("beban_akrual", b) + vnb("utang_pajak", b)
            ljp_0 = vnb("utang_usaha", b0) + vnb("beban_akrual", b0) + vnb("utang_pajak", b0)

            ocf = (
                lb + dep
                - (piut_1 - piut_0)
                - (pers_1 - pers_0)
                - (vnb("uang_muka_dan_dibayar_dimuka", b) - vnb("uang_muka_dan_dibayar_dimuka", b0))
                + (ljp_1 - ljp_0)
                + (vnb("liabilitas_imbalan_kerja", b) - vnb("liabilitas_imbalan_kerja", b0))
            )
            d_at = (vnb("aset_tetap_perolehan", b) - vnb("aset_tetap_perolehan", b0)) + (
                vnb("aset_tidak_lancar_lain", b) - vnb("aset_tidak_lancar_lain", b0)
            )
            capex = max(0.0, d_at)
            d_bank_p = (vnb("utang_bank_pendek", b) + vnb("bagian_lancar_utang_panjang", b)) - (
                vnb("utang_bank_pendek", b0) + vnb("bagian_lancar_utang_panjang", b0)
            )
            d_bank_pj = vnb("utang_bank_panjang", b) - vnb("utang_bank_panjang", b0)
            tarik_pj = max(0.0, d_bank_pj)
            bayar_pj = max(0.0, -d_bank_pj)
            div = max(0.0, vnb("saldo_laba", b0) + lb - vnb("saldo_laba", b) + (vnb("modal_disetor", b) - vnb("modal_disetor", b0)))

        ak.setdefault("arus_kas_operasi", {})[b] = ocf
        ak.setdefault("belanja_modal", {})[b] = capex
        ak.setdefault("penerimaan_pinjaman_panjang", {})[b] = tarik_pj
        ak.setdefault("pembayaran_pinjaman_panjang", {})[b] = bayar_pj
        ak.setdefault("perubahan_utang_bank_pendek", {})[b] = d_bank_p
        ak.setdefault("dividen", {})[b] = div
        ak.setdefault("kas_akhir", {})[b] = vnb("kas", b)

    peringatan.append("Arus kas bulanan dihitung otomatis dengan metode tidak langsung dari perubahan Neraca & Laba Rugi.")
    return peringatan
