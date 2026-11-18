"""Tes fitur v1.2: rasio tambahan & perhitungan, metode rata-rata, gaya narasi, visualisasi, preferensi,
mode direksi laporan-analisa, dan data-emiten (offline, memakai fixture). Jalankan: python -m unittest discover tests -v"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
SAMPLE = ROOT / "sample-data" / "01-manufaktur-garmen"
RASIO = SK / "baca-laporan-keuangan/scripts/hitung_rasio.py"
VISUAL = SK / "baca-laporan-keuangan/scripts/visualisasi.py"
PREF = SK / "tampilan-direksi/scripts/preferensi.py"
GEJALA = SK / "red-flag-operasional/scripts/deteksi_gejala.py"
BRIEF = SK / "board-brief/scripts/susun_brief.py"
LAPORAN = SK / "laporan-analisa/scripts/susun_laporan.py"
RINGKAS_EMITEN = SK / "data-emiten/scripts/ringkas_emiten.py"
FIXTURE = ROOT / "tests/fixtures/emiten-contoh.json"


def run(*a):
    return subprocess.run([sys.executable, *map(str, a)], capture_output=True, text=True, encoding="utf-8")


def js(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


class FiturBaru(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Path(tempfile.mkdtemp())
        r = run(RASIO, SAMPLE / "lk-tahunan.json", "--out-json", cls.t / "r.json", "--diam")
        assert r.returncode == 0, r.stderr
        cls.r = js(cls.t / "r.json")
        cls.lk = js(SAMPLE / "lk-tahunan.json")

    def v(self, k, p="2025"):
        return self.r["rasio"][k]["nilai"][p]

    def test_rasio_tambahan_manual(self):
        n, lr, ak = self.lk["neraca"], self.lk["laba_rugi"], self.lk["arus_kas"]
        p = "2025"
        self.assertAlmostEqual(self.v("cash_ratio"), n["kas_dan_setara_kas"][p] / n["total_liabilitas_jangka_pendek"][p], 3)
        ebitda = lr["laba_usaha"][p] + lr["penyusutan"][p]
        self.assertAlmostEqual(self.v("ebitda_margin"), ebitda / lr["pendapatan"][p] * 100, 3)
        self.assertAlmostEqual(self.v("effective_tax"), lr["beban_pajak"][p] / lr["laba_sebelum_pajak"][p] * 100, 3)
        self.assertAlmostEqual(self.v("equity_multiplier"), n["total_aset"][p] / n["total_ekuitas"][p], 3)
        self.assertAlmostEqual(self.v("inventory_turnover"), lr["beban_pokok_penjualan"][p] / n["persediaan"][p], 3)
        self.assertAlmostEqual(self.v("fcf_margin"), (ak["arus_kas_operasi"][p] - ak["belanja_modal"][p]) / lr["pendapatan"][p] * 100, 3)
        ta, tl = n["total_aset"][p], n["total_liabilitas"][p]
        z = (6.56 * (n["total_aset_lancar"][p] - n["total_liabilitas_jangka_pendek"][p]) / ta + 3.26 * n["saldo_laba"][p] / ta
             + 6.72 * lr["laba_usaha"][p] / ta + 1.05 * n["total_ekuitas"][p] / tl)
        self.assertAlmostEqual(self.v("altman_z"), z, 3)
        # DuPont: ROE = NM x AT x EM
        self.assertAlmostEqual(self.v("roe"), self.v("net_margin") * self.v("asset_turnover") * self.v("equity_multiplier"), 2)

    def test_perhitungan_tersedia(self):
        for k, x in self.r["rasio"].items():
            self.assertIn("2025", x["perhitungan"], k)
        self.assertIn("÷", self.r["rasio"]["current_ratio"]["perhitungan"]["2025"])

    def test_metode_rata_rata(self):
        run(RASIO, SAMPLE / "lk-tahunan.json", "--out-json", self.t / "rr.json", "--metode", "rata-rata", "--diam")
        rr = js(self.t / "rr.json")
        n, lr = self.lk["neraca"], self.lk["laba_rugi"]
        avg = (n["persediaan"]["2024"] + n["persediaan"]["2025"]) / 2
        self.assertAlmostEqual(rr["rasio"]["inventory_turnover"]["nilai"]["2025"], lr["beban_pokok_penjualan"]["2025"] / avg, 3)
        # periode pertama tetap saldo akhir
        self.assertAlmostEqual(rr["rasio"]["dio"]["nilai"]["2023"], self.v("dio", "2023"), 6)
        self.assertEqual(rr["meta"]["metode_kode"], "rata-rata")

    def test_laba_usaha_tanpa_rincian_beban(self):
        lk = dict(self.lk)
        lk["laba_rugi"] = {k: v for k, v in self.lk["laba_rugi"].items()
                           if k not in ("beban_penjualan", "beban_umum_administrasi", "beban_usaha")}
        f = self.t / "tanpa-rincian.json"
        f.write_text(json.dumps(lk), encoding="utf-8")
        r = run(RASIO, f, "--diam")
        self.assertEqual(r.returncode, 0, r.stderr)  # regresi bug yang ditemukan saat uji akurasi emiten

    def test_tiga_gaya(self):
        for gaya, penanda in (("ringkas", "Tiga hal yang perlu perhatian"), ("detail", "Perhitungan 2025"),
                              ("checklist", "- [ ]")):
            r = run(RASIO, SAMPLE / "lk-tahunan.json", "--gaya", gaya)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(penanda, r.stdout, gaya)
            self.assertIn("Disusun dengan TQ Board Insight", r.stdout)

    def test_visualisasi(self):
        for mode in ("grafik", "penjelasan", "keduanya"):
            out = self.t / f"v-{mode}.html"
            r = run(VISUAL, self.t / "r.json", "--out", out, "--mode", mode)
            self.assertEqual(r.returncode, 0, r.stderr)
            h = out.read_text(encoding="utf-8")
            self.assertEqual("<svg" in h, mode != "penjelasan", mode)
            self.assertEqual("Cara membaca" in h, mode != "grafik", mode)
        r = run(VISUAL, self.t / "r.json", "--out", self.t / "v.md", "--mode", "penjelasan")
        self.assertIn("Pertanyaan untuk tim minggu ini", (self.t / "v.md").read_text(encoding="utf-8"))

    def test_preferensi(self):
        f = self.t / "pref.json"
        r = run(PREF, "--jawaban", "1B,2C,3A,4C", "--out", f)
        self.assertEqual(r.returncode, 0, r.stderr)
        p = js(f)
        self.assertEqual((p["audiens"], p["gaya_narasi"], p["visual"], p["fokus"]), ("komisaris", "checklist", "grafik", "profitabilitas"))
        self.assertNotEqual(run(PREF, "--set", "gaya_narasi=puisi").returncode, 0)
        r = run(RASIO, SAMPLE / "lk-tahunan.json", "--preferensi", f)
        self.assertIn("- [", r.stdout)
        for preset in ("direksi", "komisaris", "keuangan", "bank"):
            self.assertEqual(run(PREF, "--preset", preset).returncode, 0, preset)

    def test_gaya_red_flag_dan_brief(self):
        run(GEJALA, self.t / "r.json", "--out-json", self.t / "g.json", "--diam")
        r = run(GEJALA, self.t / "r.json", "--gaya", "checklist")
        self.assertIn("- [ ]", r.stdout)
        r = run(BRIEF, "--rasio", self.t / "r.json", "--gejala", self.t / "g.json", "--gaya", "checklist")
        self.assertIn("- [ ]", r.stdout)

    def test_mode_direksi_laporan(self):
        out = self.t / "lap.html"
        r = run(LAPORAN, SAMPLE / "Data-Keuangan-Bulanan.xlsx", "--out", out, "--mode", "direksi", "--gaya-cerita", "checklist", "--diam")
        self.assertEqual(r.returncode, 0, r.stderr)
        h = out.read_text(encoding="utf-8")
        self.assertIn('"tampilan":{"mode":"direksi","cerita":"checklist"}', h)
        self.assertIn("Tiga hal yang perlu Anda ketahui", h)
        self.assertIn("Cara membaca", h)
        for tab in ("Ringkasan", "Kesehatan", "Arus kas", "Operasional", "Rumus & data"):
            self.assertIn(tab, h)

    def test_ringkas_emiten_offline(self):
        r = run(RINGKAS_EMITEN, FIXTURE, "--rasio", self.t / "r.json", "--out-json", self.t / "e.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        e = js(self.t / "e.json")
        self.assertEqual(len(e["emiten"]), 7)
        unvr = e["emiten"]["UNVR"]
        mentah = js(FIXTURE)["emiten"]["UNVR"]
        self.assertAlmostEqual(unvr["pertumbuhan"], (mentah["total_revenue_fy_h"][0] / mentah["total_revenue_fy_h"][1] - 1) * 100, 6)
        self.assertAlmostEqual(unvr["cfo_ni"], mentah["cash_f_operating_activities_fy"] / mentah["net_income_fy_h"][0], 6)
        self.assertIsNotNone(unvr["qr"])
        self.assertIn("posisi", e)
        self.assertIn("cfo_ni", e["posisi"])
        self.assertIn("Perusahaan Anda", r.stdout)
        self.assertIn("TIDAK RESMI".lower(), js(FIXTURE)["sumber"].lower())
        r = run(RINGKAS_EMITEN, FIXTURE, "--rasio", self.t / "r.json", "--gaya", "checklist")
        self.assertIn("vs median", r.stdout)

    def test_ringkas_emiten_ekuitas_negatif_dan_mata_uang(self):
        contoh = {
            "sumber": "Uji",
            "diambil": "2026-11-18T00:00:00Z",
            "emiten": {
                "TEST1": {
                    "description": "PT Uji Ekuitas Negatif",
                    "sector": "Finance",
                    "industry": "Banks",
                    "currency": "IDR",
                    "fundamental_currency_code": "USD",
                    "market_cap_basic": 800_000_000,
                    "total_revenue_fy_h": [500_000_000, 400_000_000],
                    "net_income_fy_h": [50_000_000],
                    "total_liabilities_fy": 1_000_000_000,
                    "total_equity_fy": -100_000_000,
                    "return_on_equity_fy": -50.0,
                    "debt_to_equity_fy": -2.0,
                    "cash_f_operating_activities_fy": 75_000_000,
                }
            },
        }
        f = self.t / "em-neg.json"
        f.write_text(json.dumps(contoh), encoding="utf-8")
        r = run(RINGKAS_EMITEN, f, "--out-json", self.t / "em-neg-out.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = js(self.t / "em-neg-out.json")
        t1 = out["emiten"]["TEST1"]
        self.assertIsNone(t1["der"])
        self.assertIsNone(t1["de"])
        self.assertIsNone(t1["roe"])
        self.assertAlmostEqual(t1["cfo_ni"], 1.5, 6)
        self.assertIn("Rp800 JT", r.stdout)
        self.assertIn("USD 500 JT", r.stdout)
        self.assertIn("Finance", r.stdout)
        self.assertIn("ekuitas nol/negatif", r.stdout)

    def test_ringkas_emiten_dari_laporan_bulanan(self):
        lap_json = self.t / "lap-bulanan.json"
        r_lap = run(LAPORAN, SAMPLE / "Data-Keuangan-Bulanan.xlsx", "--out", self.t / "lap-bulanan.html",
                    "--json", lap_json, "--diam")
        self.assertEqual(r_lap.returncode, 0, r_lap.stderr)
        r = run(RINGKAS_EMITEN, FIXTURE, "--rasio", lap_json, "--out-json", self.t / "e-bulanan.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = js(self.t / "e-bulanan.json")
        self.assertIsNotNone(out["pengguna"]["gm"])
        self.assertIsNotNone(out["pengguna"]["om"])
        self.assertIsNotNone(out["pengguna"]["der"])
        self.assertIn("Perusahaan Anda", r.stdout)


if __name__ == "__main__":
    unittest.main()
