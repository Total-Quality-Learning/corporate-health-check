"""Uji skill efisiensi-sdm-departemen (rasio Rp per karyawan & KPI budgeting per departemen)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
SDM_SCRIPT = SK / "efisiensi-sdm-departemen" / "scripts" / "analisa_sdm_budget.py"
TEMPLATE_CSV = SK / "efisiensi-sdm-departemen" / "templates" / "template-sdm-departemen.csv"
RASIO = SK / "baca-laporan-keuangan" / "scripts" / "hitung_rasio.py"
LAPORAN = SK / "laporan-analisa" / "scripts" / "susun_laporan.py"
SAMPLE_GARMEN = ROOT / "sample-data" / "01-manufaktur-garmen"
SAMPLE_MAMIN = ROOT / "sample-data" / "03-makanan-minuman"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


class SdmBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.rasio_json = cls.tmp / "rasio.json"
        r = run(RASIO, SAMPLE_GARMEN / "lk-tahunan.json", "--out-json", cls.rasio_json, "--diam")
        assert r.returncode == 0, r.stderr

        cls.lap_json = cls.tmp / "laporan.json"
        r2 = run(LAPORAN, SAMPLE_MAMIN / "Data-Keuangan-Bulanan.xlsx", "--out", cls.tmp / "lap.html",
                 "--json", cls.lap_json, "--diam")
        assert r2.returncode == 0, r2.stderr

    def test_csv_departemen_dengan_rasio_tahunan(self):
        out_md = self.tmp / "sdm.md"
        out_json = self.tmp / "sdm.json"
        r = run(SDM_SCRIPT, "--rasio", self.rasio_json, "--input", TEMPLATE_CSV,
                "--out-md", out_md, "--out-json", out_json, "--diam")
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(res["sdm"]["total_kini"], 120.0)
        self.assertEqual(res["sdm"]["total_lalu"], 112.0)

        # Verifikasi perhitungan manual pendapatan per karyawan (dalam juta)
        lk = json.loads((SAMPLE_GARMEN / "lk-tahunan.json").read_text(encoding="utf-8"))
        pend_2025 = lk["laba_rugi"]["pendapatan"]["2025"]
        met = {m["kunci"]: m for m in res["produktivitas"]["metrik"]}
        self.assertAlmostEqual(met["pendapatan"]["kini"], pend_2025 / 120.0, 4)

        md = out_md.read_text(encoding="utf-8")
        self.assertIn("PERLU DATA", md)
        self.assertIn("Produksi & QC", md)
        self.assertIn("Disusun dengan TQ Board Insight | totalquality.co.id", md)

    def test_cli_ringkas_dengan_laporan_bulanan_dan_biaya_sdm(self):
        csv_biaya = self.tmp / "sdm-lengkap.csv"
        csv_biaya.write_text(
            "departemen,kategori_fungsi,karyawan_kini,karyawan_lalu,biaya_sdm_tahunan,anggaran_tahun_depan\n"
            "Produksi,produksi,80,75,6400,6800\n"
            "Penjualan,penjualan,25,25,3000,3200\n"
            "Gudang,gudang_logistik,15,15,1200,1200\n",
            encoding="utf-8",
        )
        out_json = self.tmp / "sdm-bulanan.json"
        r = run(SDM_SCRIPT, "--rasio", self.lap_json, "--input", csv_biaya, "--gaya", "checklist", "--out-json", out_json)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- [", r.stdout)
        res = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertAlmostEqual(res["produktivitas"]["total_biaya_sdm_juta"], 10600.0, 4)
        self.assertIsNotNone(res["produktivitas"]["porsi_sdm_pendapatan_pct"])

        # Juga uji mode CLI cepat tanpa file CSV
        r2 = run(SDM_SCRIPT, "--rasio", self.rasio_json, "--karyawan", "100",
                 "--departemen", "Produksi:60,Penjualan:25,Keuangan & Umum:15", "--gaya", "ringkas")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("Produksi", r2.stdout)


if __name__ == "__main__":
    unittest.main()
