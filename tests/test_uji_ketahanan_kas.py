"""Uji skill uji-ketahanan-kas. Jalankan dari root repo: python -m unittest discover tests -v"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
sys.path[:0] = [str(SK / "laporan-analisa/scripts"), str(SK / "uji-ketahanan-kas/scripts")]

from analisa import Analisa  # noqa: E402
from baca_paket import baca  # noqa: E402
import uji_ketahanan_kas as u  # noqa: E402

SKRIP = SK / "uji-ketahanan-kas/scripts/uji_ketahanan_kas.py"
CASES = ["01-manufaktur-garmen", "02-distribusi-fmcg", "03-makanan-minuman", "04-komponen-logam"]


def paket(case):
    return baca(ROOT / "sample-data" / case / "Data-Keuangan-Bulanan.xlsx")


class UjiKetahananKas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paket = {c: paket(c) for c in CASES}

    def test_sama_dengan_laporan_analisa(self):
        """Horizon 3 bulan: 5 skenario bawaan pertama identik dengan uji_ketahanan() laporan-analisa."""
        for c in CASES:
            with self.subTest(case=c):
                lama = Analisa(self.paket[c]).uji_ketahanan()["rows"]
                h = u.analisa(self.paket[c], horizon=3)
                f = h["_fmt"]
                for r, s in zip(lama, h["skenario"]):
                    self.assertEqual(r["kas_akhir"], f.uang(s["kas_akhir"]), s["nama"])
                    self.assertEqual(r["status"], s["status"], s["nama"])

    def test_guncangan_memperburuk_kas(self):
        h = u.analisa(self.paket["03-makanan-minuman"], [
            {"nama": "dasar"}, {"nama": "jual", "penjualan_pct": -20}, {"nama": "bahan", "harga_bahan_pct": 10},
            {"nama": "dso", "tambah_dso_hari": 10}, {"nama": "dpo", "kurang_dpo_hari": 10},
            {"nama": "tetap", "biaya_tetap_pct": 10}, {"nama": "sekali", "belanja_tambahan": 500}], horizon=6)
        dasar = h["skenario"][0]["kas_akhir"]
        for s in h["skenario"][1:]:
            self.assertLess(s["kas_akhir"], dasar, s["nama"])

    def test_durasi_dan_mulai(self):
        p = self.paket["04-komponen-logam"]
        penuh = u.analisa(p, [{"penjualan_pct": -20}], horizon=6)["skenario"][0]
        pendek = u.analisa(p, [{"penjualan_pct": -20, "durasi_bulan": 2}], horizon=6)["skenario"][0]
        telat = u.analisa(p, [{"belanja_tambahan": 1000, "mulai_bulan": 4}], horizon=6)["skenario"][0]
        dasar = u.analisa(p, [{}], horizon=6)["skenario"][0]
        self.assertGreater(pendek["kas_akhir"], penuh["kas_akhir"])
        self.assertEqual(telat["jalur_kas"][2], dasar["jalur_kas"][2])
        self.assertAlmostEqual(telat["jalur_kas"][3], dasar["jalur_kas"][3] - 1000, places=6)

    def test_uji_balik_tepat_di_batas(self):
        p = self.paket["03-makanan-minuman"]
        h = u.analisa(p, horizon=6)
        v = next(b["nilai"] for b in h["uji_balik"] if b["guncangan"] == "Penjualan turun")
        self.assertIsNotNone(v)
        s = u.analisa(p, [{"penjualan_pct": -v}], horizon=6)["skenario"][0]
        self.assertAlmostEqual(s["kas_terendah"], h["kas_minimum"], delta=abs(h["kas_minimum"]) * 1e-6)

    def test_kovenan_dan_plafon(self):
        h = u.analisa(self.paket["02-distribusi-fmcg"], [{"nama": "x", "penjualan_pct": -25}], horizon=6,
                      plafon=1e9, batas_dscr=99)
        s = h["skenario"][0]
        self.assertFalse(s["kovenan"][0]["lulus"])
        self.assertIsNotNone(s["bulan_kas_habis"])
        self.assertIsNone(s["bulan_habis_dengan_plafon"])

    def test_skenario_tidak_sah(self):
        p = self.paket["01-manufaktur-garmen"]
        for bad in ([{"penjualan": -10}], [{"penjualan_pct": "turun"}], [{"penjualan_pct": -150}],
                    [{"mulai_bulan": 9}]):
            with self.subTest(bad=bad), self.assertRaises(u.SkenarioError):
                u.analisa(p, bad, horizon=6)

    def test_neraca_tidak_seimbang_berhenti(self):
        p = copy.deepcopy(self.paket["01-manufaktur-garmen"])
        b = sorted(p["neraca"]["kas"])[-1]
        p["neraca"]["kas"][b] += 1000
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "paket.json"
            f.write_text(json.dumps(p), encoding="utf-8")
            r = subprocess.run([sys.executable, str(SKRIP), str(f), "--diam"], capture_output=True, text=True,
                               encoding="utf-8")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("G1", r.stderr)

    def test_cli_keluaran(self):
        with tempfile.TemporaryDirectory() as t:
            sk = Path(t) / "skenario.json"
            sk.write_text(json.dumps({"horizon_bulan": 6, "batas_dscr": 1.25,
                                      "skenario": [{"nama": "Uji", "penjualan_pct": -10}]}), encoding="utf-8")
            md, js = Path(t) / "u.md", Path(t) / "u.json"
            r = subprocess.run([sys.executable, str(SKRIP), str(ROOT / "sample-data/01-manufaktur-garmen/Data-Keuangan-Bulanan.xlsx"),
                                "--skenario", str(sk), "--out-md", str(md), "--out-json", str(js), "--diam"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(data["horizon"], 6)
            self.assertEqual(len(data["skenario"][0]["jalur_kas"]), 6)
            self.assertIn("Uji balik", md.read_text(encoding="utf-8"))

    def test_zip_mandiri(self):
        """Zip skill membawa analisa.py & baca_paket.py sehingga jalan tanpa folder laporan-analisa."""
        with tempfile.TemporaryDirectory() as t:
            subprocess.run([sys.executable, str(ROOT / "tools/buat_zip.py"), "--out", t], check=True, capture_output=True)
            zipfile.ZipFile(Path(t) / "uji-ketahanan-kas.zip").extractall(t)
            d = Path(t) / "uji-ketahanan-kas"
            self.assertTrue((d / "scripts/analisa.py").exists())
            r = subprocess.run([sys.executable, str(d / "scripts/uji_ketahanan_kas.py"),
                                str(d / "sample-data/03-makanan-minuman/Data-Keuangan-Bulanan.xlsx"), "--diam"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
