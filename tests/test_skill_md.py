"""Aturan isi SKILL.md: pagar saat skrip tidak bisa dijalankan, teks pertanyaan yang sinkron, dan tipografi."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
SKILLS = sorted(d for d in SK.iterdir() if (d / "SKILL.md").exists())


def baca(d: Path) -> str:
    return (d / "SKILL.md").read_text(encoding="utf-8")


class IsiSkillMd(unittest.TestCase):

    def test_setiap_skill_punya_pagar_tanpa_skrip(self):
        # Uji coba dengan model kecil di aplikasi chat menunjukkan model mengarang angka bila skrip tidak jalan.
        for d in SKILLS:
            with self.subTest(skill=d.name):
                teks = baca(d)
                self.assertIn("tidak bisa dijalankan", teks)
                self.assertIn("Jangan pernah menulis bahwa skrip sudah dijalankan", teks)

    def test_skill_khusus_skrip_melarang_angka_karangan(self):
        self.assertIn("**Berhenti.**", baca(SK / "laporan-analisa"))
        self.assertIn("Jangan menampilkan angka emiten apa pun", baca(SK / "data-emiten"))
        self.assertIn("jangan membuat model kas sendiri", baca(SK / "uji-ketahanan-kas"))
        # Model dengan sandbox kode cenderung menulis ulang skrip sendiri; itu tidak boleh dianggap menjalankan skrip.
        for nama in ("laporan-analisa", "uji-ketahanan-kas", "data-emiten"):
            self.assertIn("Menulis kode sendiri untuk meniru skrip **tidak dihitung**", baca(SK / nama))

    def test_board_brief_kesiapan_hanya_bila_ada(self):
        teks = baca(SK / "board-brief")
        self.assertIn("jangan menilai kesiapan data sendiri", teks)
        self.assertIn("Penyebab selalu hipotesis", teks)

    def test_pertanyaan_preferensi_sama_dengan_skrip(self):
        hasil = subprocess.run([sys.executable, str(SK / "tampilan-direksi/scripts/preferensi.py"), "--pertanyaan"],
                               capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(hasil.returncode, 0, hasil.stderr)
        inti = hasil.stdout.split("Pertanyaan lanjutan")[0].strip().split("\n", 2)[2].strip()
        self.assertIn(inti, baca(SK / "tampilan-direksi"))

    def test_footer_disalin_persis(self):
        # tampilan-direksi hanya menanyakan preferensi, tidak menghasilkan keluaran analisis.
        for d in (d for d in SKILLS if d.name != "tampilan-direksi"):
            with self.subTest(skill=d.name):
                self.assertIn("Disusun dengan TQ Board Insight | totalquality.co.id", baca(d))

    def test_tipografi_natural(self):
        for f in SK.rglob("*.md"):
            teks = f.read_text(encoding="utf-8")
            for c in ("—", "–", "·", "…", "±"):
                with self.subTest(berkas=str(f.relative_to(ROOT)), karakter=repr(c)):
                    self.assertNotIn(c, teks)


if __name__ == "__main__":
    unittest.main()
