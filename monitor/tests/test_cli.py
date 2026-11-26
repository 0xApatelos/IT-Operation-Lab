"""Unit test CLI: exit code, format JSON, --json-out, konfigurasi tidak valid."""

from __future__ import annotations

import json
from datetime import datetime

from monitor_lab import cli as cli_mod
from tests.fakes import FakeDisk, FakeSystemd


def write_cfg(tmp_path, raw, name="cfg.json") -> str:
    p = tmp_path / name
    p.write_text(json.dumps(raw), encoding="utf-8")
    return str(p)


def run_cli(tmp_path, raw, *extra) -> int:
    cfg_path = write_cfg(tmp_path, raw)
    return cli_mod.main(["--config", cfg_path, *extra])


HEALTHY_CHECKS = [
    {"type": "disk", "name": "disk-root", "path": "/", "warn_pct": 80, "crit_pct": 90},
    {"type": "service", "name": "svc", "unit": "demo-http"},
    {"type": "tcp", "name": "tcp1", "host": "127.0.0.1", "port": 8080, "timeout_seconds": 1},
    {"type": "http", "name": "http1", "url": "http://127.0.0.1/health", "timeout_seconds": 1},
]


def test_exit_0_when_healthy(tmp_path, install_adapters, capsys):
    install_adapters()
    rc = run_cli(tmp_path, {"checks": HEALTHY_CHECKS})
    assert rc == 0
    out = capsys.readouterr().out
    assert "ringkasan:" in out and "healthy" in out


def test_exit_1_when_check_fails(tmp_path, install_adapters):
    install_adapters(systemd=FakeSystemd(states={"demo-http": "inactive"}))
    assert run_cli(tmp_path, {"checks": HEALTHY_CHECKS}) == 1


def test_multiple_failures_still_exit_1(tmp_path, install_adapters):
    # Beberapa check gagal sekaligus -> tetap exit 1 (bukan 2; prioritas 2 hanya
    # untuk kesalahan konfigurasi/eksekusi CLI).
    install_adapters(disk=FakeDisk(error=OSError("x")), systemd=FakeSystemd(states={}))
    assert run_cli(tmp_path, {"checks": HEALTHY_CHECKS}) == 1


def test_exit_0_with_unsupported_check_only(tmp_path, install_adapters):
    install_adapters(systemd=FakeSystemd(supported=False, states={}))
    rc = run_cli(tmp_path, {"checks": [{"type": "service", "name": "svc", "unit": "demo-http"}]})
    assert rc == 0


def test_exit_0_with_warn_only(tmp_path, install_adapters):
    install_adapters(disk=FakeDisk(total=1000, used=600, free=400))
    rc = run_cli(
        tmp_path,
        {"checks": [{"type": "disk", "name": "d", "path": "/", "warn_pct": 50, "crit_pct": 90}]},
    )
    assert rc == 0


def test_exit_2_on_invalid_config(tmp_path):
    raw = {"checks": [{"type": "disk", "name": "d", "path": "/", "warn_pct": 90, "crit_pct": 80}]}
    assert run_cli(tmp_path, raw) == 2


def test_exit_2_on_missing_config(tmp_path):
    assert cli_mod.main(["--config", str(tmp_path / "hilang.json")]) == 2


def test_json_format_schema(tmp_path, install_adapters, capsys):
    install_adapters()
    rc = run_cli(tmp_path, {"checks": HEALTHY_CHECKS}, "--format", "json")
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["exit_code"] == 0
    assert datetime.fromisoformat(data["started_at"]).tzinfo is not None
    assert len(data["results"]) == len(HEALTHY_CHECKS)
    for r in data["results"]:
        assert {"name", "check_type", "target", "status", "duration_ms", "detail"} == set(r)


def test_json_out_written(tmp_path, install_adapters):
    install_adapters()
    out_path = tmp_path / "report.json"
    rc = run_cli(
        tmp_path,
        {"checks": HEALTHY_CHECKS, "output": {"log_level": "WARNING"}},
        "--json-out",
        str(out_path),
    )
    assert rc == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["overall"] == "healthy"


def test_invalid_json_out_does_not_mask_health(tmp_path, install_adapters):
    install_adapters()
    # --json-out menunjuk path yang tidak mungkin dibuat -> warning saja,
    # exit code tetap berasal dari hasil health check (tidak jadi exit 2).
    rc = run_cli(
        tmp_path,
        {"checks": HEALTHY_CHECKS, "output": {"log_level": "ERROR"}},
        "--json-out",
        "/proc/tidak/bisa/report.json",
    )
    assert rc == 0
