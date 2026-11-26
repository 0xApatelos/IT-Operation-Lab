"""Integration test lokal (OPT-IN): pytest -m integration

Butuh lingkungan nyata: unit demo-http ter-install dan aktif di mesin ini
(lihat lab/scripts/install_demo_service.sh). Tidak dijalankan oleh CI.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from monitor_lab import cli as cli_mod

pytestmark = pytest.mark.integration


def _demo_http_ready() -> bool:
    if shutil.which("systemctl") is None:
        return False
    r = subprocess.run(
        ["systemctl", "cat", "demo-http.service"], capture_output=True, text=True, check=False
    )
    if r.returncode != 0:
        return False
    s = subprocess.run(
        ["systemctl", "is-active", "demo-http"], capture_output=True, text=True, check=False
    )
    return s.stdout.strip() == "active"


def test_monitor_against_local_lab(tmp_path):
    if not _demo_http_ready():
        pytest.skip("demo-http belum ter-install/aktif di lingkungan ini")
    cfg = {
        "checks": [
            {"type": "disk", "name": "disk-root", "path": "/", "warn_pct": 80, "crit_pct": 90},
            {"type": "service", "name": "service-demo-http", "unit": "demo-http"},
            {"type": "tcp", "name": "tcp-demo", "host": "127.0.0.1", "port": 8080, "timeout_seconds": 3},
            {
                "type": "http",
                "name": "http-demo",
                "url": "http://127.0.0.1:8080/health",
                "timeout_seconds": 5,
            },
        ],
        "output": {"log_level": "WARNING"},
    }
    cfg_path = tmp_path / "integration.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    rc = cli_mod.main(["--config", str(cfg_path), "--format", "json"])
    assert rc == 0
    # stdout sudah dicetak oleh cli; validasi exit code cukup untuk integration ini.
