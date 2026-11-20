"""Uji konverter Trial Balance (Debit/Kredit) dan Arus Kas Tidak Langsung otomatis."""
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


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


class TrialBalanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_trial_balance_multi_periode_ke_rasio(self):
        # Trial balance pra-penutup seimbang untuk 2024 & 2025 (dalam juta)
        # 2024: Kas 500, Piutang 300, Persediaan 200, AsetTetap 1000 | UtangUsaha 250, UtangBankPanjang 450, Modal 1000
        #       Pendapatan 2000, HPP 1300, BebanPenjualan 200, BebanUmum 150, BebanBunga 50 -> LabaBersih=300
        #       Total Debit = 500+300+200+1000+1300+200+150+50 = 3700 | Total Kredit = 250+450+1000+2000 = 3700
        # 2025: Kas 620, Piutang 420, Persediaan 360, AsetTetap 1100 | UtangUsaha 300, UtangBankPanjang 400, Modal 1000, SaldoLaba 300
        #       Pendapatan 2400, HPP 1500, BebanPenjualan 220, BebanUmum 140, BebanBunga 40 -> LabaBersih=500
        #       Total Debit = 620+420+360+1100+1500+220+140+40 = 4400 | Total Kredit = 300+400+1000+300+2400 = 4400
        tb_csv = self.tmp / "tb.csv"
        tb_csv.write_text(
            "kode_akun,nama_akun,debit_2024,kredit_2024,debit_2025,kredit_2025\n"
            "1-1100,Kas dan bank,500,0,620,0\n"
            "1-1200,Piutang usaha,300,0,420,0\n"
            "1-1300,Persediaan,200,0,360,0\n"
            "1-2100,Aset tetap neto,1000,0,1100,0\n"
            "2-1100,Utang usaha,0,250,0,300\n"
            "2-2100,Utang bank jangka panjang,0,450,0,400\n"
            "3-1000,Modal disetor,0,1000,0,1000\n"
            "3-2000,Saldo laba,0,0,0,300\n"
            "4-1000,Pendapatan usaha,0,2000,0,2400\n"
            "5-1000,Beban pokok penjualan,1300,0,1500,0\n"
            "6-1000,Beban penjualan,200,0,220,0\n"
            "6-2000,Beban umum dan administrasi,150,0,140,0\n"
            "7-1000,Beban bunga,50,0,40,0\n",
            encoding="utf-8",
        )
        out_lk = self.tmp / "lk-tb.json"
        r = run(KONVERSI, tb_csv, "--out", out_lk, "--perusahaan", "PT TB Sejahtera")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

        lk = json.loads(out_lk.read_text(encoding="utf-8"))
        self.assertEqual(lk["laba_rugi"]["laba_bersih"]["2025"], 500.0)
        self.assertEqual(lk["neraca"]["total_aset"]["2025"], 2500.0)
        self.assertEqual(lk["neraca"]["total_ekuitas"]["2025"], 1800.0)
        # Cek Arus Kas tidak langsung 2025: OCF = 500 - (420-300) - (360-200) + (300-250) = 500 - 120 - 160 + 50 = 270
        self.assertAlmostEqual(lk["arus_kas"]["arus_kas_operasi"]["2025"], 270.0, 4)

        r2 = run(RASIO, out_lk, "--out-json", self.tmp / "rasio-tb.json", "--diam")
        self.assertEqual(r2.returncode, 0, r2.stderr)

    def test_trial_balance_tidak_seimbang_berhenti(self):
        tb_rusak = self.tmp / "tb-rusak.csv"
        tb_rusak.write_text(
            "kode_akun,nama_akun,debit,kredit\n"
            "1-1100,Kas,500,0\n"
            "3-1000,Modal disetor,0,400\n",
            encoding="utf-8",
        )
        r = run(KONVERSI, tb_rusak, "--out", self.tmp / "x.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("tidak seimbang", r.stderr)

    def test_bulanan_tanpa_arus_kas_dihitung_otomatis(self):
        # 14 bulan L/R (2025-01..2026-02) + Neraca (2024-12..2026-02) tanpa sheet ArusKas
        bulan = [
            "2024-12", "2025-01", "2025-02", "2025-03", "2025-04", "2025-05",
            "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11",
            "2025-12", "2026-01", "2026-02",
        ]
        kas_vals = [1000 + 50 * i for i in range(len(bulan))]
        lines = ["bagian,uraian," + ",".join(bulan)]
        for nama, vals in (
            ("Pendapatan neto", [""] + ["500"] * 14),
            ("HPP - bahan baku", [""] + ["300"] * 14),
            ("Beban penjualan", [""] + ["60"] * 14),
            ("Beban umum & administrasi", [""] + ["90"] * 14),
            ("Laba bersih", [""] + ["50"] * 14),
        ):
            lines.append(",".join(["Laba Rugi", nama, *vals]))
        for nama, vals in (
            ("Kas dan setara kas", [str(k) for k in kas_vals]),
            ("Piutang usaha (bruto)", ["400"] * 15),
            ("Persediaan barang jadi", ["300"] * 15),
            ("Aset tetap - harga perolehan", ["1000"] * 15),
            ("Akumulasi penyusutan", ["200"] * 15),
            ("Utang usaha", ["300"] * 15),
            ("Utang bank jangka panjang", ["500"] * 15),
            ("Modal disetor", ["1500"] * 15),
            ("Saldo laba", [str(k - 800) for k in kas_vals]),
        ):
            lines.append(",".join(["Neraca", nama, *vals]))

        csv_no_cf = self.tmp / "tanpa-ak.csv"
        csv_no_cf.write_text("\n".join(lines), encoding="utf-8")
        paket_xlsx = self.tmp / "paket-no-cf.xlsx"
        r = run(KONVERSI, csv_no_cf, "--jenis", "bulanan", "--hitung-arus-kas", "--out", paket_xlsx)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

        lap_json = self.tmp / "lap.json"
        r2 = run(LAPORAN, paket_xlsx, "--out", self.tmp / "lap.html", "--json", lap_json, "--diam")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        vm = json.loads(lap_json.read_text(encoding="utf-8"))
        gerbang = {g["kode"]: g["status"] for g in vm["gerbang"]}
        self.assertEqual(gerbang["G1"], "Lulus")
        self.assertEqual(gerbang["G3"], "Lulus")
        self.assertEqual(gerbang["G4"], "Lulus")


if __name__ == "__main__":
    unittest.main()
