#!/usr/bin/env python3
"""Definisi format data TQ Board Insight + penulis Excel + pembuat template kosong.

Dua format:
1. LK tahunan (format standar skill baca-laporan-keuangan)  -> templates/template-lk.xlsx
2. Paket data bulanan (skill laporan-analisa)               -> templates/template-paket-data.xlsx

Pemakaian (dari root repo):  python tools/format_data.py   # menulis ulang kedua template kosong
Dependensi: openpyxl.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ============================================================ LK TAHUNAN ===
LABEL_LK = {
    "neraca": [
        ("kas_dan_setara_kas", "Kas dan setara kas", True),
        ("piutang_usaha", "Piutang usaha (neto)", True),
        ("persediaan", "Persediaan", True),
        ("aset_lancar_lainnya", "Aset lancar lainnya", False),
        ("total_aset_lancar", "TOTAL ASET LANCAR", True),
        ("aset_tetap_neto", "Aset tetap (neto)", False),
        ("aset_tidak_lancar_lainnya", "Aset tidak lancar lainnya", False),
        ("total_aset", "TOTAL ASET", True),
        ("utang_bank_jangka_pendek", "Utang bank jangka pendek (termasuk bagian lancar utang jangka panjang)", False),
        ("utang_usaha", "Utang usaha", True),
        ("liabilitas_jangka_pendek_lainnya", "Liabilitas jangka pendek lainnya", False),
        ("total_liabilitas_jangka_pendek", "TOTAL LIABILITAS JANGKA PENDEK", True),
        ("utang_bank_jangka_panjang", "Utang bank jangka panjang", False),
        ("liabilitas_jangka_panjang_lainnya", "Liabilitas jangka panjang lainnya", False),
        ("total_liabilitas", "TOTAL LIABILITAS", True),
        ("total_ekuitas", "TOTAL EKUITAS", True),
        ("saldo_laba", "Saldo laba (opsional, untuk skor Altman Z'')", False),
        ("total_liabilitas_dan_ekuitas", "TOTAL LIABILITAS DAN EKUITAS", False),
    ],
    "laba_rugi": [
        ("pendapatan", "Pendapatan", True),
        ("beban_pokok_penjualan", "Beban pokok penjualan (isi angka positif)", True),
        ("laba_kotor", "Laba kotor", False),
        ("beban_penjualan", "Beban penjualan", False),
        ("beban_umum_administrasi", "Beban umum dan administrasi", False),
        ("beban_usaha", "Total beban usaha", False),
        ("laba_usaha", "Laba usaha", False),
        ("beban_bunga", "Beban bunga / keuangan (isi angka positif)", False),
        ("pendapatan_beban_lain", "Pendapatan (beban) lain-lain, neto (negatif jika beban)", False),
        ("laba_sebelum_pajak", "Laba sebelum pajak", False),
        ("beban_pajak", "Beban pajak penghasilan (isi angka positif)", False),
        ("laba_bersih", "LABA BERSIH", True),
        ("penyusutan", "Penyusutan dan amortisasi (dari catatan / arus kas)", False),
    ],
    "arus_kas": [
        ("arus_kas_operasi", "Arus kas neto dari aktivitas operasi", True),
        ("arus_kas_investasi", "Arus kas neto dari aktivitas investasi", False),
        ("arus_kas_pendanaan", "Arus kas neto dari aktivitas pendanaan", False),
        ("belanja_modal", "Belanja modal / perolehan aset tetap (isi angka positif)", False),
        ("kas_akhir", "Kas dan setara kas akhir tahun", False),
    ],
}
SHEET_LK = {"neraca": "Neraca", "laba_rugi": "LabaRugi", "arus_kas": "ArusKas"}

# ======================================================== PAKET BULANAN ===
LABEL_PAKET = {
    "laba_rugi": [
        ("penjualan_bruto", "Penjualan bruto", False),
        ("potongan_dan_retur", "Potongan & retur penjualan (positif)", False),
        ("pendapatan", "Pendapatan neto", True),
        ("hpp_bahan", "HPP - bahan baku / barang dagangan", True),
        ("hpp_upah", "HPP - upah langsung", False),
        ("hpp_overhead", "HPP - overhead pabrik / gudang", False),
        ("hpp_penyusutan", "HPP - penyusutan", False),
        ("beban_penjualan", "Beban penjualan & distribusi", True),
        ("beban_umum_adm", "Beban umum & administrasi", True),
        ("beban_penyusutan_usaha", "Beban penyusutan (di luar HPP)", False),
        ("pendapatan_beban_lain", "Pendapatan (beban) lain-lain, neto (negatif jika beban)", False),
        ("beban_bunga", "Beban bunga", False),
        ("beban_pajak", "Beban pajak penghasilan", False),
        ("laba_bersih", "LABA BERSIH (untuk pengecekan)", True),
    ],
    "neraca": [
        ("kas", "Kas dan setara kas", True),
        ("piutang_usaha_bruto", "Piutang usaha (bruto)", True),
        ("cadangan_kerugian_piutang", "Cadangan kerugian piutang (positif)", False),
        ("persediaan_bahan_baku", "Persediaan - bahan baku & kemasan", False),
        ("persediaan_barang_dalam_proses", "Persediaan - barang dalam proses (WIP)", False),
        ("persediaan_barang_jadi", "Persediaan - barang jadi / dagangan", True),
        ("uang_muka_dan_dibayar_dimuka", "Uang muka & biaya dibayar di muka", False),
        ("aset_tetap_perolehan", "Aset tetap - harga perolehan", True),
        ("akumulasi_penyusutan", "Akumulasi penyusutan (positif)", True),
        ("aset_tidak_lancar_lain", "Aset tidak lancar lainnya", False),
        ("utang_usaha", "Utang usaha", True),
        ("utang_bank_pendek", "Utang bank jangka pendek", False),
        ("bagian_lancar_utang_panjang", "Bagian lancar utang bank jangka panjang", False),
        ("beban_akrual", "Beban akrual & liabilitas pendek lain", False),
        ("utang_pajak", "Utang pajak", False),
        ("utang_bank_panjang", "Utang bank jangka panjang (setelah bagian lancar)", False),
        ("liabilitas_imbalan_kerja", "Liabilitas imbalan kerja", False),
        ("modal_disetor", "Modal disetor", True),
        ("saldo_laba", "Saldo laba", True),
    ],
    "arus_kas": [
        ("arus_kas_operasi", "Arus kas neto dari aktivitas operasi", True),
        ("belanja_modal", "Belanja modal (positif)", False),
        ("penerimaan_pinjaman_panjang", "Penerimaan pinjaman bank jangka panjang", False),
        ("pembayaran_pinjaman_panjang", "Pembayaran pinjaman bank jangka panjang (positif)", False),
        ("perubahan_utang_bank_pendek", "Penambahan (pelunasan) utang bank jangka pendek, neto", False),
        ("dividen", "Pembayaran dividen (positif)", False),
        ("kas_akhir", "Kas akhir bulan (untuk pengecekan)", False),
    ],
    "target": [
        ("pendapatan", "Target pendapatan neto", False),
        ("laba_kotor", "Target laba kotor", False),
        ("beban_usaha", "Target beban usaha (penjualan + umum + penyusutan usaha)", False),
        ("laba_bersih", "Target laba bersih", False),
    ],
}
SHEET_PAKET = {"laba_rugi": "LabaRugi", "neraca": "Neraca", "arus_kas": "ArusKas", "target": "Target"}

# Tabel data operasional (TIER 2, opsional): nama sheet -> kolom (kunci, judul)
TABEL_OPS = {
    "piutang_pelanggan": ("Piutang_Pelanggan", [
        ("pelanggan", "Pelanggan"), ("wilayah", "Wilayah/segmen"), ("terafiliasi", "Pihak berelasi (Ya/Tidak)"),
        ("batas_kredit", "Batas kredit"), ("termin_hari", "Termin (hari)"), ("penjualan_ytd", "Penjualan YTD"),
        ("umur_0_30", "Belum jatuh tempo / 0-30 hr"), ("umur_31_60", "31-60 hr"), ("umur_61_90", "61-90 hr"),
        ("umur_90_plus", ">90 hr"), ("margin_kotor_pct", "Margin kotor (%)"), ("catatan", "Catatan")]),
    "penjualan_produk": ("Penjualan_Produk", [
        ("periode", "Periode (YYYY-MM)"), ("produk", "Produk / kelompok"), ("pendapatan", "Pendapatan neto"),
        ("hpp", "HPP"), ("volume", "Volume"), ("satuan", "Satuan volume")]),
    "pemasok": ("Pemasok", [
        ("pemasok", "Pemasok"), ("kategori", "Kategori"), ("pembelian_ytd", "Pembelian YTD"),
        ("perubahan_harga_pct", "Perubahan harga 12 bln (%)"), ("dpo_hari", "Rata-rata hari bayar"),
        ("catatan", "Catatan")]),
    "persediaan_rincian": ("Persediaan_Rincian", [
        ("item", "Item / SKU / style"), ("jenis", "Jenis (bahan/wip/jadi)"), ("nilai", "Nilai"),
        ("umur_0_30", "0-30 hr"), ("umur_31_90", "31-90 hr"), ("umur_91_180", "91-180 hr"),
        ("umur_180_plus", ">180 hr"), ("catatan", "Catatan")]),
    "produksi_lini": ("Produksi_Lini", [
        ("lini", "Lini / gudang"), ("rencana", "Rencana output"), ("realisasi", "Realisasi output"),
        ("satuan", "Satuan"), ("wip", "WIP / stok"), ("reject_pct", "Reject / retur (%)"),
        ("utilisasi_pct", "Utilisasi (%)"), ("catatan", "Catatan")]),
}
SHEET_OPS_BULANAN = "Operasional"

AMBANG_DEFAULT_KOLOM = [("kpi", "Kode KPI"), ("nama", "Nama"), ("waspada", "Batas waspada"),
                        ("kritis", "Batas kritis"), ("arah", "Arah lebih baik (tinggi/rendah)")]


def _gaya():
    from openpyxl.styles import Font, PatternFill
    return Font(bold=True), PatternFill("solid", fgColor="FFF2CC"), PatternFill("solid", fgColor="DDEBF7")


# ------------------------------------------------------------------ LK ----
def tulis_lk_excel(path: Path, data: dict | None) -> None:
    """Tulis LK tahunan format standar (data=None -> template kosong)."""
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    bold, isi, _ = _gaya()
    wb = Workbook()
    info = wb.active
    info.title = "Info"
    periode = data["periode"] if data else ["2024", "2025"]
    info.append(["kunci", "nilai"])
    for k in ("perusahaan", "mata_uang", "satuan", "sumber"):
        info.append([k, (data or {}).get(k, {"mata_uang": "IDR", "satuan": "juta"}.get(k, ""))])
    info["A1"].font = info["B1"].font = bold
    petunjuk = [
        "Petunjuk:",
        "1. Isi sheet Neraca, LabaRugi, ArusKas. Kolom 'kode' JANGAN diubah.",
        "2. Judul kolom C dst. = label periode (mis. 2024, 2025). Urut dari terlama.",
        "3. Satu satuan untuk semua angka (lihat 'satuan'). Beban diisi angka POSITIF.",
        "4. Baris bertanda * wajib diisi.",
        "5. Periode < 1 tahun: isi baris 'hari_periode' di sheet LabaRugi (mis. 90).",
        "6. Ubah ke JSON: python scripts/baca_excel.py file.xlsx --out lk.json",
    ]
    for i, t in enumerate(petunjuk, start=8):
        cell = info.cell(i, 1, t)
        if i == 8:
            cell.font = bold
    info.column_dimensions["A"].width = 18
    info.column_dimensions["B"].width = 70
    for bagian, label in LABEL_LK.items():
        ws = wb.create_sheet(SHEET_LK[bagian])
        ws.append(["kode", "uraian"] + periode)
        for c in ws[1]:
            c.font = bold
        baris = list(label) + ([("hari_periode", "Jumlah hari dalam periode (kosongkan jika 1 tahun)", False)]
                               if bagian == "laba_rugi" else [])
        for kode, uraian, wajib in baris:
            nilai = [None if (not data or kode == "hari_periode") else data[bagian].get(kode, {}).get(p)
                     for p in periode]
            ws.append([kode, uraian + (" *" if wajib else "")] + nilai)
            r = ws.max_row
            if uraian.startswith(("TOTAL", "LABA")):
                ws.cell(r, 2).font = bold
            for j in range(len(periode)):
                c = ws.cell(r, 3 + j)
                c.number_format = '#,##0;(#,##0);"-"'
                if not data:
                    c.fill = isi
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 66
        for j in range(len(periode)):
            ws.column_dimensions[get_column_letter(3 + j)].width = 14
        ws.freeze_panes = "C2"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


# --------------------------------------------------------------- PAKET ----
def tulis_paket_excel(path: Path, paket: dict | None, sertakan_operasional: bool = True) -> None:
    """Tulis paket data bulanan. paket=None -> template kosong (dengan contoh label bulan)."""
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    bold, isi, biru = _gaya()
    wb = Workbook()
    info = wb.active
    info.title = "Info"
    meta = (paket or {}).get("info", {})
    bulan = (paket or {}).get("bulan") or ["2025-01", "2025-02", "2025-03"]
    bulan_neraca = (paket or {}).get("bulan_neraca") or ["2024-12"] + bulan
    info.append(["kunci", "nilai", "keterangan"])
    for k, ket in [("perusahaan", "Nama perusahaan"), ("industri", "Bidang usaha"), ("mata_uang", "IDR"),
                   ("satuan", "Satuan semua angka uang, mis. juta"),
                   ("bulan_aktif", "Bulan laporan, format YYYY-MM (mis. 2026-10)"),
                   ("sumber", "Sumber data / catatan")]:
        info.append([k, meta.get(k, {"mata_uang": "IDR", "satuan": "juta"}.get(k, "")), ket])
    for c in info[1]:
        c.font = bold
    petunjuk = [
        "PETUNJUK PENGISIAN",
        "1. Sheet WAJIB: Info, LabaRugi, Neraca, ArusKas. Kolom 'kode' jangan diubah; judul kolom bulan = YYYY-MM.",
        "2. Minimal 13 bulan (agar ada pembanding tahun lalu). Disarankan 22+ bulan. Neraca butuh 1 bulan sebelum bulan pertama L/R.",
        "3. Semua beban, belanja modal, cicilan, dividen, cadangan & akumulasi penyusutan diisi angka POSITIF.",
        "4. Sheet Target & Ambang_KPI opsional. Tanpa Target, laporan menandai 'PERLU DATA' pada pembanding target.",
        "5. Sheet data operasional (Piutang_Pelanggan, Penjualan_Produk, Pemasok, Persediaan_Rincian, Operasional,",
        "   Produksi_Lini) OPSIONAL. Tanpa sheet ini, bagian terkait laporan ditandai 'PERLU DATA'.",
        "6. Data rahasia? Samarkan dulu: python scripts/samarkan_paket.py file.xlsx --out file-samaran.xlsx",
    ]
    for i, t in enumerate(petunjuk, start=10):
        cell = info.cell(i, 1, t)
        if i == 10:
            cell.font = bold
    info.column_dimensions["A"].width = 16
    info.column_dimensions["B"].width = 44
    info.column_dimensions["C"].width = 60

    def lembar_bulanan(nama, label, kolom, sumber):
        ws = wb.create_sheet(nama)
        ws.append(["kode", "uraian"] + kolom)
        for c in ws[1]:
            c.font = bold
        for kode, uraian, wajib in label:
            nilai = [None if sumber is None else sumber.get(kode, {}).get(b) for b in kolom]
            ws.append([kode, uraian + (" *" if wajib else "")] + nilai)
            r = ws.max_row
            for j in range(len(kolom)):
                c = ws.cell(r, 3 + j)
                c.number_format = '#,##0;(#,##0);"-"'
                if sumber is None:
                    c.fill = isi
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 50
        for j in range(len(kolom)):
            ws.column_dimensions[get_column_letter(3 + j)].width = 10.5
        ws.freeze_panes = "C2"
        return ws

    lembar_bulanan("LabaRugi", LABEL_PAKET["laba_rugi"], bulan, (paket or {}).get("laba_rugi"))
    lembar_bulanan("Neraca", LABEL_PAKET["neraca"], bulan_neraca, (paket or {}).get("neraca"))
    lembar_bulanan("ArusKas", LABEL_PAKET["arus_kas"], bulan, (paket or {}).get("arus_kas"))
    tgt = (paket or {}).get("target")
    if paket is None or tgt:
        kolom_t = sorted({b for v in (tgt or {}).values() for b in v}) or bulan
        lembar_bulanan("Target", LABEL_PAKET["target"], kolom_t, tgt)
    amb = (paket or {}).get("ambang_kpi")
    if paket is None or amb:
        ws = wb.create_sheet("Ambang_KPI")
        ws.append([j for _, j in AMBANG_DEFAULT_KOLOM])
        for c in ws[1]:
            c.font = bold
        for row in (amb or []):
            ws.append([row.get(k) for k, _ in AMBANG_DEFAULT_KOLOM])
        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 36

    if sertakan_operasional:
        for kunci, (nama, kolom) in TABEL_OPS.items():
            rows = (paket or {}).get(kunci)
            if paket is not None and not rows:
                continue
            ws = wb.create_sheet(nama)
            ws.append([k for k, _ in kolom])
            ws.append([j for _, j in kolom])
            for c in ws[1]:
                c.font = bold
            for c in ws[2]:
                c.fill = biru
            for row in rows or []:
                ws.append([row.get(k) for k, _ in kolom])
            for j, (k, _) in enumerate(kolom, start=1):
                ws.column_dimensions[get_column_letter(j)].width = 34 if k in ("catatan", "pelanggan", "item", "produk", "pemasok") else 14
            ws.freeze_panes = "A3"
        ops = (paket or {}).get("operasional")
        if paket is None or ops:
            kolom_o = sorted({b for v in (ops or {}).values() for b in v["nilai"]}) or bulan
            ws = wb.create_sheet(SHEET_OPS_BULANAN)
            ws.append(["kode", "uraian", "satuan", "arah"] + kolom_o)
            for c in ws[1]:
                c.font = bold
            for kode, v in (ops or {}).items():
                ws.append([kode, v["uraian"], v["satuan"], v.get("arah", "")] + [v["nilai"].get(b) for b in kolom_o])
            ws.column_dimensions["A"].width = 26
            ws.column_dimensions["B"].width = 44
            ws.freeze_panes = "E2"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> None:
    lk = ROOT / "skills" / "baca-laporan-keuangan" / "templates" / "template-lk.xlsx"
    tulis_lk_excel(lk, None)
    pk = ROOT / "skills" / "laporan-analisa" / "templates" / "template-paket-data.xlsx"
    tulis_paket_excel(pk, None)
    print("Template ditulis:", lk.relative_to(ROOT), "dan", pk.relative_to(ROOT))


if __name__ == "__main__":
    main()
