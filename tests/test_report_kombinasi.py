"""Uji generator report kombinasi lintas-skill (tools/susun_report_kombinasi.py)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
KOMBINASI = ROOT / "tools" / "susun_report_kombinasi.py"
RASIO = SK / "baca-laporan-keuangan" / "scripts" / "hitung_rasio.py"
GEJALA = SK / "red-flag-operasional" / "scripts" / "deteksi_gejala.py"
KESIAPAN = SK / "cek-kesiapan-data" / "scripts" / "skor_kesiapan.py"
RINGKAS_EM = SK / "data-emiten" / "scripts" / "ringkas_emiten.py"
EKO_ANALISA = SK / "kondisi-ekonomi-daerah" / "scripts" / "analisa_risiko_ekonomi.py"
EKO_CSV = SK / "kondisi-ekonomi-daerah" / "templates" / "template-ekonomi-daerah.csv"
LAPORAN = SK / "laporan-analisa" / "scripts" / "susun_laporan.py"
UJI_KAS = SK / "uji-ketahanan-kas" / "scripts" / "uji_ketahanan_kas.py"
FIXTURE_EM = ROOT / "tests" / "fixtures" / "emiten-contoh.json"
SAMPLE_GARMEN = ROOT / "sample-data" / "01-manufaktur-garmen"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


class ReportKombinasiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.rasio = cls.tmp / "rasio.json"
        cls.gejala = cls.tmp / "gejala.json"
        cls.kesiapan = cls.tmp / "kesiapan.json"
        cls.emiten = cls.tmp / "pembanding.json"
        cls.ekonomi = cls.tmp / "risiko-ekonomi.json"
        cls.laporan = cls.tmp / "laporan.json"
        cls.uji_kas = cls.tmp / "uji-kas.json"

        assert run(RASIO, SAMPLE_GARMEN / "lk-tahunan.json", "--out-json", cls.rasio, "--diam").returncode == 0
        assert run(GEJALA, cls.rasio, "--out-json", cls.gejala, "--diam").returncode == 0
        assert run(KESIAPAN, "--jawaban", "B,B,A,B,A,B,A,C", "--out-json", cls.kesiapan, "--diam").returncode == 0
        assert run(RINGKAS_EM, FIXTURE_EM, "--rasio", cls.rasio, "--out-json", cls.emiten, "--diam").returncode == 0
        assert run(EKO_ANALISA, EKO_CSV, "--rasio", cls.rasio, "--out-json", cls.ekonomi, "--diam").returncode == 0
        assert run(LAPORAN, SAMPLE_GARMEN / "Data-Keuangan-Bulanan.xlsx", "--out", cls.tmp / "lap.html", "--json", cls.laporan, "--diam").returncode == 0
        assert run(UJI_KAS, SAMPLE_GARMEN / "Data-Keuangan-Bulanan.xlsx", "--out-json", cls.uji_kas, "--diam").returncode == 0

    def test_report_kombinasi_tahunan_lengkap(self):
        out_html = self.tmp / "komb-tahunan.html"
        out_md = self.tmp / "komb-tahunan.md"
        r = run(
            KOMBINASI,
            "--rasio", self.rasio,
            "--gejala", self.gejala,
            "--kesiapan", self.kesiapan,
            "--emiten", self.emiten,
            "--ekonomi", self.ekonomi,
            "--catatan", "Laba tumbuh, namun arus kas operasi negatif sehingga stok dan piutang harus segera ditertibkan.",
            "--out", out_html,
            "--out-md", out_md,
            "--diam",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        html = out_html.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("<svg", html)
        self.assertIn("Red Flag Operasional", html)
        self.assertIn("Median Emiten IDX", html)
        self.assertIn("Forecast Risiko Ekonomi Daerah", html)
        self.assertIn("Disusun dengan TQ Board Insight", html)
        md = out_md.read_text(encoding="utf-8")
        self.assertIn("Kesiapan Data & Sistem", md)

    def test_report_kombinasi_bulanan_uji_kas_dan_sdm(self):
        sdm_json = self.tmp / "sdm.json"
        sdm_json.write_text(json.dumps({
            "sdm": {"total_kini": 120},
            "produktivitas": {
                "metrik": [
                    {"kunci": "pendapatan", "label": "Pendapatan per karyawan", "kini": 1700.0, "lalu": 1600.0},
                ]
            },
            "rekomendasi_departemen": [
                {
                    "departemen": "Produksi",
                    "karyawan_kini": 70,
                    "kpi_prioritas": ["Output per karyawan", "Reject (%)"],
                    "rekomendasi_budget": "Tahan penambahan headcount sampai utilisasi > 85%.",
                }
            ],
        }), encoding="utf-8")
        out_html = self.tmp / "komb-bulanan.html"
        r = run(
            KOMBINASI,
            "--laporan", self.laporan,
            "--uji-kas", self.uji_kas,
            "--sdm", sdm_json,
            "--out", out_html,
            "--diam",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        html = out_html.read_text(encoding="utf-8")
        self.assertIn("Uji Ketahanan Kas", html)
        self.assertIn("Produktivitas Rp per Karyawan", html)
        self.assertIn("Pendapatan / Karyawan", html)


if __name__ == "__main__":
    unittest.main()
