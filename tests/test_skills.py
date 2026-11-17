"""Uji regresi TQ Board Insight. Jalankan dari root repo:  python -m unittest discover tests -v"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
CASES = ["01-manufaktur-garmen", "02-distribusi-fmcg", "03-makanan-minuman", "04-komponen-logam"]
SAMPLE = ROOT / "sample-data" / CASES[0]
# Paket data lengkap (opsional, tidak termasuk repo). Atur lewat variabel lingkungan CHC_DATA_LENGKAP.
LENGKAP = Path(os.environ.get("CHC_DATA_LENGKAP", ROOT.parent / "materi-training" / "trainer" / "data-lengkap"))
RASIO = SK / "baca-laporan-keuangan/scripts/hitung_rasio.py"
EXCEL = SK / "baca-laporan-keuangan/scripts/baca_excel.py"
SAMAR = SK / "baca-laporan-keuangan/scripts/samarkan_lk.py"
GEJALA = SK / "red-flag-operasional/scripts/deteksi_gejala.py"
KESIAPAN = SK / "cek-kesiapan-data/scripts/skor_kesiapan.py"
BRIEF = SK / "board-brief/scripts/susun_brief.py"
LAPORAN = SK / "laporan-analisa/scripts/susun_laporan.py"
SAMAR_PAKET = SK / "laporan-analisa/scripts/samarkan_paket.py"
# Daftar istilah yang tidak boleh muncul di keluaran skill disimpan di luar repo (opsional).
_DAFTAR = Path(os.environ.get("CHC_ISTILAH_TERLARANG", ROOT.parent / "docs" / "istilah-terlarang.txt"))
TERLARANG = tuple(t.strip() for t in _DAFTAR.read_text(encoding="utf-8").splitlines() if t.strip()) if _DAFTAR.exists() else ()


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


def baca_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


class LKTahunan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        r = run(RASIO, SAMPLE / "lk-tahunan.json", "--out-json", cls.tmp / "rasio.json", "--diam")
        assert r.returncode == 0, r.stderr
        cls.rasio = baca_json(cls.tmp / "rasio.json")
        r = run(GEJALA, cls.tmp / "rasio.json", "--out-json", cls.tmp / "gejala.json", "--diam")
        assert r.returncode == 0, r.stderr
        cls.gejala = baca_json(cls.tmp / "gejala.json")

    def nilai(self, k, p):
        return self.rasio["rasio"][k]["nilai"][p]

    def test_cerita_garmen(self):
        pos = self.rasio["pos_utama"]
        self.assertGreater(pos["laba_bersih"]["perubahan"]["2024->2025"]["persen"], 10)
        self.assertLess(pos["arus_kas_operasi"]["nilai"]["2025"], 0)
        self.assertGreater(pos["persediaan"]["perubahan"]["2024->2025"]["persen"], 50)
        self.assertAlmostEqual(self.nilai("dio", "2024"), 62, delta=1.5)
        self.assertAlmostEqual(self.nilai("dio", "2025"), 92, delta=1.5)
        self.assertAlmostEqual(self.nilai("dso", "2025"), 76, delta=1.5)
        self.assertLess(self.nilai("gross_margin", "2025"), self.nilai("gross_margin", "2024"))

    def test_rasio_manual(self):
        lk = baca_json(SAMPLE / "lk-tahunan.json")
        n, lr = lk["neraca"], lk["laba_rugi"]
        p = "2025"
        self.assertAlmostEqual(self.nilai("current_ratio", p), n["total_aset_lancar"][p] / n["total_liabilitas_jangka_pendek"][p], 3)
        self.assertAlmostEqual(self.nilai("dio", p), n["persediaan"][p] / lr["beban_pokok_penjualan"][p] * 365, 3)
        self.assertAlmostEqual(self.nilai("roe", p), lr["laba_bersih"][p] / n["total_ekuitas"][p] * 100, 3)
        self.assertAlmostEqual(self.nilai("ccc", p), self.nilai("dio", p) + self.nilai("dso", p) - self.nilai("dpo", p), 3)

    def test_gejala_garmen(self):
        kode = [t["kode"] for t in self.gejala["temuan"]]
        for k in ("persediaan_menumpuk", "laba_naik_kas_turun", "piutang_melambat"):
            self.assertIn(k, kode)
        self.assertNotIn("overhead_naik", kode)

    def test_gejala_berbeda_per_industri(self):
        harap = {"03-makanan-minuman": "margin_tergerus", "04-komponen-logam": "overhead_naik",
                 "02-distribusi-fmcg": "laba_naik_kas_turun"}
        for case, kode in harap.items():
            r = run(RASIO, ROOT / "sample-data" / case / "lk-tahunan.json", "--out-json", self.tmp / f"r-{case}.json", "--diam")
            self.assertEqual(r.returncode, 0, r.stderr)
            run(GEJALA, self.tmp / f"r-{case}.json", "--out-json", self.tmp / f"g-{case}.json", "--diam")
            self.assertIn(kode, [t["kode"] for t in baca_json(self.tmp / f"g-{case}.json")["temuan"]], case)

    def test_semua_case_valid(self):
        for case in CASES:
            d = ROOT / "sample-data" / case
            for f in ("lk-tahunan.json", "LK-Tahunan.xlsx", "Data-Keuangan-Bulanan.xlsx", "jawaban-cek-kesiapan.json", "README.md"):
                self.assertTrue((d / f).exists(), f"{case}/{f}")
            self.assertTrue(list(d.glob("LK-2025-*.pdf")), case)
            self.assertEqual(run(RASIO, d / "lk-tahunan.json", "--diam").returncode, 0, case)

    @unittest.skipUnless(TERLARANG, "daftar istilah terlarang tidak tersedia")
    def test_tidak_ada_nama_program_di_repo_publik(self):
        teks = ""
        for f in list(SK.rglob("*.md")) + list(SK.rglob("*.json")) + list(SK.rglob("*.py")) + list(SK.rglob("*.html")):
            teks += f.read_text(encoding="utf-8")
        teks += json.dumps(self.gejala, ensure_ascii=False)
        for t in TERLARANG:
            self.assertNotIn(t, teks)

    def test_neraca_tidak_seimbang_berhenti(self):
        lk = baca_json(SAMPLE / "lk-tahunan.json")
        rusak = copy.deepcopy(lk)
        rusak["neraca"]["total_aset"]["2025"] += 5000
        f = self.tmp / "rusak.json"
        f.write_text(json.dumps(rusak), encoding="utf-8")
        r = run(RASIO, f, "--out-json", self.tmp / "x.json", "--diam")
        self.assertEqual(r.returncode, 2)
        self.assertIn("tidak seimbang", r.stderr)
        self.assertFalse((self.tmp / "x.json").exists())

    def test_kolom_wajib_kosong(self):
        lk = baca_json(SAMPLE / "lk-tahunan.json")
        del lk["laba_rugi"]["pendapatan"]
        f = self.tmp / "kurang.json"
        f.write_text(json.dumps(lk), encoding="utf-8")
        self.assertNotEqual(run(RASIO, f, "--diam").returncode, 0)

    def test_beban_negatif_dibalik(self):
        lk = baca_json(SAMPLE / "lk-tahunan.json")
        lk["laba_rugi"]["beban_pokok_penjualan"] = {k: -v for k, v in lk["laba_rugi"]["beban_pokok_penjualan"].items()}
        f = self.tmp / "neg.json"
        f.write_text(json.dumps(lk), encoding="utf-8")
        r = run(RASIO, f, "--out-json", self.tmp / "neg-r.json", "--diam")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = baca_json(self.tmp / "neg-r.json")
        self.assertAlmostEqual(out["rasio"]["dio"]["nilai"]["2025"], self.nilai("dio", "2025"), 6)
        self.assertTrue(out["validasi"]["peringatan"])

    def test_excel_sama_dengan_json(self):
        r = run(EXCEL, SAMPLE / "LK-Tahunan.xlsx", "--out", self.tmp / "xl.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b = baca_json(self.tmp / "xl.json"), baca_json(SAMPLE / "lk-tahunan.json")
        for k in ("periode", "neraca", "laba_rugi", "arus_kas"):
            self.assertEqual(a[k], b[k])

    def test_template_kosong_terbaca(self):
        r = run(EXCEL, SK / "baca-laporan-keuangan/templates/template-lk.xlsx", "--out", self.tmp / "kosong.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run(RASIO, self.tmp / "kosong.json", "--diam")
        self.assertEqual(r.returncode, 1)
        self.assertIn("wajib", r.stdout + r.stderr)

    def test_penyamaran_rasio_identik(self):
        run(SAMAR, SAMPLE / "lk-tahunan.json", "--out", self.tmp / "s.json", "--samarkan-periode")
        s = baca_json(self.tmp / "s.json")
        self.assertEqual(s["periode"], ["T-2", "T-1", "T"])
        self.assertNotIn("Garmen", json.dumps(s))
        r = run(RASIO, self.tmp / "s.json", "--out-json", self.tmp / "s-r.json", "--diam")
        self.assertEqual(r.returncode, 0, r.stderr)
        sr = baca_json(self.tmp / "s-r.json")
        for k in self.rasio["rasio"]:
            for p, q in (("2023", "T-2"), ("2024", "T-1"), ("2025", "T")):
                a, b = self.nilai(k, p), sr["rasio"][k]["nilai"][q]
                if a is None:
                    self.assertIsNone(b)
                else:
                    self.assertAlmostEqual(a, b, places=2, msg=k)

    def test_kesiapan_level(self):
        cases = {"AAAAAAAA": 1, "BBBBBBBB": 2, "CCCCCCCC": 3, "DDDDDDDD": 4, "ABBCABAC": 2, "DDDDDDCD": 4}
        for j, lv in cases.items():
            r = run(KESIAPAN, "--jawaban", j, "--out-json", self.tmp / "k.json", "--diam")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(baca_json(self.tmp / "k.json")["level"], lv, j)
        self.assertNotEqual(run(KESIAPAN, "--jawaban", "A,B,C", "--diam").returncode, 0)

    def test_brief(self):
        r = run(BRIEF, "--rasio", self.tmp / "rasio.json", "--gejala", self.tmp / "gejala.json",
                "--out-md", self.tmp / "b.md", "--out-html", self.tmp / "b.html", "--diam")
        self.assertEqual(r.returncode, 0, r.stderr)
        md = (self.tmp / "b.md").read_text(encoding="utf-8")
        self.assertIn("Disusun dengan TQ Board Insight · totalquality.co.id", md)
        self.assertNotIn("{{", md)
        self.assertIn("<!doctype html>", (self.tmp / "b.html").read_text(encoding="utf-8"))

    def test_skill_md_frontmatter(self):
        for d in SK.iterdir():
            teks = (d / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(teks.startswith("---\n"))
            fm = teks.split("---")[1]
            self.assertIn(f"name: {d.name}\n", fm)
            desc = [baris for baris in fm.splitlines() if baris.startswith("description:")][0]
            self.assertLessEqual(len(desc) - len("description: "), 1024)


class LaporanAnalisa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())

    def susun(self, paket, nama):
        r = run(LAPORAN, paket, "--out", self.tmp / f"{nama}.html", "--json", self.tmp / f"{nama}.json", "--diam")
        return r, (baca_json(self.tmp / f"{nama}.json") if r.returncode == 0 else None)

    def test_lk_saja_semua_case(self):
        for case in CASES:
            r, vm = self.susun(ROOT / "sample-data" / case / "Data-Keuangan-Bulanan.xlsx", f"lk-{case}")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(vm["meta"]["ops_terisi"], 0)
            self.assertTrue(all(g["status"] in ("Lulus", "PERLU DATA") for g in vm["gerbang"]), (case, vm["gerbang"]))
            self.assertTrue(any(c["penyebab"].startswith("PERLU DATA") for c in vm["cerita"]), case)
            self.assertEqual(len(vm["kpi"]["month"]["yoy"]), 15)
            html = (self.tmp / f"lk-{case}.html").read_text(encoding="utf-8")
            self.assertNotIn("/*__DATA__*/null", html)
            self.assertIn("Disusun dengan TQ Board Insight", html)

    def test_kpi_dihitung_benar(self):
        sys.path.insert(0, str(SK / "laporan-analisa/scripts"))
        from baca_paket import baca
        p = baca(SAMPLE / "Data-Keuangan-Bulanan.xlsx")
        lr, n = p["laba_rugi"], p["neraca"]
        b = "2026-10"
        hpp = sum(lr[k][b] for k in ("hpp_bahan", "hpp_upah", "hpp_overhead", "hpp_penyusutan"))
        inv = sum(n[k][b] for k in ("persediaan_bahan_baku", "persediaan_barang_dalam_proses", "persediaan_barang_jadi"))
        dio = inv / hpp * 31
        r, vm = self.susun(SAMPLE / "Data-Keuangan-Bulanan.xlsx", "cek")
        row = [x for x in vm["kpi"]["month"]["yoy"] if x["key"] == "dio"][0]
        self.assertEqual(row["cur"], f"{round(dio)} hari")

    def test_target_perlu_data(self):
        r, vm = self.susun(ROOT / "sample-data" / CASES[1] / "Data-Keuangan-Bulanan.xlsx", "fmcg")
        self.assertFalse(vm["periode"]["month"]["comps"]["target"]["ada"])
        r, vm = self.susun(SAMPLE / "Data-Keuangan-Bulanan.xlsx", "garmen")
        self.assertTrue(vm["periode"]["month"]["comps"]["target"]["ada"])

    def test_neraca_rusak_berhenti(self):
        from openpyxl import load_workbook
        wb = load_workbook(SAMPLE / "Data-Keuangan-Bulanan.xlsx")
        ws = wb["Neraca"]
        for row in ws.iter_rows(min_row=2):
            if row[0].value == "kas":
                row[10].value = (row[10].value or 0) + 5000
        f = self.tmp / "rusak.xlsx"
        wb.save(f)
        r, _ = self.susun(f, "rusak")
        self.assertEqual(r.returncode, 2)
        self.assertIn("G1", r.stderr)

    def test_samarkan_paket_status_sama(self):
        f = self.tmp / "samar.xlsx"
        r = run(SAMAR_PAKET, SAMPLE / "Data-Keuangan-Bulanan.xlsx", "--out", f)
        self.assertEqual(r.returncode, 0, r.stderr)
        _, a = self.susun(SAMPLE / "Data-Keuangan-Bulanan.xlsx", "asli")
        _, b = self.susun(f, "samar")
        self.assertTrue(b["meta"]["samaran"])
        self.assertNotIn("Nusantara", b["meta"]["perusahaan"])  # nama disamarkan; bidang industri sengaja dipertahankan
        for pid in ("month", "quarter", "ytd"):
            sa = [(x["key"], x["status"], x["cur"]) for x in a["kpi"][pid]["yoy"] if x["key"] not in ()]
            sb = [(x["key"], x["status"], x["cur"]) for x in b["kpi"][pid]["yoy"]]
            self.assertEqual(sa, sb, pid)

    @unittest.skipUnless(LENGKAP.exists(), "paket data lengkap hanya ada di folder trainer")
    def test_paket_lengkap_menjawab_penyebab(self):
        for case in CASES:
            r, vm = self.susun(LENGKAP / case / "Paket-Data-Lengkap.xlsx", f"full-{case}")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(vm["meta"]["ops_terisi"], 6, case)
            self.assertTrue(all(g["status"] == "Lulus" for g in vm["gerbang"] if g["kode"] != "G7"), case)
            self.assertFalse(any(c["penyebab"].startswith("PERLU DATA") for c in vm["cerita"] if c["sev"] != "aman"), case)


if __name__ == "__main__":
    unittest.main()
