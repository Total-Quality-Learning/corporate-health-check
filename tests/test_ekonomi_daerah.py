"""Uji skill kondisi-ekonomi-daerah (offline, koneksi ke rasio.json/laporan.json, dan uji_ketahanan_kas)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
AMBIL = SK / "kondisi-ekonomi-daerah" / "scripts" / "ambil_makro.py"
ANALISA = SK / "kondisi-ekonomi-daerah" / "scripts" / "analisa_risiko_ekonomi.py"
TEMPLATE_CSV = SK / "kondisi-ekonomi-daerah" / "templates" / "template-ekonomi-daerah.csv"
RASIO = SK / "baca-laporan-keuangan" / "scripts" / "hitung_rasio.py"
LAPORAN = SK / "laporan-analisa" / "scripts" / "susun_laporan.py"
UJI_KAS = SK / "uji-ketahanan-kas" / "scripts" / "uji_ketahanan_kas.py"
SAMPLE_GARMEN = ROOT / "sample-data" / "01-manufaktur-garmen"
SAMPLE_MAMIN = ROOT / "sample-data" / "03-makanan-minuman"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


class EkonomiDaerahTest(unittest.TestCase):
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

    def test_csv_template_offline_dan_skenario_ke_uji_kas(self):
        ek_json = self.tmp / "ekonomi.json"
        r1 = run(AMBIL, "--input", TEMPLATE_CSV, "--offline", "--out", ek_json, "--diam")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        ek = json.loads(ek_json.read_text(encoding="utf-8"))
        self.assertEqual(ek["daerah"], "Jawa Barat")
        self.assertAlmostEqual(ek["indikator_daerah"]["pdrb_pct"]["kini"], 4.8, 3)

        out_md = self.tmp / "risiko.md"
        out_json = self.tmp / "risiko.json"
        out_sken = self.tmp / "skenario-makro.json"
        r2 = run(ANALISA, ek_json, "--rasio", self.rasio_json, "--out-md", out_md,
                 "--out-json", out_json, "--out-skenario", out_sken, "--diam")
        self.assertEqual(r2.returncode, 0, r2.stderr)

        res = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(len(res["dimensi"]), 5)
        self.assertEqual(len(res["paparan"]), 5)
        self.assertIn("PT Contoh Garmen", res["keuangan"]["perusahaan"])
        md = out_md.read_text(encoding="utf-8")
        self.assertIn("Disusun dengan TQ Board Insight | totalquality.co.id", md)

        # Pastikan skenario-makro.json langsung bisa dijalankan di uji_ketahanan_kas.py
        r3 = run(UJI_KAS, SAMPLE_GARMEN / "Data-Keuangan-Bulanan.xlsx", "--skenario", out_sken,
                 "--out-json", self.tmp / "uji.json", "--diam")
        self.assertEqual(r3.returncode, 0, r3.stderr)
        uji = json.loads((self.tmp / "uji.json").read_text(encoding="utf-8"))
        self.assertEqual(len(uji["skenario"]), 4)

    def test_proksi_nasional_dan_perlu_data_dengan_laporan_bulanan(self):
        ek_proksi = {
            "daerah": "Kota Surabaya",
            "indikator_daerah": {},
            "catatan_risiko_daerah": "",
            "nasional": {
                "pertumbuhan_pdb_pct": {"kini": {"tahun": "2025", "nilai": 5.1}, "lalu": {"tahun": "2024", "nilai": 5.0}},
                "inflasi_nasional_pct": {"kini": {"tahun": "2025", "nilai": 5.4}, "lalu": {"tahun": "2024", "nilai": 3.1}},
                "suku_bunga_pinjaman_pct": {"kini": {"tahun": "2025", "nilai": 9.2}, "lalu": {"tahun": "2024", "nilai": 8.4}},
                "kurs_usd": {"kini": {"tahun": "2025", "nilai": 16800.0}, "lalu": {"tahun": "2024", "nilai": 15500.0}},
            },
        }
        p_ek = self.tmp / "ek-proksi.json"
        p_ek.write_text(json.dumps(ek_proksi), encoding="utf-8")

        out_json = self.tmp / "risiko-bulanan.json"
        r = run(ANALISA, p_ek, "--rasio", self.lap_json, "--gaya", "checklist", "--out-json", out_json)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- [ ]", r.stdout)
        self.assertIn("PERLU DATA", r.stdout)
        res = json.loads(out_json.read_text(encoding="utf-8"))
        st_map = {d["kunci"]: d["status"] for d in res["dimensi"]}
        self.assertEqual(st_map["permintaan"], "Aman")
        self.assertEqual(st_map["inflasi"], "Kritis")
        self.assertEqual(st_map["upah"], "Perlu data")
        self.assertEqual(st_map["bunga"], "Perlu perhatian")
        self.assertEqual(st_map["kurs"], "Kritis")


if __name__ == "__main__":
    unittest.main()
