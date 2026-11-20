#!/usr/bin/env python3
"""Konverter CSV dan Excel format bebas -> format standar Corporate Health Check.

Mendukung dua target format:
1. tahunan : JSON format standar (`lk.json`) dan/atau Excel `template-lk.xlsx`
             untuk skill `baca-laporan-keuangan`, `red-flag-operasional`, `board-brief`.
2. bulanan : Excel `template-paket-data.xlsx` dan/atau JSON paket bulanan
             untuk skill `laporan-analisa` dan `uji-ketahanan-kas`.

Pemakaian (dari root repo):
    python tools/konversi_data.py laporan-keuangan.xlsx --out lk.json
    python tools/konversi_data.py neraca.csv labarugi.csv aruskas.csv --out lk.json
    python tools/konversi_data.py ekspor-erp.csv --jenis bulanan --out paket.xlsx
    python tools/konversi_data.py laporan-bebas.xlsx --tulis-pemetaan pemetaan.json
    python tools/konversi_data.py laporan-bebas.xlsx --pemetaan pemetaan.json --out lk.json

Exit code: 0 sukses | 1 berkas/argumen tidak valid | 2 validasi neraca / kolom wajib gagal.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from format_data import LABEL_LK, LABEL_PAKET, tulis_lk_excel, tulis_paket_excel  # noqa: E402
from trial_balance import (  # noqa: E402
    deteksi_kolom_tb,
    ekstrak_baris_tb,
    hitung_arus_kas_tidak_langsung,
    konversi_tb_ke_mapped,
)

BULAN_MAP = {
    "jan": 1, "januari": 1, "january": 1,
    "feb": 2, "februari": 2, "february": 2,
    "mar": 3, "maret": 3, "march": 3,
    "apr": 4, "april": 4,
    "mei": 5, "may": 5,
    "jun": 6, "juni": 6, "june": 6,
    "jul": 7, "juli": 7, "july": 7,
    "agu": 8, "agt": 8, "agustus": 8, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10, "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "des": 12, "desember": 12, "dec": 12, "december": 12,
}

POS_POSITIF = {
    "tahunan": {
        "beban_pokok_penjualan", "beban_penjualan", "beban_umum_administrasi",
        "beban_usaha", "beban_bunga", "beban_pajak", "penyusutan", "belanja_modal",
    },
    "bulanan": {
        "potongan_dan_retur", "hpp_bahan", "hpp_upah", "hpp_overhead", "hpp_penyusutan",
        "beban_penjualan", "beban_umum_adm", "beban_penyusutan_usaha", "beban_bunga",
        "beban_pajak", "cadangan_kerugian_piutang", "akumulasi_penyusutan",
        "belanja_modal", "pembayaran_pinjaman_panjang", "dividen",
    },
}

WAJIB_TAHUNAN = {
    "neraca": [
        "kas_dan_setara_kas", "piutang_usaha", "persediaan", "total_aset_lancar",
        "total_aset", "utang_usaha", "total_liabilitas_jangka_pendek",
        "total_liabilitas", "total_ekuitas",
    ],
    "laba_rugi": ["pendapatan", "beban_pokok_penjualan", "laba_bersih"],
    "arus_kas": ["arus_kas_operasi"],
}

WAJIB_BULANAN = {
    bag: [kode for kode, _, wajib in items if wajib]
    for bag, items in LABEL_PAKET.items()
    if bag != "target"
}

KODE_VALID = {
    "tahunan": {bag: {k for k, _, _ in items} for bag, items in LABEL_LK.items()},
    "bulanan": {bag: {k for k, _, _ in items} for bag, items in LABEL_PAKET.items()},
}

HEADER_BAGIAN = {
    "aset", "aktiva", "aset lancar", "aktiva lancar", "aset tidak lancar",
    "aktiva tidak lancar", "aset tetap", "liabilitas", "kewajiban",
    "liabilitas jangka pendek", "kewajiban jangka pendek", "utang lancar",
    "liabilitas jangka panjang", "kewajiban jangka panjang", "ekuitas", "modal",
    "liabilitas dan ekuitas", "kewajiban dan ekuitas", "pendapatan usaha",
    "beban usaha", "beban operasional", "aktivitas operasi", "arus kas dari aktivitas operasi",
    "aktivitas investasi", "arus kas dari aktivitas investasi",
    "aktivitas pendanaan", "arus kas dari aktivitas pendanaan",
    "assets", "current assets", "non current assets", "liabilities",
    "current liabilities", "non current liabilities", "equity",
    "operating expenses", "operating activities", "investing activities", "financing activities",
}

# Daftar (bagian, kode, daftar frasa sinonim) - frasa lebih spesifik diletakkan lebih dulu.
SINONIM_TAHUNAN: list[tuple[str, str, tuple[str, ...]]] = [
    # --- NERACA ---
    ("neraca", "kas_dan_setara_kas", (
        "kas dan setara kas", "kas dan bank", "kas & setara kas", "kas & bank",
        "cash and cash equivalents", "cash & cash equivalents", "cash and bank", "kas",
    )),
    ("neraca", "piutang_usaha", (
        "piutang usaha neto", "piutang usaha bersih", "piutang usaha",
        "piutang dagang", "trade receivables", "accounts receivable",
    )),
    ("neraca", "persediaan", (
        "persediaan neto", "persediaan bersih", "persediaan barang", "persediaan",
        "inventories", "inventory", "stok barang",
    )),
    ("neraca", "aset_lancar_lainnya", (
        "aset lancar lainnya", "aset lancar lain lain", "aset lancar lain",
        "aktiva lancar lainnya", "uang muka dan biaya dibayar dimuka",
        "biaya dibayar dimuka", "biaya dibayar di muka", "uang muka",
        "pajak dibayar dimuka", "pajak dibayar di muka", "piutang lain lain",
        "other current assets", "prepaid expenses",
    )),
    ("neraca", "total_aset_lancar", (
        "total aset lancar", "jumlah aset lancar", "total aktiva lancar",
        "jumlah aktiva lancar", "total current assets",
    )),
    ("neraca", "aset_tetap_neto", (
        "aset tetap neto", "aset tetap bersih", "aset tetap setelah penyusutan",
        "aset tetap", "aktiva tetap neto", "aktiva tetap",
        "property plant and equipment", "fixed assets", "ppe",
    )),
    ("neraca", "aset_tidak_lancar_lainnya", (
        "aset tidak lancar lainnya", "aset tidak lancar lain lain", "aset tidak lancar lain",
        "aktiva tidak lancar lainnya", "properti investasi", "aset hak guna",
        "aset pajak tangguhan", "aset tak berwujud", "aset takberwujud",
        "goodwill", "other non current assets", "intangible assets",
    )),
    ("neraca", "total_aset", (
        "total aset", "jumlah aset", "total aktiva", "jumlah aktiva", "total assets",
    )),
    ("neraca", "utang_bank_jangka_pendek", (
        "utang bank jangka pendek", "hutang bank jangka pendek",
        "pinjaman bank jangka pendek", "pinjaman jangka pendek",
        "bagian lancar utang bank jangka panjang", "bagian lancar pinjaman jangka panjang",
        "utang bank jatuh tempo dalam satu tahun", "cerukan", "short term bank loans",
        "current portion of long term debt", "short term debt",
    )),
    ("neraca", "utang_usaha", (
        "utang usaha", "hutang usaha", "utang dagang", "hutang dagang",
        "trade payables", "accounts payable",
    )),
    ("neraca", "liabilitas_jangka_pendek_lainnya", (
        "liabilitas jangka pendek lainnya", "liabilitas jangka pendek lain",
        "kewajiban jangka pendek lainnya", "utang lancar lainnya",
        "beban akrual", "biaya masih harus dibayar", "utang pajak", "hutang pajak",
        "uang muka pelanggan", "pendapatan diterima dimuka", "utang lain lain",
        "liabilitas sewa jangka pendek", "other current liabilities", "accrued expenses",
    )),
    ("neraca", "total_liabilitas_jangka_pendek", (
        "total liabilitas jangka pendek", "jumlah liabilitas jangka pendek",
        "total kewajiban jangka pendek", "jumlah kewajiban jangka pendek",
        "total utang lancar", "total current liabilities",
    )),
    ("neraca", "utang_bank_jangka_panjang", (
        "utang bank jangka panjang", "hutang bank jangka panjang",
        "pinjaman bank jangka panjang", "pinjaman jangka panjang",
        "utang jangka panjang setelah dikurangi bagian lancar",
        "long term bank loans", "long term debt",
    )),
    ("neraca", "liabilitas_jangka_panjang_lainnya", (
        "liabilitas jangka panjang lainnya", "liabilitas jangka panjang lain",
        "kewajiban jangka panjang lainnya", "liabilitas imbalan kerja",
        "liabilitas pajak tangguhan", "liabilitas sewa jangka panjang",
        "other non current liabilities", "employee benefits liability",
    )),
    ("neraca", "total_liabilitas", (
        "total liabilitas", "jumlah liabilitas", "total kewajiban",
        "jumlah kewajiban", "total liabilities",
    )),
    ("neraca", "saldo_laba", (
        "saldo laba", "laba ditahan", "retained earnings", "defisit",
    )),
    ("neraca", "total_liabilitas_dan_ekuitas", (
        "total liabilitas dan ekuitas", "jumlah liabilitas dan ekuitas",
        "total kewajiban dan ekuitas", "jumlah kewajiban dan ekuitas",
        "total pasiva", "total liabilities and equity",
    )),
    ("neraca", "total_ekuitas", (
        "total ekuitas", "jumlah ekuitas", "total modal", "jumlah modal",
        "ekuitas bersih", "total equity", "total shareholders equity",
    )),
    # --- LABA RUGI ---
    ("laba_rugi", "pendapatan", (
        "pendapatan neto", "pendapatan bersih", "penjualan neto", "penjualan bersih",
        "pendapatan usaha", "pendapatan kontrak", "pendapatan", "penjualan",
        "omzet", "revenue", "net sales", "sales",
    )),
    ("laba_rugi", "beban_pokok_penjualan", (
        "beban pokok penjualan", "beban pokok pendapatan", "harga pokok penjualan",
        "harga pokok produksi", "hpp", "cogs", "cost of goods sold", "cost of revenue",
    )),
    ("laba_rugi", "laba_kotor", (
        "laba kotor", "laba bruto", "gross profit",
    )),
    ("laba_rugi", "beban_penjualan", (
        "beban penjualan dan distribusi", "beban penjualan", "biaya penjualan",
        "beban pemasaran", "selling expenses", "selling and distribution expenses",
    )),
    ("laba_rugi", "beban_umum_administrasi", (
        "beban umum dan administrasi", "beban umum & administrasi",
        "biaya umum dan administrasi", "beban administrasi dan umum",
        "general and administrative expenses", "g&a expenses",
    )),
    ("laba_rugi", "beban_usaha", (
        "total beban usaha", "jumlah beban usaha", "beban usaha",
        "total beban operasional", "total operating expenses", "operating expenses", "opex",
    )),
    ("laba_rugi", "laba_usaha", (
        "laba usaha", "laba operasional", "laba operasi", "ebit", "operating profit", "operating income",
    )),
    ("laba_rugi", "beban_bunga", (
        "beban bunga", "beban keuangan", "biaya bunga", "biaya keuangan",
        "interest expense", "finance costs",
    )),
    ("laba_rugi", "pendapatan_beban_lain", (
        "pendapatan beban lain lain neto", "pendapatan beban lain lain",
        "pendapatan dan beban lain lain", "penghasilan beban lain lain",
        "pendapatan lain lain neto", "beban lain lain neto",
        "other income expenses net", "other income net",
    )),
    ("laba_rugi", "laba_sebelum_pajak", (
        "laba sebelum pajak", "rugi sebelum pajak", "laba rugi sebelum pajak",
        "profit before tax", "earnings before tax", "ebt",
    )),
    ("laba_rugi", "beban_pajak", (
        "beban pajak penghasilan", "beban pajak", "pajak penghasilan",
        "income tax expense", "tax expense",
    )),
    ("laba_rugi", "laba_bersih", (
        "laba bersih", "laba tahun berjalan", "laba periode berjalan",
        "laba rugi tahun berjalan", "laba neto", "net profit", "net income", "profit for the year",
    )),
    ("laba_rugi", "penyusutan", (
        "penyusutan dan amortisasi", "beban penyusutan dan amortisasi",
        "depresiasi dan amortisasi", "penyusutan", "depreciation and amortization",
    )),
    # --- ARUS KAS ---
    ("arus_kas", "arus_kas_operasi", (
        "arus kas neto dari aktivitas operasi", "arus kas bersih dari aktivitas operasi",
        "arus kas diperoleh dari aktivitas operasi", "arus kas operasi",
        "kas neto dari aktivitas operasi", "operating cash flow",
        "net cash from operating activities", "net cash provided by operating activities",
    )),
    ("arus_kas", "arus_kas_investasi", (
        "arus kas neto dari aktivitas investasi", "arus kas bersih dari aktivitas investasi",
        "arus kas investasi", "kas neto untuk aktivitas investasi",
        "investing cash flow", "net cash used in investing activities",
    )),
    ("arus_kas", "arus_kas_pendanaan", (
        "arus kas neto dari aktivitas pendanaan", "arus kas bersih dari aktivitas pendanaan",
        "arus kas pendanaan", "kas neto dari aktivitas pendanaan",
        "financing cash flow", "net cash from financing activities",
    )),
    ("arus_kas", "belanja_modal", (
        "belanja modal", "perolehan aset tetap", "pembelian aset tetap",
        "capex", "capital expenditure", "additions to property plant and equipment",
    )),
    ("arus_kas", "kas_akhir", (
        "kas dan setara kas akhir tahun", "kas dan setara kas akhir periode",
        "kas akhir tahun", "kas akhir periode", "kas akhir",
        "cash and cash equivalents at end of year", "ending cash",
    )),
]

SINONIM_BULANAN: list[tuple[str, str, tuple[str, ...]]] = [
    # --- LABA RUGI ---
    ("laba_rugi", "penjualan_bruto", (
        "penjualan bruto", "penjualan kotor", "pendapatan bruto", "gross sales",
    )),
    ("laba_rugi", "potongan_dan_retur", (
        "potongan dan retur penjualan", "potongan & retur penjualan",
        "retur dan potongan penjualan", "diskon penjualan", "sales returns and discounts",
    )),
    ("laba_rugi", "pendapatan", (
        "pendapatan neto", "pendapatan bersih", "penjualan neto", "penjualan bersih",
        "pendapatan usaha", "pendapatan", "penjualan", "omzet", "revenue", "net sales",
    )),
    ("laba_rugi", "hpp_bahan", (
        "hpp bahan baku", "hpp bahan", "bahan baku dan kemasan", "pemakaian bahan baku",
        "harga pokok barang dagangan", "raw materials cost", "cost of materials",
    )),
    ("laba_rugi", "hpp_upah", (
        "hpp upah langsung", "upah langsung", "tenaga kerja langsung", "direct labor",
    )),
    ("laba_rugi", "hpp_overhead", (
        "hpp overhead", "overhead pabrik", "overhead gudang", "biaya overhead pabrik",
        "manufacturing overhead",
    )),
    ("laba_rugi", "hpp_penyusutan", (
        "hpp penyusutan", "penyusutan produksi", "penyusutan pabrik", "depreciation cogs",
    )),
    ("laba_rugi", "beban_penjualan", (
        "beban penjualan dan distribusi", "beban penjualan & distribusi",
        "beban penjualan", "biaya penjualan", "beban pemasaran", "selling expenses",
    )),
    ("laba_rugi", "beban_umum_adm", (
        "beban umum dan administrasi", "beban umum & administrasi", "beban umum adm",
        "biaya umum dan administrasi", "general and administrative expenses",
    )),
    ("laba_rugi", "beban_penyusutan_usaha", (
        "beban penyusutan di luar hpp", "beban penyusutan usaha",
        "penyusutan dan amortisasi usaha", "penyusutan kantor", "operating depreciation",
    )),
    ("laba_rugi", "pendapatan_beban_lain", (
        "pendapatan beban lain lain neto", "pendapatan beban lain lain",
        "pendapatan dan beban lain lain", "pendapatan lain lain neto",
        "other income expenses net",
    )),
    ("laba_rugi", "beban_bunga", (
        "beban bunga", "beban keuangan", "biaya bunga", "interest expense", "finance costs",
    )),
    ("laba_rugi", "beban_pajak", (
        "beban pajak penghasilan", "beban pajak", "pajak penghasilan", "income tax expense",
    )),
    ("laba_rugi", "laba_bersih", (
        "laba bersih", "laba periode berjalan", "laba bulan berjalan",
        "net profit", "net income",
    )),
    # --- NERACA ---
    ("neraca", "kas", (
        "kas dan setara kas", "kas dan bank", "kas & setara kas", "kas", "cash and cash equivalents",
    )),
    ("neraca", "piutang_usaha_bruto", (
        "piutang usaha bruto", "piutang usaha kotor", "piutang usaha",
        "piutang dagang", "accounts receivable", "trade receivables",
    )),
    ("neraca", "cadangan_kerugian_piutang", (
        "cadangan kerugian piutang", "penyisihan piutang tak tertagih", "allowance for doubtful accounts",
    )),
    ("neraca", "persediaan_bahan_baku", (
        "persediaan bahan baku", "persediaan bahan baku dan kemasan", "bahan baku", "raw materials",
    )),
    ("neraca", "persediaan_barang_dalam_proses", (
        "persediaan barang dalam proses", "barang dalam proses", "persediaan wip", "work in process",
    )),
    ("neraca", "persediaan_barang_jadi", (
        "persediaan barang jadi", "barang jadi", "barang dagangan", "persediaan dagang", "finished goods",
    )),
    ("neraca", "uang_muka_dan_dibayar_dimuka", (
        "uang muka dan biaya dibayar dimuka", "uang muka & biaya dibayar di muka",
        "biaya dibayar dimuka", "biaya dibayar di muka", "uang muka", "prepaid expenses",
    )),
    ("neraca", "aset_tetap_perolehan", (
        "aset tetap harga perolehan", "aset tetap perolehan", "harga perolehan aset tetap",
        "aset tetap bruto", "property plant and equipment gross",
    )),
    ("neraca", "akumulasi_penyusutan", (
        "akumulasi penyusutan", "akumulasi depresiasi", "accumulated depreciation",
    )),
    ("neraca", "aset_tidak_lancar_lain", (
        "aset tidak lancar lainnya", "aset tidak lancar lain", "aktiva tidak lancar lainnya",
        "other non current assets",
    )),
    ("neraca", "utang_usaha", (
        "utang usaha", "hutang usaha", "utang dagang", "accounts payable", "trade payables",
    )),
    ("neraca", "utang_bank_pendek", (
        "utang bank jangka pendek", "hutang bank jangka pendek", "pinjaman bank jangka pendek",
        "cerukan", "short term bank loans",
    )),
    ("neraca", "bagian_lancar_utang_panjang", (
        "bagian lancar utang bank jangka panjang", "bagian lancar utang jangka panjang",
        "current portion of long term debt",
    )),
    ("neraca", "beban_akrual", (
        "beban akrual", "beban akrual dan liabilitas pendek lain", "biaya masih harus dibayar",
        "liabilitas jangka pendek lainnya", "accrued expenses",
    )),
    ("neraca", "utang_pajak", (
        "utang pajak", "hutang pajak", "taxes payable",
    )),
    ("neraca", "utang_bank_panjang", (
        "utang bank jangka panjang", "hutang bank jangka panjang", "pinjaman bank jangka panjang",
        "long term bank loans", "long term debt",
    )),
    ("neraca", "liabilitas_imbalan_kerja", (
        "liabilitas imbalan kerja", "kewajiban imbalan kerja", "imbalan pasca kerja",
        "employee benefits liability",
    )),
    ("neraca", "modal_disetor", (
        "modal disetor", "modal saham", "share capital", "paid in capital",
    )),
    ("neraca", "saldo_laba", (
        "saldo laba", "laba ditahan", "retained earnings",
    )),
    # --- ARUS KAS ---
    ("arus_kas", "arus_kas_operasi", (
        "arus kas neto dari aktivitas operasi", "arus kas bersih dari aktivitas operasi",
        "arus kas operasi", "operating cash flow", "net cash from operating activities",
    )),
    ("arus_kas", "belanja_modal", (
        "belanja modal", "perolehan aset tetap", "capex", "capital expenditure",
    )),
    ("arus_kas", "penerimaan_pinjaman_panjang", (
        "penerimaan pinjaman bank jangka panjang", "penarikan pinjaman jangka panjang",
        "proceeds from long term borrowings",
    )),
    ("arus_kas", "pembayaran_pinjaman_panjang", (
        "pembayaran pinjaman bank jangka panjang", "cicilan pinjaman jangka panjang",
        "pelunasan pinjaman jangka panjang", "repayment of long term borrowings",
    )),
    ("arus_kas", "perubahan_utang_bank_pendek", (
        "penambahan pelunasan utang bank jangka pendek neto",
        "perubahan utang bank jangka pendek", "net short term borrowings",
    )),
    ("arus_kas", "dividen", (
        "pembayaran dividen", "dividen dibayarkan", "dividen", "dividends paid",
    )),
    ("arus_kas", "kas_akhir", (
        "kas akhir bulan", "kas dan setara kas akhir bulan", "kas akhir periode",
        "kas dan setara kas akhir periode", "ending cash",
    )),
    # --- TARGET ---
    ("target", "pendapatan", ("target pendapatan neto", "target pendapatan", "anggaran pendapatan")),
    ("target", "laba_kotor", ("target laba kotor", "anggaran laba kotor")),
    ("target", "beban_usaha", ("target beban usaha", "anggaran beban usaha")),
    ("target", "laba_bersih", ("target laba bersih", "anggaran laba bersih")),
]

# Fallback khusus jika data bulanan hanya menyajikan pos ringkas (tanpa rincian komponen).
FALLBACK_BULANAN = {
    ("laba_rugi", "beban pokok penjualan"): ("laba_rugi", "hpp_bahan"),
    ("laba_rugi", "harga pokok penjualan"): ("laba_rugi", "hpp_bahan"),
    ("laba_rugi", "hpp"): ("laba_rugi", "hpp_bahan"),
    ("laba_rugi", "cogs"): ("laba_rugi", "hpp_bahan"),
    ("laba_rugi", "cost of goods sold"): ("laba_rugi", "hpp_bahan"),
    ("laba_rugi", "penyusutan"): ("laba_rugi", "beban_penyusutan_usaha"),
    ("laba_rugi", "penyusutan dan amortisasi"): ("laba_rugi", "beban_penyusutan_usaha"),
    ("neraca", "persediaan"): ("neraca", "persediaan_barang_jadi"),
    ("neraca", "inventories"): ("neraca", "persediaan_barang_jadi"),
    ("neraca", "inventory"): ("neraca", "persediaan_barang_jadi"),
    ("neraca", "aset tetap"): ("neraca", "aset_tetap_perolehan"),
    ("neraca", "aset tetap neto"): ("neraca", "aset_tetap_perolehan"),
}


# =========================================================== utilitas teks ===
def bersihkan_label(teks: Any) -> str:
    """Normalisasi nama akun untuk pencocokan sinonim."""
    s = str(teks or "").strip().lower()
    s = re.sub(r"[\(\[].*?[\)\]]", " ", s)
    s = re.sub(r"^\s*(?:[ivxlcdm]+|\d+(?:[.\-]\d+)*|[a-z])(?:[.)\-:]|\s+)\s*", "", s)
    s = s.replace("&", " dan ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_angka(v: Any) -> float | None:
    """Parse angka format Indonesia/internasional, tanda kurung, atau simbol mata uang."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()
    s = re.sub(r"^(?:rp\.?|idr|usd|\$)\s*", "", s, flags=re.IGNORECASE)
    s = s.replace(" ", "")
    if s in ("", "-", "--", "n/a", "na", "nil"):
        return None
    if s.startswith("-"):
        neg = not neg
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif s.count(",") > 1:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


def parse_periode(v: Any) -> tuple[str, bool, tuple[int, int, int]] | None:
    """Kenali label periode -> (label_normalisasi, apakah_bulanan, kunci_urut)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (_dt.datetime, _dt.date)):
        return (f"{v.year:04d}-{v.month:02d}", True, (v.year, v.month, v.day))

    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int):
        if 1900 <= v <= 2100:
            return (str(v), False, (v, 12, 31))
        return None

    s = str(v).strip()
    if not s:
        return None

    # YYYY-MM atau YYYY/MM
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return (f"{y:04d}-{mo:02d}", True, (y, mo, 1))

    # YYYY-MM-DD atau DD/MM/YYYY
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12:
            return (f"{y:04d}-{mo:02d}", True, (y, mo, d))
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12:
            return (f"{y:04d}-{mo:02d}", True, (y, mo, d))

    # MM/YYYY atau MM-YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{4})$", s)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return (f"{y:04d}-{mo:02d}", True, (y, mo, 1))

    # [DD] NamaBulan YYYY / YYYY NamaBulan / NamaBulan-YY
    m = re.match(r"^(?:(\d{1,2})\s+)?([a-zA-Z]+)[\s\-/]+(\d{2,4})$", s)
    if m and m.group(2).lower() in BULAN_MAP:
        mo = BULAN_MAP[m.group(2).lower()]
        yr = int(m.group(3))
        if yr < 100:
            yr += 2000
        day = int(m.group(1)) if m.group(1) else 1
        return (f"{yr:04d}-{mo:02d}", True, (yr, mo, day))

    m = re.match(r"^(\d{4})[\s\-/]+([a-zA-Z]+)$", s)
    if m and m.group(2).lower() in BULAN_MAP:
        yr, mo = int(m.group(1)), BULAN_MAP[m.group(2).lower()]
        return (f"{yr:04d}-{mo:02d}", True, (yr, mo, 1))

    # Tahun: 2024, FY2024, FY 2024, TA 2024
    m = re.match(r"^(?:fy|ta|tahun)?\s*(\d{4})$", s, flags=re.IGNORECASE)
    if m:
        yr = int(m.group(1))
        if 1900 <= yr <= 2100:
            return (str(yr), False, (yr, 12, 31))

    # Kuartal: Q1 2025, 2025 Q1
    m = re.match(r"^q([1-4])[\s\-/]+(\d{4})$", s, flags=re.IGNORECASE)
    if m:
        q, yr = int(m.group(1)), int(m.group(2))
        return (f"Q{q} {yr}", False, (yr, q * 3, 1))
    m = re.match(r"^(\d{4})[\s\-/]+q([1-4])$", s, flags=re.IGNORECASE)
    if m:
        yr, q = int(m.group(1)), int(m.group(2))
        return (f"Q{q} {yr}", False, (yr, q * 3, 1))

    # Periode samaran: T, T-1, T-2
    m = re.match(r"^t(?:\s*-\s*(\d+))?$", s, flags=re.IGNORECASE)
    if m:
        offset = int(m.group(1) or 0)
        return (s.upper().replace(" ", ""), False, (9999 - offset, 12, 31))

    return None


def deteksi_bagian_teks(teks: Any) -> str | None:
    """Tebak bagian laporan dari judul sheet atau judul blok."""
    s = bersihkan_label(teks)
    if not s:
        return None
    if any(k in s for k in ("neraca", "posisi keuangan", "balance sheet")):
        return "neraca"
    if any(k in s for k in ("laba rugi", "labarugi", "profit loss", "profit and loss", "income statement", "p dan l", "pnl")):
        return "laba_rugi"
    if any(k in s for k in ("arus kas", "aruskas", "cash flow", "cashflow")):
        return "arus_kas"
    if any(k in s for k in ("target", "rkap", "anggaran", "budget")):
        return "target"
    return None


# ============================================================ baca berkas ===
def _baca_csv_rows(path: Path) -> list[list[Any]]:
    raw = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            raw = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        raise ValueError(f"Encoding berkas CSV tidak didukung: {path}")

    sample = "\n".join(raw.splitlines()[:20])
    delimiter = ","
    if path.suffix.lower() == ".tsv":
        delimiter = "\t"
    else:
        counts = {d: sample.count(d) for d in (";", ",", "\t", "|")}
        best = max(counts, key=counts.get)  # type: ignore[arg-type]
        if counts[best] > 0:
            delimiter = best
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            delimiter = dialect.delimiter
        except csv.Error:
            pass

    return [list(r) for r in csv.reader(raw.splitlines(), delimiter=delimiter)]


def _baca_excel_sheets(path: Path) -> list[tuple[str, list[list[Any]]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise RuntimeError("openpyxl belum terpasang. Jalankan: pip install openpyxl") from e
    wb = load_workbook(path, data_only=True, read_only=True)
    return [(nama, [list(r) for r in wb[nama].iter_rows(values_only=True)]) for nama in wb.sheetnames]


def baca_sumber(paths: list[Path], peran_berkas: dict[Path, str] | None = None) -> tuple[list[tuple[str, str | None, list[list[Any]]]], dict[str, str]]:
    """Muat semua input CSV/Excel menjadi daftar (sumber, bagian_hint, rows) + info_meta."""
    tabel: list[tuple[str, str | None, list[list[Any]]]] = []
    info_meta: dict[str, str] = {}
    peran_berkas = peran_berkas or {}

    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Berkas tidak ditemukan: {p}")
        ext = p.suffix.lower()
        hint_file = peran_berkas.get(p) or deteksi_bagian_teks(p.stem)
        if ext in (".xlsx", ".xlsm"):
            for sheet, rows in _baca_excel_sheets(p):
                if sheet.strip().lower() == "info":
                    for r in rows[1:]:
                        if r and len(r) >= 2 and r[0] and r[1] not in (None, ""):
                            k = str(r[0]).strip().lower()
                            if k in ("perusahaan", "mata_uang", "satuan", "industri", "bulan_aktif", "sumber"):
                                info_meta[k] = str(r[1]).strip()
                    continue
                if sheet.strip().lower() in ("ambang_kpi", "piutang_pelanggan", "penjualan_produk", "pemasok",
                                             "persediaan_rincian", "operasional", "produksi_lini"):
                    continue
                tabel.append((f"{p.name}:{sheet}", deteksi_bagian_teks(sheet) or hint_file, rows))
        elif ext in (".csv", ".tsv", ".txt"):
            tabel.append((p.name, hint_file, _baca_csv_rows(p)))
        else:
            raise ValueError(f"Ekstensi berkas belum didukung ({ext}). Gunakan .xlsx, .xlsm, .csv, atau .tsv.")
    return tabel, info_meta


def _deteksi_header_wide(rows: list[list[Any]]) -> tuple[int, int | None, int, list[tuple[int, tuple[str, bool, tuple[int, int, int]]]]] | None:
    """Cari baris header tabel melebar (akun | [kode] | periode...)."""
    best = None
    for idx, r in enumerate(rows[:30]):
        if not r:
            continue
        p_cols: list[tuple[int, tuple[str, bool, tuple[int, int, int]]]] = []
        kode_col: int | None = None
        akun_col: int | None = None
        bagian_col: int | None = None
        for c, val in enumerate(r):
            if val is None or str(val).strip() == "":
                continue
            p = parse_periode(val)
            if p:
                p_cols.append((c, p))
                continue
            low = bersihkan_label(val)
            if low in ("kode", "code", "kode akun"):
                kode_col = c
            elif low in ("bagian", "laporan", "statement", "section", "kategori"):
                bagian_col = c
            elif akun_col is None and low in ("uraian", "akun", "nama akun", "pos", "keterangan", "account", "description", "line item", "item"):
                akun_col = c
        if p_cols:
            if akun_col is None:
                # Pilih kolom teks pertama sebelum kolom periode pertama yang bukan kode/bagian.
                p0 = p_cols[0][0]
                for c in range(p0):
                    if c not in (kode_col, bagian_col):
                        akun_col = c
                        break
                if akun_col is None and kode_col is not None:
                    akun_col = kode_col
            if akun_col is not None:
                score = (len(p_cols), 1 if kode_col is not None else 0, -idx)
                if best is None or score > best[0]:
                    best = (score, idx, kode_col, akun_col, bagian_col, p_cols)
    if best is None:
        return None
    _, idx, kode_col, akun_col, bagian_col, p_cols = best
    return idx, kode_col, akun_col, bagian_col, p_cols  # type: ignore[return-value]


def _deteksi_header_tidy(rows: list[list[Any]]) -> tuple[int, dict[str, int]] | None:
    """Cari header format panjang/tidy: kolom (bagian), akun/kode, periode, nilai."""
    for idx, r in enumerate(rows[:20]):
        if not r:
            continue
        cols: dict[str, int] = {}
        for c, val in enumerate(r):
            low = bersihkan_label(val)
            if low in ("bagian", "laporan", "statement", "section"):
                cols.setdefault("bagian", c)
            elif low in ("kode", "code"):
                cols.setdefault("kode", c)
            elif low in ("akun", "uraian", "nama akun", "pos", "account", "description", "keterangan"):
                cols.setdefault("akun", c)
            elif low in ("periode", "bulan", "tahun", "period", "tanggal", "date"):
                cols.setdefault("periode", c)
            elif low in ("nilai", "jumlah", "nominal", "saldo", "angka", "amount", "value"):
                cols.setdefault("nilai", c)
        if "periode" in cols and "nilai" in cols and ("akun" in cols or "kode" in cols):
            return idx, cols
    return None


def ekstrak_baris_mentah(tabel: list[tuple[str, str | None, list[list[Any]]]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Ubah tabel-tabel input menjadi daftar baris mentah standar + petunjuk info."""
    baris_mentah: list[dict[str, Any]] = []
    info_hint: dict[str, str] = {}

    for sumber, bagian_hint, rows in tabel:
        if not rows:
            continue
        # Cek judul atas untuk petunjuk perusahaan / satuan
        for r in rows[:5]:
            teks = " ".join(str(x) for x in r if x not in (None, "")).strip()
            low = teks.lower()
            if not info_hint.get("satuan"):
                if "dalam jutaan" in low or "jutaan rupiah" in low:
                    info_hint["satuan"] = "juta"
                elif "dalam ribuan" in low or "ribuan rupiah" in low:
                    info_hint["satuan"] = "ribu"
            if not info_hint.get("perusahaan") and (low.startswith("pt ") or low.startswith("cv ")):
                info_hint["perusahaan"] = teks

        tidy = _deteksi_header_tidy(rows)
        if tidy:
            h_idx, cols = tidy
            kelompok: dict[tuple[str | None, str | None, str], dict[str, Any]] = {}
            for r in rows[h_idx + 1:]:
                if not r or all(x in (None, "") for x in r):
                    continue
                p_raw = r[cols["periode"]] if cols["periode"] < len(r) else None
                p_parsed = parse_periode(p_raw)
                if not p_parsed:
                    continue
                val = parse_angka(r[cols["nilai"]] if cols["nilai"] < len(r) else None)
                bag = deteksi_bagian_teks(r[cols["bagian"]]) if "bagian" in cols and cols["bagian"] < len(r) else bagian_hint
                kode_eks = str(r[cols["kode"]]).strip() if "kode" in cols and cols["kode"] < len(r) and r[cols["kode"]] not in (None, "") else None
                akun = str(r[cols["akun"]]).strip() if "akun" in cols and cols["akun"] < len(r) and r[cols["akun"]] not in (None, "") else (kode_eks or "")
                if not akun and not kode_eks:
                    continue
                key = (bag, kode_eks, akun)
                item = kelompok.setdefault(key, {
                    "sumber": sumber, "bagian": bag, "kode_eksplisit": kode_eks,
                    "akun": akun, "nilai": {},
                })
                if val is not None:
                    item["nilai"][p_parsed[0]] = (item["nilai"].get(p_parsed[0]) or 0.0) + val
                    item.setdefault("periode_meta", {})[p_parsed[0]] = p_parsed
            baris_mentah.extend(kelompok.values())
            continue

        wide = _deteksi_header_wide(rows)
        if not wide:
            continue
        h_idx, kode_col, akun_col, bagian_col, p_cols = wide  # type: ignore[misc]
        bagian_aktif = bagian_hint
        for r in rows[h_idx + 1:]:
            if not r or all(x in (None, "") for x in r):
                continue
            kode_eks = str(r[kode_col]).strip() if kode_col is not None and kode_col < len(r) and r[kode_col] not in (None, "") else None
            akun = str(r[akun_col]).strip() if akun_col < len(r) and r[akun_col] not in (None, "") else (kode_eks or "")
            if not akun and not kode_eks:
                continue

            # Hindari membaca ulang baris header periode di tengah sheet bertumpuk
            label_cek = bersihkan_label(akun)
            bag_header = deteksi_bagian_teks(akun)
            if bag_header or label_cek in ("uraian", "akun", "nama akun", "kode", "pos", "keterangan", "account"):
                sel_periode = [r[c_idx] if c_idx < len(r) else None for c_idx, _ in p_cols]
                if any(x not in (None, "") for x in sel_periode) and all(
                    x in (None, "") or parse_periode(x) is not None for x in sel_periode
                ):
                    if bag_header:
                        bagian_aktif = bag_header
                    continue

            nilai_row: dict[str, float] = {}
            p_meta: dict[str, tuple[str, bool, tuple[int, int, int]]] = {}
            for c_idx, p_parsed in p_cols:
                val = parse_angka(r[c_idx]) if c_idx < len(r) else None
                if val is not None:
                    nilai_row[p_parsed[0]] = val
                    p_meta[p_parsed[0]] = p_parsed

            # Deteksi baris pemisah blok laporan (tanpa angka)
            if not nilai_row:
                bag_baru = deteksi_bagian_teks(akun)
                if bag_baru:
                    bagian_aktif = bag_baru
                continue

            bag_baris = (
                deteksi_bagian_teks(r[bagian_col])
                if bagian_col is not None and bagian_col < len(r) and r[bagian_col] not in (None, "")
                else None
            ) or bagian_aktif

            baris_mentah.append({
                "sumber": sumber,
                "bagian": bag_baris,
                "kode_eksplisit": kode_eks,
                "akun": akun,
                "nilai": nilai_row,
                "periode_meta": p_meta,
            })

    return baris_mentah, info_hint


# ========================================================= pemetaan & ubah ===
def pilih_jenis(baris_mentah: list[dict[str, Any]], jenis_req: str) -> str:
    if jenis_req in ("tahunan", "bulanan"):
        return jenis_req
    semua_pm = [pm for b in baris_mentah for pm in b.get("periode_meta", {}).values()]
    unik_tgl = {pm[0]: pm for pm in semua_pm if pm[1]}
    unik_thn = {pm[0]: pm for pm in semua_pm if not pm[1]}

    # Tanggal tutup buku tahunan (mis. 31 Des 2024 & 31 Des 2025 di Neraca) adalah tahunan, bukan bulanan.
    if unik_tgl:
        tahun_dari_tgl = [pm[2][0] for pm in unik_tgl.values()]
        bulan_dari_tgl = {pm[2][1] for pm in unik_tgl.values()}
        satu_titik_per_tahun = len(tahun_dari_tgl) == len(set(tahun_dari_tgl))
        if satu_titik_per_tahun and (unik_thn or bulan_dari_tgl == {12} or len(unik_tgl) <= 4):
            return "tahunan"
        if len(unik_tgl) >= 3:
            return "bulanan"
    return "tahunan"


def normalisasi_periode_jenis(baris_mentah: list[dict[str, Any]], jenis: str) -> list[str]:
    """Pastikan label periode konsisten dengan mode tahunan/bulanan dan urut kronologis."""
    urutan: dict[str, tuple[int, int, int]] = {}
    if jenis == "tahunan":
        # Jika format tahunan memakai tanggal tutup buku (mis. 31 Des 2025 -> 2025-12) di bulan Desember
        # atau 1 titik tanggal per tahun, ringkas menjadi label tahun YYYY agar cocok dengan LabaRugi/ArusKas.
        semua_pm = [pm for b in baris_mentah for pm in b.get("periode_meta", {}).values()]
        unik_tgl = {pm[0]: pm for pm in semua_pm if pm[1]}
        tahun_tgl = [pm[2][0] for pm in unik_tgl.values()]
        if unik_tgl and len(tahun_tgl) == len(set(tahun_tgl)):
            for b in baris_mentah:
                baru: dict[str, float] = {}
                meta_baru: dict[str, tuple[str, bool, tuple[int, int, int]]] = {}
                for k, val in b["nilai"].items():
                    pm = b.get("periode_meta", {}).get(k)
                    if pm and pm[1]:
                        yr = str(pm[2][0])
                        baru[yr] = (baru.get(yr) or 0.0) + val
                        meta_baru[yr] = (yr, False, (pm[2][0], 12, 31))
                    else:
                        baru[k] = (baru.get(k) or 0.0) + val
                        if pm:
                            meta_baru[k] = pm
                b["nilai"] = baru
                b["periode_meta"] = meta_baru

    for b in baris_mentah:
        for p_key in b["nilai"]:
            pm = b.get("periode_meta", {}).get(p_key)
            if pm:
                urutan[p_key] = pm[2]

    return sorted(urutan.keys(), key=lambda k: urutan[k])


def muat_pemetaan_kustom(path: Path | None) -> dict[tuple[str | None, str], tuple[str | None, str | None, int]]:
    """Muat aturan pemetaan khusus dari JSON atau CSV -> {(bagian|None, label_norm): (bagian, kode, tanda)}."""
    hasil: dict[tuple[str | None, str], tuple[str | None, str | None, int]] = {}
    if path is None:
        return hasil
    if not path.exists():
        raise FileNotFoundError(f"Berkas pemetaan tidak ditemukan: {path}")

    def tambah(bag: str | None, akun: str, target: Any) -> None:
        k_norm = bersihkan_label(akun)
        if not k_norm:
            return
        if target in (None, "", "_abaikan"):
            hasil[(bag, k_norm)] = (bag, None, 1)
        elif isinstance(target, str):
            bag_t, kode_t = (target.split(".", 1) if "." in target else (bag, target))
            hasil[(bag, k_norm)] = (bag_t, kode_t.strip(), 1)
        elif isinstance(target, dict):
            kode_t = target.get("kode")
            bag_t = target.get("bagian") or bag
            tanda = int(target.get("tanda", 1))
            hasil[(bag, k_norm)] = (bag_t, kode_t, tanda)

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for k, v in data.items():
            if k in ("neraca", "laba_rugi", "arus_kas", "target") and isinstance(v, dict):
                for akun, tgt in v.items():
                    tambah(k, akun, tgt)
            elif k in ("belum_terpetakan", "terpetakan") and isinstance(v, dict):
                for akun, tgt in v.items():
                    tambah(None, akun, tgt)
            else:
                tambah(None, k, v)
    else:
        for r in _baca_csv_rows(path):
            if not r or len(r) < 2 or bersihkan_label(r[0]) in ("akun", "uraian", "nama akun"):
                continue
            bag = deteksi_bagian_teks(r[2]) if len(r) > 2 and r[2] else None
            tambah(bag, r[0], r[1])
    return hasil


def _cocok_sinonim(label_norm: str, bagian_hint: str | None, daftar: list[tuple[str, str, tuple[str, ...]]]) -> tuple[str, str] | None:
    """Cocokkan frasa sinonim paling spesifik; hormati bagian_hint bila tersedia."""
    kandidat: list[tuple[int, int, str, str]] = []
    for bag, kode, frasa_list in daftar:
        if bagian_hint and bag != bagian_hint:
            continue
        for frasa in frasa_list:
            if label_norm == frasa:
                kandidat.append((3, len(frasa), bag, kode))
            elif frasa in label_norm.split() or f" {frasa} " in f" {label_norm} ":
                kandidat.append((2, len(frasa), bag, kode))
            elif frasa in label_norm and len(frasa) >= 5:
                kandidat.append((1, len(frasa), bag, kode))
    if not kandidat and bagian_hint:
        return _cocok_sinonim(label_norm, None, daftar)
    if not kandidat:
        return None
    kandidat.sort(reverse=True)
    _, _, bag, kode = kandidat[0]
    return bag, kode


def petakan_data(
    baris_mentah: list[dict[str, Any]],
    jenis: str,
    pemetaan_kustom: dict[tuple[str | None, str], tuple[str | None, str | None, int]],
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, Any]]:
    """Petakan baris mentah ke struktur target + audit pemetaan."""
    kode_valid = KODE_VALID[jenis]
    sinonim = SINONIM_TAHUNAN if jenis == "tahunan" else SINONIM_BULANAN
    pos_pos = POS_POSITIF[jenis]

    hasil: dict[str, dict[str, dict[str, float]]] = {bag: {} for bag in kode_valid}
    terpetakan: list[dict[str, Any]] = []
    tidak_terpetakan: list[dict[str, Any]] = []
    catatan_tanda: list[str] = []

    for b in baris_mentah:
        akun = b["akun"]
        bag_hint = b["bagian"]
        kode_eks = b["kode_eksplisit"]
        label_norm = bersihkan_label(akun)
        if not label_norm and not kode_eks:
            continue

        bag_t: str | None = None
        kode_t: str | None = None
        tanda = 1
        cara = ""

        # 1. Pemetaan kustom pengguna
        if (bag_hint, label_norm) in pemetaan_kustom:
            bag_t, kode_t, tanda = pemetaan_kustom[(bag_hint, label_norm)]
            cara = "kustom"
        elif (None, label_norm) in pemetaan_kustom:
            bag_t, kode_t, tanda = pemetaan_kustom[(None, label_norm)]
            cara = "kustom"
        # 2. Kode eksplisit atau nama akun persis sama dengan kode standar
        elif kode_eks:
            for bag, daftar_k in kode_valid.items():
                if kode_eks in daftar_k and (bag_hint in (None, bag)):
                    bag_t, kode_t, cara = bag, kode_eks, "kode_eksplisit"
                    break
        if kode_t is None and akun.strip() in {k for s in kode_valid.values() for k in s}:
            for bag, daftar_k in kode_valid.items():
                if akun.strip() in daftar_k and (bag_hint in (None, bag)):
                    bag_t, kode_t, cara = bag, akun.strip(), "kode_akun"
                    break
        # 3. Sinonim otomatis
        if kode_t is None and cara != "kustom":
            cocok = _cocok_sinonim(label_norm, bag_hint, sinonim)
            if cocok:
                bag_t, kode_t = cocok
                cara = "sinonim"
            elif jenis == "bulanan" and (bag_hint, label_norm) in FALLBACK_BULANAN:
                bag_t, kode_t = FALLBACK_BULANAN[(bag_hint, label_norm)]
                cara = "sinonim_ringkas"
            elif jenis == "bulanan":
                for (fb_bag, fb_lbl), tgt in FALLBACK_BULANAN.items():
                    if label_norm == fb_lbl and bag_hint in (None, fb_bag):
                        bag_t, kode_t = tgt
                        cara = "sinonim_ringkas"
                        break

        if cara == "kustom" and kode_t is None:
            continue
        if kode_t is None:
            if label_norm not in HEADER_BAGIAN:
                contoh = next(iter(b["nilai"].items()), None)
                tidak_terpetakan.append({
                    "bagian": bag_hint or "-",
                    "akun": akun,
                    "sumber": b["sumber"],
                    "contoh": f"{contoh[0]}={contoh[1]}" if contoh else "-",
                })
            continue
        if bag_t is None:
            for bag, daftar_k in kode_valid.items():
                if kode_t in daftar_k:
                    bag_t = bag
                    break
        if bag_t not in hasil or kode_t not in kode_valid[bag_t]:
            tidak_terpetakan.append({"bagian": bag_hint or "-", "akun": akun, "sumber": b["sumber"], "contoh": "-"})
            continue

        baris_target = hasil[bag_t].setdefault(kode_t, {})
        dibalik = False
        for p, v in b["nilai"].items():
            val = v * tanda
            if kode_t in pos_pos and val < 0:
                val = -val
                dibalik = True
            baris_target[p] = (baris_target.get(p) or 0.0) + val
        if dibalik:
            catatan_tanda.append(f"{bag_t}.{kode_t} ('{akun}') bernilai negatif; diubah ke positif sesuai skema.")
        terpetakan.append({"bagian": bag_t, "akun": akun, "kode": kode_t, "cara": cara})

    audit = {
        "terpetakan": terpetakan,
        "tidak_terpetakan": tidak_terpetakan,
        "catatan_tanda": catatan_tanda,
    }
    return hasil, audit


def validasi_hasil(data: dict[str, Any], jenis: str) -> tuple[list[str], list[str]]:
    """Validasi kelengkapan pos wajib dan keseimbangan neraca (tanpa melonggarkan aturan)."""
    error: list[str] = []
    peringatan: list[str] = []

    if jenis == "tahunan":
        periode = data["periode"]
        if not periode:
            return ["Tidak ada kolom periode yang terbaca."], peringatan
        for bag, daftar in WAJIB_TAHUNAN.items():
            for k in daftar:
                kurang = [p for p in periode if data[bag].get(k, {}).get(p) is None]
                if kurang:
                    error.append(f"Pos wajib {bag}.{k} kosong pada periode: {', '.join(kurang)}.")
        for p in periode:
            ta = data["neraca"].get("total_aset", {}).get(p)
            tl = data["neraca"].get("total_liabilitas", {}).get(p)
            te = data["neraca"].get("total_ekuitas", {}).get(p)
            if None not in (ta, tl, te):
                tol = max(2.0, abs(ta) * 0.001)
                if abs(ta - (tl + te)) > tol:
                    error.append(
                        f"[{p}] Neraca tidak seimbang: total aset {ta:,.2f} vs "
                        f"liabilitas + ekuitas {tl + te:,.2f} (selisih {ta - tl - te:,.2f})."
                    )
        return error, peringatan

    # Bulanan
    lr, n = data["laba_rugi"], data["neraca"]
    bl = data["bulan"]
    if not bl:
        return ["Sheet LabaRugi tidak berisi periode bulanan."], peringatan
    for bag, daftar in WAJIB_BULANAN.items():
        for k in daftar:
            if not data[bag].get(k):
                error.append(f"Pos wajib {bag}.{k} belum terisi.")
    if len(bl) < 13:
        peringatan.append(f"Baru tersedia {len(bl)} bulan LabaRugi (laporan-analisa menyarankan >= 13 bulan untuk YoY).")

    for b in sorted(n.get("kas", {})):
        def gv(k: str) -> float:
            return n.get(k, {}).get(b, 0.0) or 0.0

        piutang = gv("piutang_usaha_bruto") - gv("cadangan_kerugian_piutang")
        persediaan = gv("persediaan_bahan_baku") + gv("persediaan_barang_dalam_proses") + gv("persediaan_barang_jadi")
        aset_lancar = gv("kas") + piutang + persediaan + gv("uang_muka_dan_dibayar_dimuka")
        aset_tetap = gv("aset_tetap_perolehan") - gv("akumulasi_penyusutan")
        total_aset = aset_lancar + aset_tetap + gv("aset_tidak_lancar_lain")
        ljp = gv("utang_usaha") + gv("utang_bank_pendek") + gv("bagian_lancar_utang_panjang") + gv("beban_akrual") + gv("utang_pajak")
        ljpg = gv("utang_bank_panjang") + gv("liabilitas_imbalan_kerja")
        ekuitas = gv("modal_disetor") + gv("saldo_laba")
        sel = total_aset - (ljp + ljpg) - ekuitas
        if abs(sel) > max(2.0, abs(total_aset) * 0.001):
            error.append(
                f"[{b}] Neraca tidak seimbang (G1): total aset {total_aset:,.2f} vs "
                f"liabilitas + ekuitas {ljp + ljpg + ekuitas:,.2f} (selisih {sel:,.2f})."
            )
    return error, peringatan


def bangun_keluaran(
    mapped: dict[str, dict[str, dict[str, float]]],
    periode: list[str],
    jenis: str,
    info_meta: dict[str, str],
) -> dict[str, Any]:
    if jenis == "tahunan":
        return {
            "perusahaan": info_meta.get("perusahaan", ""),
            "mata_uang": info_meta.get("mata_uang", "IDR"),
            "satuan": info_meta.get("satuan", "juta"),
            "periode": periode,
            "sumber": info_meta.get("sumber", "Konversi otomatis dari CSV/Excel format bebas"),
            "neraca": mapped["neraca"],
            "laba_rugi": mapped["laba_rugi"],
            "arus_kas": mapped["arus_kas"],
        }

    bulan_lr = sorted({b for v in mapped["laba_rugi"].values() for b in v}) or periode
    bulan_neraca = sorted({b for v in mapped["neraca"].values() for b in v}) or periode
    info = {
        "perusahaan": info_meta.get("perusahaan", ""),
        "industri": info_meta.get("industri", ""),
        "mata_uang": info_meta.get("mata_uang", "IDR"),
        "satuan": info_meta.get("satuan", "juta"),
        "bulan_aktif": info_meta.get("bulan_aktif") or (bulan_lr[-1] if bulan_lr else ""),
        "sumber": info_meta.get("sumber", "Konversi otomatis dari CSV/Excel format bebas"),
    }
    out: dict[str, Any] = {
        "info": info,
        "bulan": bulan_lr,
        "bulan_neraca": bulan_neraca,
        "laba_rugi": mapped["laba_rugi"],
        "neraca": mapped["neraca"],
        "arus_kas": mapped["arus_kas"],
    }
    if mapped.get("target") and any(mapped["target"].values()):
        out["target"] = mapped["target"]
    return out


def tulis_draf_pemetaan(path: Path, audit: dict[str, Any]) -> None:
    draf = {
        "_petunjuk": "Isi nilai null dengan '<bagian>.<kode>' atau '_abaikan', lalu jalankan ulang dengan --pemetaan.",
        "belum_terpetakan": {item["akun"]: None for item in audit["tidak_terpetakan"]},
        "terpetakan": {item["akun"]: f"{item['bagian']}.{item['kode']}" for item in audit["terpetakan"]},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(draf, indent=2, ensure_ascii=False), encoding="utf-8")


# ==================================================================== CLI ===
def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Konverter CSV / Excel format bebas ke format standar repo")
    ap.add_argument("inputs", nargs="*", type=Path, help="File input (.xlsx, .xlsm, .csv, .tsv)")
    ap.add_argument("--neraca", type=Path, help="File khusus Neraca (opsional)")
    ap.add_argument("--laba-rugi", type=Path, help="File khusus Laba Rugi (opsional)")
    ap.add_argument("--arus-kas", type=Path, help="File khusus Arus Kas (opsional)")
    ap.add_argument("--target", type=Path, help="File khusus Target (opsional, mode bulanan)")
    ap.add_argument("--jenis", choices=["auto", "tahunan", "bulanan"], default="auto",
                    help="Format keluaran target (default: auto)")
    ap.add_argument("--pemetaan", type=Path, help="File JSON/CSV pemetaan akun kustom")
    ap.add_argument("--tulis-pemetaan", type=Path, help="Tulis draf pemetaan akun (termasuk yang belum terpetakan)")
    ap.add_argument("--out", type=Path, help="File keluaran utama (.json atau .xlsx)")
    ap.add_argument("--out-json", type=Path, help="Tambahan/eksplisit file keluaran JSON")
    ap.add_argument("--out-xlsx", type=Path, help="Tambahan/eksplisit file keluaran Excel template")
    ap.add_argument("--perusahaan", help="Override nama perusahaan")
    ap.add_argument("--industri", help="Override bidang usaha (mode bulanan)")
    ap.add_argument("--mata-uang", help="Override mata uang (default: IDR)")
    ap.add_argument("--satuan", help="Override satuan angka (default: juta)")
    ap.add_argument("--bulan-aktif", help="Override bulan_aktif YYYY-MM (mode bulanan)")
    ap.add_argument("--trial-balance", action="store_true", help="Perlakukan input sebagai Neraca Saldo (Debit/Kredit)")
    ap.add_argument("--periode", default="2025", help="Label periode bawaan untuk Trial Balance 1 periode")
    ap.add_argument("--hitung-arus-kas", action="store_true",
                    help="Hitung Arus Kas metode tidak langsung otomatis jika ArusKas kosong")
    ap.add_argument("--draf", action="store_true", help="Tetap tulis keluaran meski validasi gagal (untuk perbaikan)")
    ap.add_argument("--diam", action="store_true", help="Ringkas output terminal")
    a = ap.parse_args(argv)

    paths: list[Path] = list(a.inputs)
    peran: dict[Path, str] = {}
    for p, bag in ((a.neraca, "neraca"), (a.laba_rugi, "laba_rugi"), (a.arus_kas, "arus_kas"), (a.target, "target")):
        if p is not None:
            paths.append(p)
            peran[p] = bag
    if not paths:
        ap.error("Berikan minimal satu berkas input (.xlsx/.xlsm/.csv/.tsv).")

    info_hint: dict[str, str] = {}
    tb_warnings: list[str] = []
    try:
        tabel, info_file = baca_sumber(paths, peran)
        pemetaan_kustom = muat_pemetaan_kustom(a.pemetaan)
        apakah_tb = a.trial_balance or any(deteksi_kolom_tb(rows, parse_periode, bersihkan_label) for _, _, rows in tabel)

        if apakah_tb:
            baris_tb, totals_dk = ekstrak_baris_tb(tabel, parse_angka, parse_periode, bersihkan_label, a.periode)
            if not baris_tb:
                print("GAGAL: Tidak ada baris Trial Balance (Debit/Kredit) yang terbaca.", file=sys.stderr)
                return 1
            for p_lbl, (tot_d, tot_k) in sorted(totals_dk.items()):
                tol = max(2.0, max(tot_d, tot_k, 1.0) * 0.001)
                if abs(tot_d - tot_k) > tol:
                    print(
                        f"VALIDASI GAGAL: Trial Balance [{p_lbl}] tidak seimbang: "
                        f"Debit {tot_d:,.2f} vs Kredit {tot_k:,.2f} (selisih {tot_d - tot_k:,.2f}).",
                        file=sys.stderr,
                    )
                    return 2
            if a.jenis in ("tahunan", "bulanan"):
                jenis = a.jenis
            else:
                semua_p = [pm for b in baris_tb for pm in b.get("periode_meta", {}).values()]
                jml_tgl = len({pm[0] for pm in semua_p if pm[1]})
                jenis = "bulanan" if jml_tgl >= 3 else "tahunan"
            mapped, audit, periode = konversi_tb_ke_mapped(
                baris_tb, jenis, pemetaan_kustom, KODE_VALID[jenis],
                SINONIM_TAHUNAN if jenis == "tahunan" else SINONIM_BULANAN,
                bersihkan_label, _cocok_sinonim, FALLBACK_BULANAN,
            )
            # Urutkan periode kronologis berdasar meta
            urutan_tb = {pm[0]: pm[2] for b in baris_tb for pm in b.get("periode_meta", {}).values()}
            periode = sorted(periode, key=lambda p_k: urutan_tb.get(p_k, (9999, 12, 31)))
        else:
            baris_mentah, info_hint = ekstrak_baris_mentah(tabel)
            if not baris_mentah:
                print("GAGAL: Tidak ada tabel laporan keuangan dengan kolom periode yang terbaca.", file=sys.stderr)
                return 1
            jenis = pilih_jenis(baris_mentah, a.jenis)
            periode = normalisasi_periode_jenis(baris_mentah, jenis)
            mapped, audit = petakan_data(baris_mentah, jenis, pemetaan_kustom)
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as e:
        print(f"GAGAL: {e}", file=sys.stderr)
        return 1

    info_meta = {**info_hint, **info_file}
    for k, v in (("perusahaan", a.perusahaan), ("industri", a.industri), ("mata_uang", a.mata_uang),
                 ("satuan", a.satuan), ("bulan_aktif", a.bulan_aktif)):
        if v:
            info_meta[k] = v

    if a.tulis_pemetaan:
        tulis_draf_pemetaan(a.tulis_pemetaan, audit)

    hasil = bangun_keluaran(mapped, periode, jenis, info_meta)
    if a.hitung_arus_kas or (apakah_tb and not hasil["arus_kas"].get("arus_kas_operasi")):
        tb_warnings.extend(hitung_arus_kas_tidak_langsung(hasil, jenis))
    error, peringatan = validasi_hasil(hasil, jenis)
    peringatan = tb_warnings + peringatan

    if not a.diam:
        print(f"Jenis terdeteksi : {jenis}")
        print(f"Periode ({len(periode)})     : {', '.join(periode[:6])}{' ... ' + periode[-1] if len(periode) > 6 else ''}")
        print(f"Baris terpetakan : {len(audit['terpetakan'])} | Belum terpetakan: {len(audit['tidak_terpetakan'])}")
        if audit["tidak_terpetakan"]:
            print("Akun belum terpetakan:")
            for item in audit["tidak_terpetakan"][:15]:
                print(f"  - [{item['bagian']}] {item['akun']} ({item['contoh']})")
        for w in audit["catatan_tanda"] + peringatan:
            print(f"PERINGATAN: {w}", file=sys.stderr)

    if error and not a.draf:
        print("VALIDASI GAGAL:", file=sys.stderr)
        for e in error:
            print(f"  - {e}", file=sys.stderr)
        if a.tulis_pemetaan:
            print(f"Draf pemetaan ditulis ke {a.tulis_pemetaan}. Lengkapi lalu jalankan dengan --pemetaan.", file=sys.stderr)
        return 2

    out_json = a.out_json
    out_xlsx = a.out_xlsx
    if a.out:
        if a.out.suffix.lower() in (".xlsx", ".xlsm"):
            out_xlsx = out_xlsx or a.out
        else:
            out_json = out_json or a.out

    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(hasil, indent=2, ensure_ascii=False), encoding="utf-8")
        if not a.diam:
            print(f"JSON ditulis ke {out_json}")
    if out_xlsx:
        if jenis == "tahunan":
            tulis_lk_excel(out_xlsx, hasil)
        else:
            tulis_paket_excel(out_xlsx, hasil, sertakan_operasional=False)
        if not a.diam:
            print(f"Excel template ditulis ke {out_xlsx}")

    return 2 if error else 0


if __name__ == "__main__":
    sys.exit(main())
