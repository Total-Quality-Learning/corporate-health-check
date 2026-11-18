"""Uji konverter CSV & Excel format bebas (tools/konversi_data.py)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KONVERSI = ROOT / "tools" / "konversi_data.py"
RASIO = ROOT / "skills" / "baca-laporan-keuangan" / "scripts" / "hitung_rasio.py"
LAPORAN = ROOT / "skills" / "laporan-analisa" / "scripts" / "susun_laporan.py"
UJI_KAS = ROOT / "skills" / "uji-ketahanan-kas" / "scripts" / "uji_ketahanan_kas.py"
SAMPLE_LK = ROOT / "sample-data" / "01-manufaktur-garmen" / "lk-tahunan.json"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


class KonversiDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sample = json.loads(SAMPLE_LK.read_text(encoding="utf-8"))

    def test_excel_bebas_tahunan_ke_rasio(self):
        from openpyxl import Workbook

        wb = Workbook()
        ws_n = wb.active
        ws_n.title = "Posisi Keuangan"
        ws_n.append(["PT Contoh Format Bebas"])
        ws_n.append(["Dalam jutaan Rupiah"])
        ws_n.append([])
        # Kolom terbaru di kiri (2025, 2024) + multi-akun ke satu pos standar
        ws_n.append(["Kode Akun & Uraian", "31 Des 2025", "31 Des 2024"])
        n = self.sample["neraca"]
        ws_n.append(["1-1100 Kas dan Bank", n["kas_dan_setara_kas"]["2025"], n["kas_dan_setara_kas"]["2024"]])
        ws_n.append(["1-1200 Piutang Dagang", n["piutang_usaha"]["2025"], n["piutang_usaha"]["2024"]])
        ws_n.append(["1-1300 Persediaan Barang", n["persediaan"]["2025"], n["persediaan"]["2024"]])
        # Bagi aset_lancar_lainnya menjadi 2 baris untuk menguji penjumlahan otomatis
        ws_n.append(["1-1410 Uang Muka", 1000, 1000])
        ws_n.append(["1-1420 Biaya Dibayar di Muka", n["aset_lancar_lainnya"]["2025"] - 1000, n["aset_lancar_lainnya"]["2024"] - 1000])
        ws_n.append(["Total Aktiva Lancar", n["total_aset_lancar"]["2025"], n["total_aset_lancar"]["2024"]])
        ws_n.append(["Aset Tetap (Neto)", n["aset_tetap_neto"]["2025"], n["aset_tetap_neto"]["2024"]])
        ws_n.append(["Aset Tidak Lancar Lain", n["aset_tidak_lancar_lainnya"]["2025"], n["aset_tidak_lancar_lainnya"]["2024"]])
        ws_n.append(["TOTAL ASET", n["total_aset"]["2025"], n["total_aset"]["2024"]])
        ws_n.append(["Utang Bank Jangka Pendek", n["utang_bank_jangka_pendek"]["2025"], n["utang_bank_jangka_pendek"]["2024"]])
        ws_n.append(["Utang Dagang", n["utang_usaha"]["2025"], n["utang_usaha"]["2024"]])
        ws_n.append(["Beban Akrual", n["liabilitas_jangka_pendek_lainnya"]["2025"], n["liabilitas_jangka_pendek_lainnya"]["2024"]])
        ws_n.append(["Total Kewajiban Jangka Pendek", n["total_liabilitas_jangka_pendek"]["2025"], n["total_liabilitas_jangka_pendek"]["2024"]])
        ws_n.append(["Pinjaman Bank Jangka Panjang", n["utang_bank_jangka_panjang"]["2025"], n["utang_bank_jangka_panjang"]["2024"]])
        ws_n.append(["Liabilitas Imbalan Kerja", n["liabilitas_jangka_panjang_lainnya"]["2025"], n["liabilitas_jangka_panjang_lainnya"]["2024"]])
        ws_n.append(["Total Kewajiban", n["total_liabilitas"]["2025"], n["total_liabilitas"]["2024"]])
        ws_n.append(["Saldo Laba", n["saldo_laba"]["2025"], n["saldo_laba"]["2024"]])
        ws_n.append(["Total Ekuitas", n["total_ekuitas"]["2025"], n["total_ekuitas"]["2024"]])

        ws_lr = wb.create_sheet("Profit & Loss")
        lr = self.sample["laba_rugi"]
        ws_lr.append(["Account", "FY2025", "FY2024"])
        ws_lr.append(["Revenue", lr["pendapatan"]["2025"], lr["pendapatan"]["2024"]])
        # Beban negatif dalam kurung -> dinormalisasi menjadi positif
        ws_lr.append(["Cost of Goods Sold", f"({lr['beban_pokok_penjualan']['2025']})", f"({lr['beban_pokok_penjualan']['2024']})"])
        ws_lr.append(["Selling Expenses", -lr["beban_penjualan"]["2025"], -lr["beban_penjualan"]["2024"]])
        ws_lr.append(["General and Administrative Expenses", -lr["beban_umum_administrasi"]["2025"], -lr["beban_umum_administrasi"]["2024"]])
        ws_lr.append(["Interest Expense", lr["beban_bunga"]["2025"], lr["beban_bunga"]["2024"]])
        ws_lr.append(["Income Tax Expense", lr["beban_pajak"]["2025"], lr["beban_pajak"]["2024"]])
        ws_lr.append(["Net Profit", lr["laba_bersih"]["2025"], lr["laba_bersih"]["2024"]])

        ws_ak = wb.create_sheet("Cash Flow")
        ak = self.sample["arus_kas"]
        ws_ak.append(["Description", "2025", "2024"])
        ws_ak.append(["Operating Cash Flow", ak["arus_kas_operasi"]["2025"], ak["arus_kas_operasi"]["2024"]])
        ws_ak.append(["Capex", ak["belanja_modal"]["2025"], ak["belanja_modal"]["2024"]])
        ws_ak.append(["Ending Cash", ak["kas_akhir"]["2025"], ak["kas_akhir"]["2024"]])

        src = self.tmp / "bebas.xlsx"
        wb.save(src)
        out_json = self.tmp / "lk.json"
        out_xlsx = self.tmp / "lk-template.xlsx"
        r = run(KONVERSI, src, "--out", out_json, "--out-xlsx", out_xlsx)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        lk = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(lk["periode"], ["2024", "2025"])
        self.assertEqual(lk["satuan"], "juta")
        self.assertEqual(lk["neraca"]["aset_lancar_lainnya"]["2025"], n["aset_lancar_lainnya"]["2025"])
        self.assertTrue(out_xlsx.exists())

        r2 = run(RASIO, out_json, "--out-json", self.tmp / "rasio.json", "--diam")
        self.assertEqual(r2.returncode, 0, r2.stderr)

    def test_csv_semicolon_bertumpuk_dan_tidy(self):
        n, lr, ak = self.sample["neraca"], self.sample["laba_rugi"], self.sample["arus_kas"]
        baris = [
            "Uraian;2024;2025",
            "NERACA;;",
            f"Kas dan setara kas;{n['kas_dan_setara_kas']['2024']};{n['kas_dan_setara_kas']['2025']}",
            f"Piutang usaha;{n['piutang_usaha']['2024']};{n['piutang_usaha']['2025']}",
            f"Persediaan;{n['persediaan']['2024']};{n['persediaan']['2025']}",
            f"Total aset lancar;{n['total_aset_lancar']['2024']};{n['total_aset_lancar']['2025']}",
            f"Total aset;{n['total_aset']['2024']};{n['total_aset']['2025']}",
            f"Utang usaha;{n['utang_usaha']['2024']};{n['utang_usaha']['2025']}",
            f"Total liabilitas jangka pendek;{n['total_liabilitas_jangka_pendek']['2024']};{n['total_liabilitas_jangka_pendek']['2025']}",
            f"Total liabilitas;{n['total_liabilitas']['2024']};{n['total_liabilitas']['2025']}",
            f"Total ekuitas;{n['total_ekuitas']['2024']};{n['total_ekuitas']['2025']}",
            "LABA RUGI;2024;2025",
            f"Pendapatan;{lr['pendapatan']['2024']};{lr['pendapatan']['2025']}",
            f"Beban pokok penjualan;{lr['beban_pokok_penjualan']['2024']};{lr['beban_pokok_penjualan']['2025']}",
            f"Laba bersih;{lr['laba_bersih']['2024']};{lr['laba_bersih']['2025']}",
            "ARUS KAS;;",
            f"Arus kas operasi;{ak['arus_kas_operasi']['2024']};{ak['arus_kas_operasi']['2025']}",
        ]
        csv_path = self.tmp / "stacked.csv"
        csv_path.write_text("\n".join(baris), encoding="utf-8-sig")
        out_json = self.tmp / "lk-csv.json"
        r = run(KONVERSI, csv_path, "--out", out_json, "--perusahaan", "PT CSV Mandiri")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(run(RASIO, out_json, "--diam").returncode, 0)

        # Uji format tidy/panjang
        tidy_rows = ["bagian,akun,periode,nilai"]
        for bag, src_dict in (("neraca", n), ("laba_rugi", lr), ("arus_kas", ak)):
            for kode, pmap in src_dict.items():
                for p in ("2024", "2025"):
                    if p in pmap:
                        tidy_rows.append(f"{bag},{kode},{p},{pmap[p]}")
        tidy_csv = self.tmp / "tidy.csv"
        tidy_csv.write_text("\n".join(tidy_rows), encoding="utf-8")
        out_tidy = self.tmp / "lk-tidy.json"
        r2 = run(KONVERSI, tidy_csv, "--out", out_tidy)
        self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
        self.assertEqual(run(RASIO, out_tidy, "--diam").returncode, 0)

    def test_pemetaan_kustom_dan_neraca_rusak_berhenti(self):
        n, lr, ak = self.sample["neraca"], self.sample["laba_rugi"], self.sample["arus_kas"]
        # Pakai nama akun non-standar "Simpanan Darurat Perusahaan" untuk kas_dan_setara_kas
        baris = [
            "bagian,akun,2024,2025",
            f"neraca,Simpanan Darurat Perusahaan,{n['kas_dan_setara_kas']['2024']},{n['kas_dan_setara_kas']['2025']}",
            f"neraca,Piutang usaha,{n['piutang_usaha']['2024']},{n['piutang_usaha']['2025']}",
            f"neraca,Persediaan,{n['persediaan']['2024']},{n['persediaan']['2025']}",
            f"neraca,Total aset lancar,{n['total_aset_lancar']['2024']},{n['total_aset_lancar']['2025']}",
            f"neraca,Total aset,{n['total_aset']['2024']},{n['total_aset']['2025']}",
            f"neraca,Utang usaha,{n['utang_usaha']['2024']},{n['utang_usaha']['2025']}",
            f"neraca,Total liabilitas jangka pendek,{n['total_liabilitas_jangka_pendek']['2024']},{n['total_liabilitas_jangka_pendek']['2025']}",
            f"neraca,Total liabilitas,{n['total_liabilitas']['2024']},{n['total_liabilitas']['2025']}",
            f"neraca,Total ekuitas,{n['total_ekuitas']['2024']},{n['total_ekuitas']['2025']}",
            f"laba_rugi,Pendapatan,{lr['pendapatan']['2024']},{lr['pendapatan']['2025']}",
            f"laba_rugi,HPP,{lr['beban_pokok_penjualan']['2024']},{lr['beban_pokok_penjualan']['2025']}",
            f"laba_rugi,Laba bersih,{lr['laba_bersih']['2024']},{lr['laba_bersih']['2025']}",
            f"arus_kas,Arus kas operasi,{ak['arus_kas_operasi']['2024']},{ak['arus_kas_operasi']['2025']}",
        ]
        csv_path = self.tmp / "kustom.csv"
        csv_path.write_text("\n".join(baris), encoding="utf-8")
        draft_map = self.tmp / "pemetaan.json"
        out_lk = self.tmp / "lk-kustom.json"
        r_fail = run(KONVERSI, csv_path, "--tulis-pemetaan", draft_map, "--out", out_lk)
        self.assertEqual(r_fail.returncode, 2)
        self.assertTrue(draft_map.exists())
        draf = json.loads(draft_map.read_text(encoding="utf-8"))
        self.assertIn("Simpanan Darurat Perusahaan", draf["belum_terpetakan"])

        draf["belum_terpetakan"]["Simpanan Darurat Perusahaan"] = "neraca.kas_dan_setara_kas"
        draft_map.write_text(json.dumps(draf), encoding="utf-8")
        r_ok = run(KONVERSI, csv_path, "--pemetaan", draft_map, "--out", out_lk)
        self.assertEqual(r_ok.returncode, 0, r_ok.stderr + r_ok.stdout)

        # Neraca tidak seimbang harus ditolak (exit 2) dan file keluaran tidak ditulis
        baris_rusak = list(baris)
        baris_rusak[5] = f"neraca,Total aset,{n['total_aset']['2024'] + 5000},{n['total_aset']['2025']}"
        csv_rusak = self.tmp / "rusak.csv"
        csv_rusak.write_text("\n".join(baris_rusak), encoding="utf-8")
        out_rusak = self.tmp / "tidak-ada.json"
        r_rusak = run(KONVERSI, csv_rusak, "--pemetaan", draft_map, "--out", out_rusak)
        self.assertEqual(r_rusak.returncode, 2)
        self.assertFalse(out_rusak.exists())

    def test_csv_bulanan_ke_laporan_dan_uji_kas(self):
        # 14 bulan (2025-01..2026-02) + Neraca sejak Des 2024 (format nama bulan Indonesia)
        bulan_labels = [
            "Des 2024", "Jan 2025", "Feb 2025", "Mar 2025", "Apr 2025", "Mei 2025",
            "Jun 2025", "Jul 2025", "Agu 2025", "Sep 2025", "Okt 2025", "Nov 2025",
            "Des 2025", "Jan 2026", "Feb 2026",
        ]
        # Buat data seimbang deterministik untuk tiap bulan
        kas_vals = [1000 + 20 * i for i in range(len(bulan_labels))]
        lr_rows = [
            ("Pendapatan neto", [""] + ["500"] * 14),
            ("HPP - bahan baku", [""] + ["300"] * 14),
            ("Beban penjualan", [""] + ["50"] * 14),
            ("Beban umum & administrasi", [""] + ["80"] * 14),
            ("Beban bunga", [""] + ["10"] * 14),
            ("Beban pajak", [""] + ["10"] * 14),
            ("Laba bersih", [""] + ["50"] * 14),
        ]
        # Neraca: Aset = kas + piutang(400) + persediaan_jadi(300) + aset_tetap(1000) - akum(200) = kas + 1500
        # Pasiva: utang_usaha(300) + utang_bank_panjang(500) + modal_disetor(1500) + saldo_laba(kas - 800) = kas + 1500
        n_rows = [
            ("Kas dan setara kas", [str(k) for k in kas_vals]),
            ("Piutang usaha (bruto)", ["400"] * 15),
            ("Persediaan barang jadi", ["300"] * 15),
            ("Aset tetap - harga perolehan", ["1000"] * 15),
            ("Akumulasi penyusutan", ["200"] * 15),
            ("Utang usaha", ["300"] * 15),
            ("Utang bank jangka panjang", ["500"] * 15),
            ("Modal disetor", ["1500"] * 15),
            ("Saldo laba", [str(k - 800) for k in kas_vals]),
        ]
        ak_rows = [
            ("Arus kas operasi", [""] + ["40"] * 14),
            ("Belanja modal", [""] + ["20"] * 14),
            ("Kas akhir bulan", [""] + [str(k) for k in kas_vals[1:]]),
        ]

        lines = ["bagian,uraian," + ",".join(bulan_labels)]
        for bag, grp in (("Laba Rugi", lr_rows), ("Neraca", n_rows), ("Arus Kas", ak_rows)):
            for nama, vals in grp:
                lines.append(",".join([bag, nama, *vals]))

        csv_bulanan = self.tmp / "bulanan-bebas.csv"
        csv_bulanan.write_text("\n".join(lines), encoding="utf-8")
        paket_xlsx = self.tmp / "paket.xlsx"
        r = run(KONVERSI, csv_bulanan, "--out", paket_xlsx, "--perusahaan", "PT Bulanan CSV")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue(paket_xlsx.exists())

        r_lap = run(LAPORAN, paket_xlsx, "--out", self.tmp / "laporan.html", "--json", self.tmp / "laporan.json", "--diam")
        self.assertEqual(r_lap.returncode, 0, r_lap.stderr)
        self.assertTrue((self.tmp / "laporan.html").exists())

        r_kas = run(UJI_KAS, paket_xlsx, "--horizon", "3", "--out-json", self.tmp / "uji.json", "--diam")
        self.assertEqual(r_kas.returncode, 0, r_kas.stderr)


if __name__ == "__main__":
    unittest.main()
