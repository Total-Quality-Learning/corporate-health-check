#!/usr/bin/env python3
"""Deteksi gejala operasional dari hasil hitung_rasio.py (rasio.json).

Pemakaian:
    python scripts/deteksi_gejala.py rasio.json --out-json gejala.json --out-md gejala.md

Aturan deteksi transparan (lihat references/aturan-deteksi.md). Teks penyebab,
data pembukti, dan pertanyaan diambil dari references/peta-gejala.json.
Hanya pustaka standar Python.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERSI = "1.0.0"
PETA = Path(__file__).resolve().parents[1] / "references" / "peta-gejala.json"
URUT_TINGKAT = {"merah": 0, "kuning": 1}


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


def label_satuan(meta: dict) -> str:
    sat = str(meta.get("satuan", "")).strip()
    if "samaran" in sat:
        return "unit samaran"
    uang = "Rupiah" if meta.get("mata_uang", "IDR") == "IDR" else meta.get("mata_uang", "")
    return f"{sat} {uang}".strip()


def ambil(rasio, kunci, p, bagian="rasio"):
    item = rasio.get(bagian, {}).get(kunci)
    if not item:
        return None
    return item["nilai"].get(p)


def tumbuh(a, b):
    if a is None or b is None or a <= 0:
        return None
    return (b - a) / a * 100


def deteksi(r: dict) -> tuple[list, dict]:
    per = r["meta"]["periode"]
    b = per[-1]
    a = per[-2] if len(per) > 1 else None
    satuan = label_satuan(r["meta"])
    hari_b = r["meta"].get("hari_periode", {}).get(b, 365) or 365
    R = lambda k, p: ambil(r, k, p)                 # noqa: E731
    P = lambda k, p: ambil(r, k, p, "pos_utama")    # noqa: E731
    temuan = []

    def tambah(kode, tingkat, bukti, ringkas, dampak=None):
        temuan.append({"kode": kode, "tingkat": tingkat, "ringkas": ringkas, "bukti": bukti,
                       "dampak_kas": dampak})

    # 1. Persediaan menumpuk
    if a:
        da, db = R("dio", a), R("dio", b)
        if da is not None and db is not None:
            sel, pct = db - da, tumbuh(da, db)
            if sel >= 20 or (pct is not None and pct >= 30):
                tingkat = "merah"
            elif sel >= 10 or (pct is not None and pct >= 15):
                tingkat = "kuning"
            else:
                tingkat = None
            if tingkat:
                hpp = r["laporan_terstandar"]["laba_rugi"]["beban_pokok_penjualan"][b]
                lepas = sel / hari_b * hpp if sel > 0 else None
                g_pers = tumbuh(P("persediaan", a), P("persediaan", b))
                g_pend = tumbuh(P("pendapatan", a), P("pendapatan", b))
                bukti = [f"DIO {fmt(da)} → {fmt(db)} hari (+{fmt(sel)} hari)"]
                if g_pers is not None and g_pend is not None:
                    bukti.append(f"Persediaan tumbuh {fmt(g_pers, 1)}% sementara pendapatan tumbuh {fmt(g_pend, 1)}%")
                tambah("persediaan_menumpuk", tingkat, bukti,
                       f"Hari persediaan naik dari {fmt(da)} menjadi {fmt(db)} hari.",
                       {"keterangan": f"Kas yang dapat dilepas jika DIO kembali ke {fmt(da)} hari",
                        "nilai": round(lepas, 2) if lepas else None, "satuan": satuan})

    # 2. Margin kotor tergerus
    if a:
        ga, gb = R("gross_margin", a), R("gross_margin", b)
        if ga is not None and gb is not None:
            sel = gb - ga
            tingkat = "merah" if sel <= -2.0 else ("kuning" if sel <= -1.0 else None)
            if tingkat:
                pend = r["laporan_terstandar"]["laba_rugi"]["pendapatan"][b]
                tambah("margin_tergerus", tingkat,
                       [f"Margin laba kotor {fmt(ga, 1)}% → {fmt(gb, 1)}% ({fmt(sel, 1)} poin)"],
                       f"Margin laba kotor turun {fmt(abs(sel), 1)} poin, dari {fmt(ga, 1)}% menjadi {fmt(gb, 1)}%.",
                       {"keterangan": f"Laba kotor yang hilang dibanding margin {fmt(ga, 1)}% pada pendapatan periode {b}",
                        "nilai": round(-sel / 100 * pend, 2), "satuan": satuan})

    # 3. Laba naik, kas operasi turun / kualitas laba rendah
    nib, cfob = P("laba_bersih", b), P("arus_kas_operasi", b)
    rasio_b = R("cfo_to_ni", b)
    tingkat, bukti = None, []
    if a:
        nia, cfoa = P("laba_bersih", a), P("arus_kas_operasi", a)
        if None not in (nia, nib, cfoa, cfob) and nib > nia and cfob < cfoa:
            tingkat = "kuning"
            bukti.append(f"Laba bersih {fmt_uang(nia)} → {fmt_uang(nib)}; arus kas operasi {fmt_uang(cfoa)} → {fmt_uang(cfob)}")
    if nib is not None and nib > 0 and cfob is not None and (cfob < 0 or (rasio_b is not None and rasio_b < 0.5)):
        tingkat = "merah"
        if not bukti:
            bukti.append(f"Laba bersih {fmt_uang(nib)}; arus kas operasi {fmt_uang(cfob)}")
    if tingkat:
        if rasio_b is not None:
            bukti.append(f"Arus kas operasi / laba bersih periode {b}: {fmt(rasio_b, 2)}x")
        tambah("laba_naik_kas_turun", tingkat, bukti,
               "Laba bertambah, tetapi uang tunai dari operasi justru berkurang"
               + (" hingga negatif." if cfob is not None and cfob < 0 else "."))

    # 4. Piutang melambat
    if a:
        sa, sb = R("dso", a), R("dso", b)
        if sa is not None and sb is not None:
            sel, pct = sb - sa, tumbuh(sa, sb)
            if sel >= 20 or (pct is not None and pct >= 30):
                tingkat = "merah"
            elif sel >= 10 or (pct is not None and pct >= 15):
                tingkat = "kuning"
            else:
                tingkat = None
            if tingkat:
                pend = r["laporan_terstandar"]["laba_rugi"]["pendapatan"][b]
                tambah("piutang_melambat", tingkat, [f"DSO {fmt(sa)} → {fmt(sb)} hari (+{fmt(sel)} hari)"],
                       f"Pelanggan rata-rata membayar dalam {fmt(sb)} hari, sebelumnya {fmt(sa)} hari.",
                       {"keterangan": f"Kas yang dapat dilepas jika DSO kembali ke {fmt(sa)} hari",
                        "nilai": round(sel / hari_b * pend, 2), "satuan": satuan})

    # 5. Beban usaha tumbuh lebih cepat dari pendapatan
    if a:
        go, gp = tumbuh(P("beban_usaha", a), P("beban_usaha", b)), tumbuh(P("pendapatan", a), P("pendapatan", b))
        if go is not None and gp is not None:
            sel = go - gp
            tingkat = "merah" if sel >= 10 else ("kuning" if sel >= 5 else None)
            if tingkat:
                tambah("overhead_naik", tingkat,
                       [f"Beban usaha tumbuh {fmt(go, 1)}%, pendapatan tumbuh {fmt(gp, 1)}%"],
                       f"Beban usaha tumbuh {fmt(go, 1)}%, lebih cepat dari pendapatan ({fmt(gp, 1)}%).")

    # 6. Pinjaman bank menopang modal kerja
    if a:
        ua, ub = P("utang_bank_total", a), P("utang_bank_total", b)
        cfoa = P("arus_kas_operasi", a)
        gu = tumbuh(ua, ub)
        icb = R("interest_coverage", b)
        if gu is not None and gu >= 25 and cfob is not None and cfoa is not None and cfob < cfoa:
            tingkat = "merah" if (icb is not None and icb < 3) else "kuning"
            bukti = [f"Utang bank {fmt_uang(ua)} → {fmt_uang(ub)} (+{fmt(gu, 1)}%) saat arus kas operasi turun"]
            ica = R("interest_coverage", a)
            if ica is not None and icb is not None:
                bukti.append(f"Interest coverage {fmt(ica, 2)}x → {fmt(icb, 2)}x")
            tambah("utang_menopang_modal_kerja", tingkat, bukti,
                   f"Utang bank naik {fmt(gu, 1)}% bersamaan dengan turunnya kas dari operasi.")

    # 7. Data tidak sinkron (dari peringatan validasi)
    pw = r.get("validasi", {}).get("peringatan", [])
    relevan = [w for w in pw if "tidak sama" in w or "berbeda" in w or "Rincian" in w]
    if relevan:
        tambah("data_tidak_sinkron", "kuning", relevan[:3],
               "Beberapa angka di laporan tidak saling cocok saat diperiksa silang.")

    temuan.sort(key=lambda t: URUT_TINGKAT[t["tingkat"]])

    # Ringkasan modal kerja
    ringkas = {}
    if a:
        lt = r["laporan_terstandar"]["neraca"]
        try:
            dmk = ((lt["piutang_usaha"][b] - lt["piutang_usaha"][a]) + (lt["persediaan"][b] - lt["persediaan"][a])
                   - (lt["utang_usaha"][b] - lt["utang_usaha"][a]))
            ringkas["tambahan_modal_kerja"] = {
                "keterangan": "Tambahan dana tertahan di piutang + persediaan - utang usaha",
                "nilai": round(dmk, 2), "satuan": satuan}
        except (KeyError, TypeError):
            pass
        ca, cb = R("ccc", a), R("ccc", b)
        if ca is not None and cb is not None:
            ringkas["cash_conversion_cycle"] = {"dari": round(ca, 1), "ke": round(cb, 1)}
    return temuan, ringkas


def lengkapi(temuan: list, peta: dict) -> list:
    out = []
    for t in temuan:
        g = peta["gejala"][t["kode"]]
        out.append({**t, "judul": g["judul"], "kemungkinan_penyebab": g["kemungkinan_penyebab"],
                    "kenapa_tidak_terlihat": g["kenapa_tidak_terlihat"], "data_pembukti": g["data_pembukti"],
                    "biasanya_tersedia_jika": g["biasanya_tersedia_jika"],
                    "pertanyaan_minggu_ini": g["pertanyaan_minggu_ini"], "kategori_solusi": g["kategori_solusi"]})
    return out


def ke_markdown_ringkas(r: dict, temuan: list, ringkas: dict, checklist: bool) -> str:
    m = r["meta"]
    L = [f"# Red Flag Operasional: {m['perusahaan']}", ""]
    if not temuan:
        L.append("Tidak ada gejala yang melewati ambang deteksi.")
    if "tambahan_modal_kerja" in ringkas and temuan:
        x = ringkas["tambahan_modal_kerja"]
        L += [f"Dana tambahan tertahan di modal kerja: **{fmt_uang(x['nilai'])} {x['satuan']}**.", ""]
    for i, t in enumerate(temuan, 1):
        ikon = "status merah" if t["tingkat"] == "merah" else "status kuning"
        if checklist:
            L += [f"- [ ] **{t['judul']}**, {ikon}. {t['ringkas']}",
                  f"  - [ ] Data pembukti: {'; '.join(t['data_pembukti'][:2])}",
                  f"  - [ ] Tanya tim: {t['pertanyaan_minggu_ini'][0]}"]
        else:
            L.append(f"{i}. **{t['judul']}**, {ikon}. {t['ringkas']} Penyebab belum bisa dipastikan dari laporan "
                     f"keuangan. *Tanya tim:* {t['pertanyaan_minggu_ini'][0]}")
    L += ["", "_Penyebab bersifat hipotesis. Alat bantu analisis, bukan nasihat investasi atau hasil audit._", "",
          "Disusun dengan TQ Board Insight | totalquality.co.id", ""]
    return "\n".join(L)


def ke_markdown(r: dict, temuan: list, ringkas: dict, gaya: str = "detail") -> str:
    if gaya in ("ringkas", "checklist"):
        return ke_markdown_ringkas(r, temuan, ringkas, gaya == "checklist")
    m = r["meta"]
    per = m["periode"]
    L = [f"# Red Flag Operasional: {m['perusahaan']}", "",
         f"Periode dibandingkan: {per[-2]} → {per[-1]}" if len(per) > 1 else f"Periode: {per[-1]}", ""]
    if not temuan:
        L += ["Tidak ada gejala yang melewati ambang deteksi. Ini **bukan** jaminan operasional sehat; "
              "laporan keuangan tahunan bisa menutupi masalah yang muncul per bulan, per produk, atau per lini.", ""]
    else:
        merah = sum(1 for t in temuan if t["tingkat"] == "merah")
        L += [f"Ditemukan **{len(temuan)} gejala** ({merah} merah, {len(temuan) - merah} kuning).", ""]
        if "tambahan_modal_kerja" in ringkas:
            x = ringkas["tambahan_modal_kerja"]
            L.append(f"- Tambahan dana yang tertahan di modal kerja (piutang + persediaan - utang usaha): "
                     f"**{fmt_uang(x['nilai'])} {x['satuan']}**")
        if "cash_conversion_cycle" in ringkas:
            c = ringkas["cash_conversion_cycle"]
            L.append(f"- Cash conversion cycle: {fmt(c['dari'])} → {fmt(c['ke'])} hari")
        L.append("")
    for i, t in enumerate(temuan, 1):
        ikon = "status merah" if t["tingkat"] == "merah" else "status kuning"
        L += [f"## {i}. {t['judul']}, {ikon}", "",
              f"**Temuan:** {t['ringkas']}", ""]
        L += [f"- {b}" for b in t["bukti"]]
        if t.get("dampak_kas") and t["dampak_kas"].get("nilai"):
            d = t["dampak_kas"]
            L.append(f"- {d['keterangan']}: sekitar {fmt_uang(d['nilai'])} {d['satuan']}")
        L += ["", "**Kemungkinan penyebab:** " + "; ".join(f"({j}) {p}" for j, p in
                                                          enumerate(t["kemungkinan_penyebab"], 1)) + ".", "",
              f"**Tidak bisa dipastikan dari laporan keuangan.** {t['kenapa_tidak_terlihat']} "
              f"Untuk membuktikannya dibutuhkan: {'; '.join(t['data_pembukti'])}. "
              f"Data ini biasanya hanya tersedia jika {t['biasanya_tersedia_jika']}.", "",
              f"**Pertanyaan untuk tim Anda minggu ini:** {t['pertanyaan_minggu_ini'][0]}", "",
              f"_Arah solusi: {t['kategori_solusi']}._", ""]
    L += ["---", "",
          "_Gejala dideteksi dengan aturan ambang umum (bukan benchmark industri) oleh "
          f"deteksi_gejala.py v{VERSI}. Penyebab bersifat hipotesis. Alat bantu analisis, bukan nasihat investasi "
          "atau hasil audit._", "",
          "Disusun dengan TQ Board Insight | totalquality.co.id", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Deteksi gejala operasional dari rasio.json")
    ap.add_argument("rasio", type=Path, help="Keluaran hitung_rasio.py --out-json")
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--gaya", choices=["ringkas", "detail", "checklist"])
    ap.add_argument("--preferensi", type=Path)
    ap.add_argument("--diam", action="store_true")
    a = ap.parse_args(argv)
    pref = json.loads(a.preferensi.read_text(encoding="utf-8-sig")) if a.preferensi and a.preferensi.exists() else {}
    gaya = a.gaya or pref.get("gaya_narasi") or "detail"
    try:
        r = json.loads(a.rasio.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Tidak bisa membaca {a.rasio}: {e}", file=sys.stderr)
        return 1
    if "rasio" not in r or "meta" not in r:
        print("File bukan keluaran hitung_rasio.py. Jalankan skill baca-laporan-keuangan dulu.", file=sys.stderr)
        return 1
    peta = json.loads(PETA.read_text(encoding="utf-8"))
    temuan, ringkas = deteksi(r)
    temuan = lengkapi(temuan, peta)
    out = {"meta": {**r["meta"], "skrip": f"deteksi_gejala.py v{VERSI}"}, "ringkasan": ringkas, "temuan": temuan}
    md = ke_markdown(r, temuan, ringkas, gaya)
    if a.out_json:
        a.out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    if a.out_md:
        a.out_md.write_text(md, encoding="utf-8")
    if not a.diam:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
