#!/usr/bin/env python3
"""Portal Web Peserta (wrapper deterministik) untuk Corporate Health Check.

Membungkus skrip Python di folder skills/ menjadi aplikasi web lokal/kelas tanpa
dependensi tambahan di luar requirements.txt (hanya pustaka standar + openpyxl).

Pemakaian (dari root repo):
    python tools/portal_peserta.py
    python tools/portal_peserta.py --host 0.0.0.0 --port 8080 --no-browser
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
import webbrowser
import zipfile
from collections import OrderedDict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
SAMPLE = ROOT / "sample-data"
HTML_FILE = Path(__file__).resolve().parent / "portal_peserta.html"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_JOBS = 40
JOB_ID_RE = re.compile(r"^[a-f0-9]{12}$")

TEMPLATES = {
    "template-lk.xlsx": SK / "baca-laporan-keuangan" / "templates" / "template-lk.xlsx",
    "template-paket-data.xlsx": SK / "laporan-analisa" / "templates" / "template-paket-data.xlsx",
    "template-ekonomi-daerah.csv": SK / "kondisi-ekonomi-daerah" / "templates" / "template-ekonomi-daerah.csv",
    "template-sdm-departemen.csv": SK / "efisiensi-sdm-departemen" / "templates" / "template-sdm-departemen.csv",
}

ALLOWED_DATA_EXTS = (".xlsx", ".xlsm", ".json", ".csv", ".tsv")


def daftar_case() -> list[dict]:
    """Kumpulkan daftar data contoh fiktif yang tersedia di sample-data/."""
    hasil = []
    if not SAMPLE.exists():
        return hasil
    for d in sorted(SAMPLE.iterdir()):
        if not d.is_dir():
            continue
        readme = d / "README.md"
        judul = d.name
        ringkas = ""
        if readme.exists():
            baris = [b.strip() for b in readme.read_text(encoding="utf-8").splitlines() if b.strip()]
            if baris:
                judul = baris[0].lstrip("# ").strip()
            if len(baris) > 1:
                ringkas = baris[1]
        hasil.append({
            "id": d.name,
            "judul": judul,
            "ringkas": ringkas,
            "ada_bulanan": (d / "Data-Keuangan-Bulanan.xlsx").exists(),
            "ada_tahunan_xlsx": (d / "LK-Tahunan.xlsx").exists(),
            "ada_tahunan_json": (d / "lk-tahunan.json").exists(),
            "ada_kesiapan": (d / "jawaban-cek-kesiapan.json").exists(),
        })
    return hasil


def info_aplikasi() -> dict:
    """Metadata statis untuk antarmuka peserta."""
    pertanyaan_path = SK / "cek-kesiapan-data" / "references" / "pertanyaan.json"
    pertanyaan = json.loads(pertanyaan_path.read_text(encoding="utf-8")) if pertanyaan_path.exists() else {}
    tpls = [
        {"nama": "template-lk.xlsx", "label": "Template LK Tahunan (Excel)", "url": "/api/template/template-lk.xlsx"},
        {"nama": "template-paket-data.xlsx", "label": "Template Paket Data Bulanan (>= 13 bulan, Excel)", "url": "/api/template/template-paket-data.xlsx"},
    ]
    if TEMPLATES["template-ekonomi-daerah.csv"].is_file():
        tpls.append({"nama": "template-ekonomi-daerah.csv", "label": "Template Data Ekonomi Daerah (CSV)", "url": "/api/template/template-ekonomi-daerah.csv"})
    if TEMPLATES["template-sdm-departemen.csv"].is_file():
        tpls.append({"nama": "template-sdm-departemen.csv", "label": "Template SDM & Departemen (CSV)", "url": "/api/template/template-sdm-departemen.csv"})
    return {
        "cases": daftar_case(),
        "pertanyaan_kesiapan": pertanyaan.get("pertanyaan", []),
        "templates": tpls,
        "fitur": {
            "konversi_bebas": (ROOT / "tools" / "konversi_data.py").is_file(),
            "trial_balance": (ROOT / "tools" / "trial_balance.py").is_file(),
            "ekonomi_daerah": (SK / "kondisi-ekonomi-daerah" / "scripts" / "analisa_risiko_ekonomi.py").is_file(),
            "sdm_budget": (SK / "efisiensi-sdm-departemen" / "scripts" / "analisa_sdm_budget.py").is_file(),
            "report_kombinasi": (ROOT / "tools" / "susun_report_kombinasi.py").is_file(),
            "emiten_node": bool(shutil.which("node")) and (SK / "data-emiten" / "scripts" / "node_modules").is_dir(),
        },
    }


class JobStore:
    """Penyimpanan sementara berkas keluaran per sesi analisis."""

    def __init__(self, base_dir: Path | None = None, max_jobs: int = MAX_JOBS):
        self._own_tmp = None
        if base_dir is None:
            self._own_tmp = tempfile.TemporaryDirectory(prefix="chc-portal-")
            base_dir = Path(self._own_tmp.name)
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_jobs = max_jobs
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, tuple[Path, set[str]]] = OrderedDict()

    def buat_job(self) -> tuple[str, Path]:
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_id, job_dir

    def daftarkan(self, job_id: str, job_dir: Path, files: list[str]) -> None:
        with self._lock:
            self._jobs[job_id] = (job_dir, set(files))
            self._jobs.move_to_end(job_id)
            while len(self._jobs) > self.max_jobs:
                _, (old_dir, _) = self._jobs.popitem(last=False)
                shutil.rmtree(old_dir, ignore_errors=True)

    def ambil_file(self, job_id: str, filename: str) -> Path | None:
        if not JOB_ID_RE.fullmatch(job_id) or "/" in filename or "\\" in filename or ".." in filename:
            return None
        with self._lock:
            entri = self._jobs.get(job_id)
            if not entri:
                return None
            job_dir, allowed = entri
            if filename not in allowed:
                return None
            p = job_dir / filename
            return p if p.is_file() else None

    def tutup(self) -> None:
        if self._own_tmp is not None:
            self._own_tmp.cleanup()
            self._own_tmp = None


def _run_script(*args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )


def _pesan_galat(proc: subprocess.CompletedProcess[str]) -> str:
    teks = (proc.stderr or "").strip() or (proc.stdout or "").strip()
    return teks or f"Skrip berhenti dengan kode {proc.returncode}."


def _resolve_input(
    payload: dict,
    job_dir: Path,
    allowed_exts: tuple[str, ...],
    sample_candidates: tuple[str, ...],
) -> tuple[Path | None, tuple[int, dict] | None]:
    sample_case = (payload.get("sample_case") or "").strip()
    if sample_case:
        cases_valid = {c["id"] for c in daftar_case()}
        if sample_case not in cases_valid:
            return None, (400, {"ok": False, "error": f"Data contoh '{sample_case}' tidak ditemukan."})
        for cand in sample_candidates:
            p = SAMPLE / sample_case / cand
            if p.is_file():
                return p, None
        return None, (400, {"ok": False, "error": f"Berkas contoh untuk '{sample_case}' tidak tersedia."})

    file_name = (payload.get("file_name") or "").strip()
    file_b64 = payload.get("file_b64") or ""
    if not file_name or not file_b64:
        return None, (400, {"ok": False, "error": "Pilih data contoh atau unggah berkas terlebih dahulu."})

    ext = Path(file_name).suffix.lower()
    if ext not in allowed_exts:
        return None, (400, {"ok": False, "error": f"Format berkas harus salah satu dari: {', '.join(allowed_exts)}."})

    if "," in file_b64 and file_b64.startswith("data:"):
        file_b64 = file_b64.split(",", 1)[1]
    try:
        raw = base64.b64decode(file_b64, validate=True)
    except (binascii.Error, ValueError):
        return None, (400, {"ok": False, "error": "Isi berkas base64 tidak valid."})
    if len(raw) > MAX_UPLOAD_BYTES:
        return None, (400, {"ok": False, "error": "Ukuran berkas melebihi batas 25 MB."})
    if not raw:
        return None, (400, {"ok": False, "error": "Berkas unggahan kosong."})

    tujuan = job_dir / f"input{ext}"
    tujuan.write_bytes(raw)
    return tujuan, None


def _konversi_input_jika_perlu(
    src: Path,
    job_dir: Path,
    jenis: str,
    payload: dict,
) -> tuple[Path, list[str], tuple[int, dict] | None]:
    """Jalankan konversi_data.py untuk CSV/TSV, Excel bebas, Trial Balance, atau hitung arus kas otomatis."""
    ext = src.suffix.lower()
    perlu = (
        ext in (".csv", ".tsv")
        or bool(payload.get("konversi_bebas"))
        or bool(payload.get("trial_balance"))
        or bool(payload.get("hitung_arus_kas"))
    )
    if not perlu:
        return src, [], None

    konv_script = ROOT / "tools" / "konversi_data.py"
    if not konv_script.is_file():
        return src, [], (400, {"ok": False, "error": "Skrip konversi_data.py tidak tersedia."})

    out_path = job_dir / ("lk-konversi.json" if jenis == "tahunan" else "paket-konversi.xlsx")
    cmd: list[Any] = [konv_script, src, "--jenis", jenis, "--out", out_path]
    if payload.get("perusahaan"):
        cmd += ["--perusahaan", str(payload["perusahaan"]).strip()]
    if payload.get("satuan"):
        cmd += ["--satuan", str(payload["satuan"]).strip()]
    if payload.get("trial_balance") and (ROOT / "tools" / "trial_balance.py").is_file():
        cmd.append("--trial-balance")
        if payload.get("periode"):
            cmd += ["--periode", str(payload["periode"]).strip()]
    if payload.get("hitung_arus_kas") and (ROOT / "tools" / "trial_balance.py").is_file():
        cmd.append("--hitung-arus-kas")

    proc = _run_script(*cmd)
    if proc.returncode != 0:
        status = 422 if proc.returncode == 2 else 400
        kode = "VALIDASI_GAGAL" if proc.returncode == 2 else "GAGAL_PROSES"
        detail = _pesan_galat(proc)
        if proc.stdout and "Akun belum terpetakan:" in proc.stdout:
            detail = detail + "\n\n" + proc.stdout.strip()
        return src, [], (status, {"ok": False, "kode": kode, "error": detail})
    return out_path, [out_path.name], None


def jalankan_laporan_analisa(store: JobStore, payload: dict) -> tuple[int, dict]:
    """Jalankan alur laporan-analisa (opsional konversi bebas & samarkan terlebih dulu)."""
    job_id, job_dir = store.buat_job()
    src, err = _resolve_input(
        payload,
        job_dir,
        allowed_exts=ALLOWED_DATA_EXTS,
        sample_candidates=("Data-Keuangan-Bulanan.xlsx",),
    )
    if err or src is None:
        shutil.rmtree(job_dir, ignore_errors=True)
        return err  # type: ignore[return-value]

    src, extra_files, conv_err = _konversi_input_jika_perlu(src, job_dir, "bulanan", payload)
    if conv_err:
        shutil.rmtree(job_dir, ignore_errors=True)
        return conv_err

    mode = payload.get("mode", "direksi")
    if mode not in ("direksi", "lengkap"):
        mode = "direksi"
    gaya = payload.get("gaya_cerita", "narasi")
    if gaya not in ("narasi", "checklist"):
        gaya = "narasi"
    samarkan = bool(payload.get("samarkan", False))

    files: list[str] = list(extra_files)
    paket_pakai = src
    if samarkan:
        if src.suffix.lower() not in (".xlsx", ".xlsm"):
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": "Penyamaran paket bulanan hanya mendukung berkas Excel (.xlsx)."}
        samar_path = job_dir / "paket-samaran.xlsx"
        p_samar = _run_script(SK / "laporan-analisa/scripts/samarkan_paket.py", src, "--out", samar_path)
        if p_samar.returncode != 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": _pesan_galat(p_samar)}
        paket_pakai = samar_path
        files.append("paket-samaran.xlsx")

    out_html = job_dir / "laporan.html"
    out_json = job_dir / "laporan.json"
    proc = _run_script(
        SK / "laporan-analisa/scripts/susun_laporan.py",
        paket_pakai,
        "--out",
        out_html,
        "--json",
        out_json,
        "--mode",
        mode,
        "--gaya-cerita",
        gaya,
        "--diam",
    )
    if proc.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        status = 422 if proc.returncode == 2 else 400
        kode = "VALIDASI_GAGAL" if proc.returncode == 2 else "GAGAL_PROSES"
        return status, {"ok": False, "kode": kode, "error": _pesan_galat(proc)}

    files = ["laporan.html", "laporan.json", *files]
    store.daftarkan(job_id, job_dir, files)
    vm = json.loads(out_json.read_text(encoding="utf-8"))
    ringkasan = {
        "meta": vm.get("meta", {}),
        "periode": vm.get("periode", {}).get("month", {}).get("label", ""),
        "skor": vm.get("skor", {}).get("month", {}),
        "putusan": vm.get("putusan", {}).get("month", {}),
        "cerita": vm.get("cerita", []),
        "gerbang": vm.get("gerbang", []),
        "kelengkapan": vm.get("kelengkapan", []),
    }
    return 200, {"ok": True, "job_id": job_id, "files": files, "ringkasan": ringkasan}


def jalankan_analisis_tahunan(store: JobStore, payload: dict) -> tuple[int, dict]:
    """Jalankan alur LK tahunan: Excel/JSON -> (samarkan) -> rasio -> visual -> gejala -> (kesiapan) -> brief."""
    job_id, job_dir = store.buat_job()
    src, err = _resolve_input(
        payload,
        job_dir,
        allowed_exts=ALLOWED_DATA_EXTS,
        sample_candidates=("LK-Tahunan.xlsx", "lk-tahunan.json"),
    )
    if err or src is None:
        shutil.rmtree(job_dir, ignore_errors=True)
        return err  # type: ignore[return-value]

    src, extra_files, conv_err = _konversi_input_jika_perlu(src, job_dir, "tahunan", payload)
    if conv_err:
        shutil.rmtree(job_dir, ignore_errors=True)
        return conv_err

    gaya = payload.get("gaya", "ringkas")
    if gaya not in ("ringkas", "detail", "checklist"):
        gaya = "ringkas"
    metode = payload.get("metode", "akhir")
    if metode not in ("akhir", "rata-rata"):
        metode = "akhir"
    samarkan = bool(payload.get("samarkan", False))
    kesiapan = (payload.get("kesiapan") or "").strip()

    lk_path = job_dir / "lk.json"
    if src.suffix.lower() in (".xlsx", ".xlsm"):
        p_xl = _run_script(SK / "baca-laporan-keuangan/scripts/baca_excel.py", src, "--out", lk_path)
        if p_xl.returncode != 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": _pesan_galat(p_xl)}
    else:
        lk_path.write_bytes(src.read_bytes())

    files: list[str] = list(extra_files)
    if samarkan:
        samar_path = job_dir / "lk-samaran.json"
        p_samar = _run_script(
            SK / "baca-laporan-keuangan/scripts/samarkan_lk.py",
            lk_path,
            "--out",
            samar_path,
            "--samarkan-periode",
        )
        if p_samar.returncode != 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": _pesan_galat(p_samar)}
        lk_path.unlink(missing_ok=True)
        lk_path = samar_path
        files.append("lk-samaran.json")

    rasio_json = job_dir / "rasio.json"
    rasio_md = job_dir / "rasio.md"
    p_rasio = _run_script(
        SK / "baca-laporan-keuangan/scripts/hitung_rasio.py",
        lk_path,
        "--out-json",
        rasio_json,
        "--out-md",
        rasio_md,
        "--gaya",
        gaya,
        "--metode",
        metode,
        "--diam",
    )
    if p_rasio.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        status = 422 if p_rasio.returncode == 2 else 400
        kode = "VALIDASI_GAGAL" if p_rasio.returncode == 2 else "GAGAL_PROSES"
        return status, {"ok": False, "kode": kode, "error": _pesan_galat(p_rasio)}

    visual_html = job_dir / "visual.html"
    p_vis = _run_script(SK / "baca-laporan-keuangan/scripts/visualisasi.py", rasio_json, "--out", visual_html)
    if p_vis.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(p_vis)}

    gejala_json = job_dir / "gejala.json"
    gejala_md = job_dir / "gejala.md"
    p_gej = _run_script(
        SK / "red-flag-operasional/scripts/deteksi_gejala.py",
        rasio_json,
        "--out-json",
        gejala_json,
        "--out-md",
        gejala_md,
        "--gaya",
        gaya,
        "--diam",
    )
    if p_gej.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(p_gej)}

    brief_cmd = [
        SK / "board-brief/scripts/susun_brief.py",
        "--rasio",
        rasio_json,
        "--gejala",
        gejala_json,
        "--out-md",
        job_dir / "brief.md",
        "--out-html",
        job_dir / "brief.html",
        "--diam",
    ]
    kesiapan_md_teks = ""
    if kesiapan:
        kes_json = job_dir / "kesiapan.json"
        kes_md = job_dir / "kesiapan.md"
        p_kes = _run_script(
            SK / "cek-kesiapan-data/scripts/skor_kesiapan.py",
            "--jawaban",
            kesiapan,
            "--out-json",
            kes_json,
            "--out-md",
            kes_md,
            "--diam",
        )
        if p_kes.returncode != 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": _pesan_galat(p_kes)}
        brief_cmd += ["--kesiapan", kes_json]
        files += ["kesiapan.json", "kesiapan.md"]
        kesiapan_md_teks = kes_md.read_text(encoding="utf-8")

    p_brief = _run_script(*brief_cmd)
    if p_brief.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(p_brief)}

    files = ["brief.html", "brief.md", "visual.html", "rasio.md", "rasio.json", "gejala.md", "gejala.json", *files]
    zip_path = job_dir / "hasil.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in files:
            zf.write(job_dir / fn, fn)
    files.append("hasil.zip")

    store.daftarkan(job_id, job_dir, files)
    rasio_data = json.loads(rasio_json.read_text(encoding="utf-8"))
    return 200, {
        "ok": True,
        "job_id": job_id,
        "files": files,
        "meta": rasio_data.get("meta", {}),
        "peringatan": rasio_data.get("validasi", {}).get("peringatan", []),
        "brief_md": (job_dir / "brief.md").read_text(encoding="utf-8"),
        "rasio_md": rasio_md.read_text(encoding="utf-8"),
        "gejala_md": gejala_md.read_text(encoding="utf-8"),
        "kesiapan_md": kesiapan_md_teks,
    }


def jalankan_uji_kas(store: JobStore, payload: dict) -> tuple[int, dict]:
    """Jalankan skill uji-ketahanan-kas (stress test kas)."""
    job_id, job_dir = store.buat_job()
    src, err = _resolve_input(
        payload,
        job_dir,
        allowed_exts=ALLOWED_DATA_EXTS,
        sample_candidates=("Data-Keuangan-Bulanan.xlsx",),
    )
    if err or src is None:
        shutil.rmtree(job_dir, ignore_errors=True)
        return err  # type: ignore[return-value]

    src, extra_files, conv_err = _konversi_input_jika_perlu(src, job_dir, "bulanan", payload)
    if conv_err:
        shutil.rmtree(job_dir, ignore_errors=True)
        return conv_err

    files: list[str] = list(extra_files)
    paket_pakai = src
    if bool(payload.get("samarkan", False)):
        if src.suffix.lower() not in (".xlsx", ".xlsm"):
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": "Penyamaran paket bulanan hanya mendukung berkas Excel (.xlsx)."}
        samar_path = job_dir / "paket-samaran.xlsx"
        p_samar = _run_script(SK / "laporan-analisa/scripts/samarkan_paket.py", src, "--out", samar_path)
        if p_samar.returncode != 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": _pesan_galat(p_samar)}
        paket_pakai = samar_path
        files.append("paket-samaran.xlsx")

    out_md = job_dir / "uji-kas.md"
    out_json = job_dir / "uji-kas.json"
    cmd = [
        SK / "uji-ketahanan-kas/scripts/uji_ketahanan_kas.py",
        paket_pakai,
        "--out-md",
        out_md,
        "--out-json",
        out_json,
        "--diam",
    ]
    if payload.get("horizon") not in (None, ""):
        cmd += ["--horizon", str(payload["horizon"])]
    for param, flag in (
        ("plafon", "--plafon"),
        ("batas_dscr", "--batas-dscr"),
        ("batas_icr", "--batas-icr"),
        ("kas_minimum", "--kas-minimum"),
    ):
        val = payload.get(param)
        if val not in (None, ""):
            cmd += [flag, str(val)]

    skenario = payload.get("skenario")
    if isinstance(skenario, list) and skenario:
        sk_path = job_dir / "skenario.json"
        sk_path.write_text(json.dumps({"skenario": skenario}, ensure_ascii=False), encoding="utf-8")
        cmd += ["--skenario", sk_path]

    proc = _run_script(*cmd)
    if proc.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        status = 422 if proc.returncode == 2 else 400
        kode = "VALIDASI_GAGAL" if proc.returncode == 2 else "GAGAL_PROSES"
        return status, {"ok": False, "kode": kode, "error": _pesan_galat(proc)}

    files = ["uji-kas.md", "uji-kas.json", *files]
    store.daftarkan(job_id, job_dir, files)
    return 200, {
        "ok": True,
        "job_id": job_id,
        "files": files,
        "data": json.loads(out_json.read_text(encoding="utf-8")),
        "md": out_md.read_text(encoding="utf-8"),
    }


def _ambil_file_job(store: JobStore, job_id: str | None, fn: str | None) -> Path | None:
    if not job_id or not fn:
        return None
    return store.ambil_file(str(job_id).strip(), str(fn).strip())


def jalankan_ekonomi_daerah(store: JobStore, payload: dict) -> tuple[int, dict]:
    """Jalankan skill kondisi-ekonomi-daerah (World Bank / CSV daerah -> paparan & skenario kas)."""
    ambil_script = SK / "kondisi-ekonomi-daerah/scripts/ambil_makro.py"
    analisa_script = SK / "kondisi-ekonomi-daerah/scripts/analisa_risiko_ekonomi.py"
    if not ambil_script.is_file() or not analisa_script.is_file():
        return 400, {"ok": False, "error": "Skill kondisi-ekonomi-daerah belum tersedia."}

    job_id, job_dir = store.buat_job()
    ek_json = job_dir / "ekonomi.json"
    cmd_ambil: list[Any] = [ambil_script, "--out", ek_json, "--diam"]
    if payload.get("daerah"):
        cmd_ambil += ["--daerah", str(payload["daerah"]).strip()]
    if payload.get("offline"):
        cmd_ambil.append("--offline")
    if payload.get("file_name") and payload.get("file_b64"):
        src, err = _resolve_input(payload, job_dir, allowed_exts=(".csv", ".json"), sample_candidates=())
        if err or src is None:
            shutil.rmtree(job_dir, ignore_errors=True)
            return err  # type: ignore[return-value]
        cmd_ambil += ["--input", src]
    for param, flag in (
        ("pdrb_pct", "--pdrb-pct"),
        ("inflasi_daerah_pct", "--inflasi-daerah-pct"),
        ("kenaikan_ump_pct", "--kenaikan-ump-pct"),
        ("suku_bunga_pct", "--suku-bunga-pct"),
        ("kurs_usd", "--kurs-usd"),
        ("catatan_daerah", "--catatan-daerah"),
    ):
        val = payload.get(param)
        if val not in (None, ""):
            cmd_ambil += [flag, str(val)]

    p1 = _run_script(*cmd_ambil)
    if p1.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(p1)}

    out_md = job_dir / "risiko-ekonomi.md"
    out_json = job_dir / "risiko-ekonomi.json"
    out_sken = job_dir / "skenario-makro.json"
    cmd_ana: list[Any] = [analisa_script, ek_json, "--out-md", out_md, "--out-json", out_json, "--out-skenario", out_sken, "--diam"]
    rasio_path = _ambil_file_job(store, payload.get("rasio_job_id"), payload.get("rasio_file"))
    if rasio_path:
        cmd_ana += ["--rasio", rasio_path]
    gaya = payload.get("gaya")
    if gaya in ("ringkas", "detail", "checklist"):
        cmd_ana += ["--gaya", gaya]

    p2 = _run_script(*cmd_ana)
    if p2.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(p2)}

    files = ["ekonomi.json", "risiko-ekonomi.md", "risiko-ekonomi.json", "skenario-makro.json"]
    store.daftarkan(job_id, job_dir, files)
    return 200, {
        "ok": True,
        "job_id": job_id,
        "files": files,
        "data": json.loads(out_json.read_text(encoding="utf-8")),
        "skenario": json.loads(out_sken.read_text(encoding="utf-8")),
        "md": out_md.read_text(encoding="utf-8"),
    }


def _run_node(*args) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    if not node:
        return subprocess.CompletedProcess(args, 1, "", "Node.js (>= 20) belum terpasang di sistem.")
    return subprocess.run(
        [node, *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(SK / "data-emiten/scripts"),
    )


def jalankan_emiten(store: JobStore, payload: dict) -> tuple[int, dict]:
    """Cari atau bandingkan emiten IDX via data-emiten (TradingView)."""
    tv_script = SK / "data-emiten/scripts/tv_emiten.mjs"
    ringkas_script = SK / "data-emiten/scripts/ringkas_emiten.py"
    action = (payload.get("action") or "bandingkan").strip()

    job_id, job_dir = store.buat_job()
    if action == "daftar":
        out_daftar = job_dir / "daftar-emiten.json"
        cmd: list[Any] = [tv_script, "daftar", "--limit", str(payload.get("limit") or 15), "--json", out_daftar]
        if payload.get("cari"):
            cmd += ["--cari", str(payload["cari"]).strip()]
        if payload.get("sektor"):
            cmd += ["--sektor", str(payload["sektor"]).strip()]
        proc = _run_node(*cmd)
        if proc.returncode != 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": _pesan_galat(proc)}
        rows = json.loads(out_daftar.read_text(encoding="utf-8"))[: int(payload.get("limit") or 15)]
        shutil.rmtree(job_dir, ignore_errors=True)
        return 200, {"ok": True, "daftar": rows}

    em_json = job_dir / "emiten.json"
    if payload.get("file_name") and payload.get("file_b64"):
        src, err = _resolve_input(payload, job_dir, allowed_exts=(".json",), sample_candidates=())
        if err or src is None:
            shutil.rmtree(job_dir, ignore_errors=True)
            return err  # type: ignore[return-value]
        em_json.write_bytes(src.read_bytes())
    else:
        kodes = [k.strip().upper() for k in str(payload.get("kode") or "").replace(",", " ").split() if k.strip()]
        if not kodes:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": "Masukkan kode emiten (mis. UNVR ICBP MYOR) atau unggah emiten.json."}
        p_tv = _run_node(tv_script, "ambil", *kodes[:15], "--out", em_json)
        if p_tv.returncode != 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            return 400, {"ok": False, "error": _pesan_galat(p_tv)}

    out_md = job_dir / "pembanding.md"
    out_json = job_dir / "pembanding.json"
    cmd_r: list[Any] = [ringkas_script, em_json, "--out-md", out_md, "--out-json", out_json, "--diam"]
    rasio_path = _ambil_file_job(store, payload.get("rasio_job_id"), payload.get("rasio_file"))
    if rasio_path:
        cmd_r += ["--rasio", rasio_path]
    if payload.get("gaya") in ("ringkas", "detail", "checklist"):
        cmd_r += ["--gaya", payload["gaya"]]
    p_r = _run_script(*cmd_r)
    if p_r.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(p_r)}

    files = ["emiten.json", "pembanding.md", "pembanding.json"]
    store.daftarkan(job_id, job_dir, files)
    return 200, {
        "ok": True,
        "job_id": job_id,
        "files": files,
        "data": json.loads(out_json.read_text(encoding="utf-8")),
        "md": out_md.read_text(encoding="utf-8"),
    }


def jalankan_sdm_budget(store: JobStore, payload: dict) -> tuple[int, dict]:
    """Jalankan skill efisiensi-sdm-departemen (Rp per karyawan & KPI budgeting)."""
    sdm_script = SK / "efisiensi-sdm-departemen/scripts/analisa_sdm_budget.py"
    if not sdm_script.is_file():
        return 400, {"ok": False, "error": "Skill efisiensi-sdm-departemen belum tersedia di repo ini."}

    job_id, job_dir = store.buat_job()
    rasio_path = _ambil_file_job(store, payload.get("rasio_job_id"), payload.get("rasio_file"))
    if not rasio_path:
        sample_case = (payload.get("sample_case") or "").strip()
        if sample_case:
            src = SAMPLE / sample_case / "lk-tahunan.json"
            if src.is_file():
                rasio_path = job_dir / "rasio-sample.json"
                p_ras = _run_script(SK / "baca-laporan-keuangan/scripts/hitung_rasio.py", src, "--out-json", rasio_path, "--diam")
                if p_ras.returncode != 0:
                    shutil.rmtree(job_dir, ignore_errors=True)
                    return 400, {"ok": False, "error": _pesan_galat(p_ras)}
    if not rasio_path:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": "Jalankan Tab 1 (Bulanan) atau Tab 2 (Tahunan) terlebih dahulu, atau pilih Data Contoh."}

    out_md = job_dir / "sdm-budget.md"
    out_json = job_dir / "sdm-budget.json"
    cmd: list[Any] = [sdm_script, "--rasio", rasio_path, "--out-md", out_md, "--out-json", out_json, "--diam"]
    if payload.get("file_name") and payload.get("file_b64"):
        src_sdm, err = _resolve_input(payload, job_dir, allowed_exts=(".csv", ".json"), sample_candidates=())
        if err or src_sdm is None:
            shutil.rmtree(job_dir, ignore_errors=True)
            return err  # type: ignore[return-value]
        cmd += ["--input", src_sdm]
    else:
        if payload.get("karyawan") not in (None, ""):
            cmd += ["--karyawan", str(payload["karyawan"])]
        if payload.get("karyawan_lalu") not in (None, ""):
            cmd += ["--karyawan-lalu", str(payload["karyawan_lalu"])]
        dept = payload.get("departemen")
        if dept:
            if isinstance(dept, list):
                teks_dept = ",".join(
                    f"{d.get('nama', '').strip()}:{d.get('karyawan', 0)}"
                    for d in dept
                    if isinstance(d, dict) and d.get("nama")
                )
            else:
                teks_dept = str(dept).strip()
            if teks_dept:
                cmd += ["--departemen", teks_dept]
    if payload.get("gaya") in ("ringkas", "detail", "checklist"):
        cmd += ["--gaya", payload["gaya"]]

    proc = _run_script(*cmd)
    if proc.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(proc)}

    files = ["sdm-budget.md", "sdm-budget.json"]
    store.daftarkan(job_id, job_dir, files)
    return 200, {
        "ok": True,
        "job_id": job_id,
        "files": files,
        "data": json.loads(out_json.read_text(encoding="utf-8")),
        "md": out_md.read_text(encoding="utf-8"),
    }


def jalankan_report_kombinasi(store: JobStore, payload: dict) -> tuple[int, dict]:
    """Susun report kombinasi HTML/PDF + Markdown dari hasil modul yang aktif di sesi."""
    komb_script = ROOT / "tools/susun_report_kombinasi.py"
    if not komb_script.is_file():
        return 400, {"ok": False, "error": "Skrip susun_report_kombinasi.py belum tersedia di repo ini."}

    job_id, job_dir = store.buat_job()
    out_html = job_dir / "report-kombinasi.html"
    out_md = job_dir / "report-kombinasi.md"
    cmd: list[Any] = [komb_script, "--out", out_html, "--out-md", out_md, "--diam"]
    if payload.get("judul"):
        cmd += ["--judul", str(payload["judul"]).strip()]
    if payload.get("catatan"):
        cmd += ["--catatan", str(payload["catatan"]).strip()]

    sumber = payload.get("sumber") or {}
    ada_basis = False
    for key, flag in (
        ("rasio", "--rasio"),
        ("laporan", "--laporan"),
        ("gejala", "--gejala"),
        ("kesiapan", "--kesiapan"),
        ("emiten", "--emiten"),
        ("ekonomi", "--ekonomi"),
        ("sdm", "--sdm"),
        ("uji_kas", "--uji-kas"),
    ):
        ref = sumber.get(key)
        if isinstance(ref, dict):
            p = _ambil_file_job(store, ref.get("job_id"), ref.get("file"))
            if p:
                cmd += [flag, p]
                if key in ("rasio", "laporan"):
                    ada_basis = True
    if not ada_basis:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": "Jalankan minimal Tab 1 (Bulanan) atau Tab 2 (Tahunan) sebelum menyusun Report Kombinasi."}

    proc = _run_script(*cmd)
    if proc.returncode != 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return 400, {"ok": False, "error": _pesan_galat(proc)}

    files = ["report-kombinasi.html", "report-kombinasi.md"]
    store.daftarkan(job_id, job_dir, files)
    return 200, {
        "ok": True,
        "job_id": job_id,
        "files": files,
        "md": out_md.read_text(encoding="utf-8"),
    }


def buat_handler(store: JobStore):
    """Bangun kelas handler HTTP dengan akses ke JobStore."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "CorporateHealthCheckPortal/1.0"

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def _kirim_bytes(self, status: int, content_type: str, data: bytes, download_name: str | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            if download_name:
                self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
            self.end_headers()
            self.wfile.write(data)

        def _kirim_json(self, status: int, obj: dict) -> None:
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self._kirim_bytes(status, "application/json; charset=utf-8", raw)

        def _baca_json_body(self) -> dict | None:
            try:
                panjang = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._kirim_json(400, {"ok": False, "error": "Header Content-Length tidak valid."})
                return None
            if panjang <= 0 or panjang > MAX_UPLOAD_BYTES * 2:
                self._kirim_json(400, {"ok": False, "error": "Ukuran permintaan tidak valid atau terlalu besar."})
                return None
            raw = self.rfile.read(panjang)
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._kirim_json(400, {"ok": False, "error": "Payload JSON tidak valid."})
                return None
            if not isinstance(data, dict):
                self._kirim_json(400, {"ok": False, "error": "Payload harus berupa objek JSON."})
                return None
            return data

        def do_GET(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?", 1)[0])
            if path in ("/", "/index.html"):
                self._kirim_bytes(200, "text/html; charset=utf-8", HTML_FILE.read_bytes())
                return
            if path == "/api/info":
                self._kirim_json(200, info_aplikasi())
                return
            if path.startswith("/api/template/"):
                nama = path[len("/api/template/"):]
                p = TEMPLATES.get(nama)
                if p and p.is_file():
                    ctype = (
                        "text/csv; charset=utf-8"
                        if p.suffix.lower() == ".csv"
                        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    self._kirim_bytes(200, ctype, p.read_bytes(), download_name=nama)
                    return
                self._kirim_json(404, {"ok": False, "error": "Template tidak ditemukan."})
                return
            if path.startswith("/api/job/"):
                sisa = path[len("/api/job/"):].split("/", 1)
                if len(sisa) != 2:
                    self._kirim_json(404, {"ok": False, "error": "Berkas tidak ditemukan."})
                    return
                job_id, fn = sisa
                p = store.ambil_file(job_id, fn)
                if not p:
                    self._kirim_json(404, {"ok": False, "error": "Berkas hasil tidak ditemukan atau sudah kedaluwarsa."})
                    return
                ctype, _ = mimetypes.guess_type(p.name)
                if p.suffix == ".html":
                    ctype = "text/html; charset=utf-8"
                elif p.suffix in (".md", ".json"):
                    ctype = "text/plain; charset=utf-8" if p.suffix == ".md" else "application/json; charset=utf-8"
                elif not ctype:
                    ctype = "application/octet-stream"
                dl = None if p.suffix == ".html" else p.name
                self._kirim_bytes(200, ctype, p.read_bytes(), download_name=dl)
                return
            self._kirim_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Endpoint tidak ditemukan."})

        def do_POST(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?", 1)[0])
            payload = self._baca_json_body()
            if payload is None:
                return
            routes = {
                "/api/laporan-analisa": jalankan_laporan_analisa,
                "/api/analisis-tahunan": jalankan_analisis_tahunan,
                "/api/uji-kas": jalankan_uji_kas,
                "/api/ekonomi-daerah": jalankan_ekonomi_daerah,
                "/api/emiten": jalankan_emiten,
                "/api/sdm-budget": jalankan_sdm_budget,
                "/api/report-kombinasi": jalankan_report_kombinasi,
            }
            fn = routes.get(path)
            if not fn:
                self._kirim_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Endpoint tidak ditemukan."})
                return
            status, body = fn(store, payload)
            self._kirim_json(status, body)

    return Handler


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Portal Web Peserta Corporate Health Check")
    ap.add_argument("--host", default="127.0.0.1", help="Alamat bind server (bawaan: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8080, help="Port server (bawaan: 8080)")
    ap.add_argument("--no-browser", action="store_true", help="Jangan buka browser otomatis")
    a = ap.parse_args(argv)

    store = JobStore()
    server = ThreadingHTTPServer((a.host, a.port), buat_handler(store))
    url = f"http://{a.host if a.host != '0.0.0.0' else '127.0.0.1'}:{server.server_address[1]}"
    print(f"Portal Peserta Corporate Health Check berjalan di {url}")
    print("Tekan Ctrl+C untuk berhenti.")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()
        store.tutup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
