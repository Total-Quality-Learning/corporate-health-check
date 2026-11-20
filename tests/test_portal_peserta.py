"""Uji wrapper web portal peserta (tools/portal_peserta.py)."""
from __future__ import annotations

import base64
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import portal_peserta as pp  # noqa: E402


def http_req(url: str, body: dict | None = None) -> tuple[int, dict[str, str], bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


class PortalPesertaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = pp.JobStore(base_dir=Path(cls.tmp.name), max_jobs=10)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), pp.buat_handler(cls.store))
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.store.tutup()
        cls.tmp.cleanup()

    def test_index_info_dan_template(self):
        status, _, html = http_req(f"{self.base}/")
        self.assertEqual(status, 200)
        self.assertIn("Portal Peserta", html.decode("utf-8"))

        status, _, raw = http_req(f"{self.base}/api/info")
        self.assertEqual(status, 200)
        info = json.loads(raw.decode("utf-8"))
        self.assertEqual(len(info["cases"]), 4)
        self.assertEqual(len(info["pertanyaan_kesiapan"]), 8)

        status, _, tpl = http_req(f"{self.base}/api/template/template-lk.xlsx")
        self.assertEqual(status, 200)
        self.assertTrue(tpl.startswith(b"PK"))  # format zip/xlsx

    def test_laporan_analisa_sample_dan_samarkan(self):
        status, _, raw = http_req(
            f"{self.base}/api/laporan-analisa",
            {"sample_case": "01-manufaktur-garmen", "mode": "direksi", "gaya_cerita": "narasi", "samarkan": True},
        )
        self.assertEqual(status, 200, raw.decode("utf-8"))
        res = json.loads(raw.decode("utf-8"))
        self.assertTrue(res["ok"])
        self.assertIn("laporan.html", res["files"])
        self.assertIn("paket-samaran.xlsx", res["files"])
        self.assertTrue(res["ringkasan"]["meta"]["samaran"])

        s_html, _, body = http_req(f"{self.base}/api/job/{res['job_id']}/laporan.html")
        self.assertEqual(s_html, 200)
        self.assertIn("Disusun dengan TQ Board Insight", body.decode("utf-8"))

        # Pastikan path traversal ditolak
        s_bad, _, _ = http_req(f"{self.base}/api/job/{res['job_id']}/../secret.txt")
        self.assertEqual(s_bad, 404)

    def test_analisis_tahunan_upload_samarkan_dan_neraca_rusak(self):
        sample_json = ROOT / "sample-data/01-manufaktur-garmen/lk-tahunan.json"
        b64 = base64.b64encode(sample_json.read_bytes()).decode("ascii")
        status, _, raw = http_req(
            f"{self.base}/api/analisis-tahunan",
            {
                "file_name": "lk.json",
                "file_b64": b64,
                "gaya": "detail",
                "metode": "rata-rata",
                "samarkan": True,
                "kesiapan": "A,B,B,C,A,B,A,C",
            },
        )
        self.assertEqual(status, 200, raw.decode("utf-8"))
        res = json.loads(raw.decode("utf-8"))
        self.assertIn("brief.html", res["files"])
        self.assertIn("lk-samaran.json", res["files"])
        self.assertIn("hasil.zip", res["files"])
        self.assertTrue(res["kesiapan_md"])
        self.assertNotIn("Garmen", res["brief_md"])

        # Neraca tidak seimbang harus berhenti dengan 422
        rusak = json.loads(sample_json.read_text(encoding="utf-8"))
        rusak["neraca"]["total_aset"]["2025"] += 5000
        b64_rusak = base64.b64encode(json.dumps(rusak).encode("utf-8")).decode("ascii")
        s_err, _, err_raw = http_req(
            f"{self.base}/api/analisis-tahunan",
            {"file_name": "rusak.json", "file_b64": b64_rusak},
        )
        self.assertEqual(s_err, 422)
        err_json = json.loads(err_raw.decode("utf-8"))
        self.assertEqual(err_json["kode"], "VALIDASI_GAGAL")

    def test_uji_kas_kustom(self):
        status, _, raw = http_req(
            f"{self.base}/api/uji-kas",
            {
                "sample_case": "03-makanan-minuman",
                "horizon": 6,
                "plafon": 500,
                "batas_dscr": 1.25,
                "skenario": [{"nama": "Uji", "penjualan_pct": -15}],
            },
        )
        self.assertEqual(status, 200, raw.decode("utf-8"))
        res = json.loads(raw.decode("utf-8"))
        self.assertEqual(res["data"]["horizon"], 6)
        self.assertEqual(len(res["data"]["skenario"]), 1)
        self.assertIn("Uji balik", res["md"])

    def test_konversi_csv_tahunan_ekonomi_dan_emiten_offline(self):
        csv_lk = (
            "Akun,2024,2025\n"
            "Kas dan Setara Kas,100,140\n"
            "Piutang Usaha,200,240\n"
            "Persediaan,150,170\n"
            "Total Aset Lancar,450,550\n"
            "Aset Tetap Neto,550,650\n"
            "Total Aset,1000,1200\n"
            "Utang Usaha,150,180\n"
            "Utang Bank Jangka Pendek,100,120\n"
            "Total Liabilitas Jangka Pendek,250,300\n"
            "Utang Bank Jangka Panjang,250,260\n"
            "Total Liabilitas,500,560\n"
            "Modal Saham,350,350\n"
            "Saldo Laba,150,290\n"
            "Total Ekuitas,500,640\n"
            "Penjualan Neto,1800,2100\n"
            "Beban Pokok Penjualan,1200,1380\n"
            "Beban Usaha,350,390\n"
            "Beban Bunga,40,38\n"
            "Beban Pajak Penghasilan,46,64\n"
            "Laba Bersih,164,228\n"
            "Arus Kas Operasi,190,230\n"
        ).encode("utf-8")
        st, _, raw = http_req(
            f"{self.base}/api/analisis-tahunan",
            {
                "file_name": "lk-bebas.csv",
                "file_b64": base64.b64encode(csv_lk).decode("ascii"),
                "konversi_bebas": True,
                "perusahaan": "PT Uji Format Bebas",
                "gaya": "ringkas",
            },
        )
        self.assertEqual(st, 200, raw.decode("utf-8"))
        res_t = json.loads(raw.decode("utf-8"))
        self.assertIn("rasio.json", res_t["files"])
        rasio_job = res_t["job_id"]

        tpl_ek = (ROOT / "skills" / "kondisi-ekonomi-daerah" / "templates" / "template-ekonomi-daerah.csv").read_bytes()
        st_e, _, raw_e = http_req(
            f"{self.base}/api/ekonomi-daerah",
            {
                "daerah": "Jawa Barat",
                "offline": True,
                "file_name": "daerah.csv",
                "file_b64": base64.b64encode(tpl_ek).decode("ascii"),
                "rasio_job_id": rasio_job,
                "rasio_file": "rasio.json",
            },
        )
        self.assertEqual(st_e, 200, raw_e.decode("utf-8"))
        res_e = json.loads(raw_e.decode("utf-8"))
        self.assertIn("skenario-makro.json", res_e["files"])
        self.assertIn("risiko-ekonomi.md", res_e["files"])
        self.assertTrue(len(res_e["skenario"]) >= 1)

        em_fix = (ROOT / "tests" / "fixtures" / "emiten-contoh.json").read_bytes()
        st_em, _, raw_em = http_req(
            f"{self.base}/api/emiten",
            {
                "action": "bandingkan",
                "file_name": "emiten-contoh.json",
                "file_b64": base64.b64encode(em_fix).decode("ascii"),
                "rasio_job_id": rasio_job,
                "rasio_file": "rasio.json",
            },
        )
        self.assertEqual(st_em, 200, raw_em.decode("utf-8"))
        res_em = json.loads(raw_em.decode("utf-8"))
        self.assertIn("pembanding.md", res_em["files"])
        self.assertIn("Perusahaan Anda", res_em["md"])

    @unittest.skipUnless(
        (pp.SK / "efisiensi-sdm-departemen" / "scripts" / "analisa_sdm_budget.py").is_file(),
        "membutuhkan modul efisiensi-sdm-departemen",
    )
    def test_sdm_budget_opsional(self):
        st, _, raw = http_req(
            f"{self.base}/api/sdm-budget",
            {
                "sample_case": "01-manufaktur-garmen",
                "karyawan": 120,
                "karyawan_lalu": 115,
                "departemen": [
                    {"nama": "Produksi", "karyawan": 75},
                    {"nama": "Penjualan", "karyawan": 25},
                    {"nama": "Umum", "karyawan": 20},
                ],
            },
        )
        self.assertEqual(st, 200, raw.decode("utf-8"))
        res = json.loads(raw.decode("utf-8"))
        self.assertIn("sdm-budget.json", res["files"])

    @unittest.skipUnless(
        (pp.ROOT / "tools" / "susun_report_kombinasi.py").is_file(),
        "membutuhkan tools/susun_report_kombinasi.py",
    )
    def test_report_kombinasi_opsional(self):
        st_t, _, raw_t = http_req(
            f"{self.base}/api/analisis-tahunan",
            {"sample_case": "01-manufaktur-garmen", "gaya": "ringkas"},
        )
        self.assertEqual(st_t, 200)
        res_t = json.loads(raw_t.decode("utf-8"))
        st_k, _, raw_k = http_req(
            f"{self.base}/api/report-kombinasi",
            {
                "judul": "Paket Uji Portal",
                "sumber": {
                    "rasio": {"job_id": res_t["job_id"], "file": "rasio.json"},
                    "gejala": {"job_id": res_t["job_id"], "file": "gejala.json"},
                },
            },
        )
        self.assertEqual(st_k, 200, raw_k.decode("utf-8"))
        res_k = json.loads(raw_k.decode("utf-8"))
        self.assertIn("report-kombinasi.html", res_k["files"])


if __name__ == "__main__":
    unittest.main()
