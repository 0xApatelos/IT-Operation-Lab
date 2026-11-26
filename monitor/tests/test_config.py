"""Unit test konfigurasi: validasi ketat (semua deterministik, tanpa I/O jaringan)."""

from __future__ import annotations

import json

import pytest

from monitor_lab.config import AlertConfig, ConfigError, load_config


def write_cfg(tmp_path, raw) -> str:
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    return str(p)


VALID_CHECKS = [
    {"type": "disk", "name": "disk-root", "path": "/", "warn_pct": 80, "crit_pct": 90},
    {"type": "service", "name": "svc", "unit": "demo-http"},
    {"type": "dns", "name": "dns1", "host": "example.test", "timeout_seconds": 2},
    {"type": "tcp", "name": "tcp1", "host": "127.0.0.1", "port": 8080, "timeout_seconds": 2},
    {"type": "http", "name": "http1", "url": "http://127.0.0.1/health", "timeout_seconds": 2},
]


def test_valid_config_parses_with_defaults(tmp_path):
    cfg = load_config(write_cfg(tmp_path, {"checks": VALID_CHECKS}))
    assert len(cfg.checks) == 5
    assert cfg.output.log_file is None
    assert cfg.output.log_level == "INFO"
    assert cfg.alerts == AlertConfig()  # semua default, webhook off
    assert cfg.alerts.webhook_enabled is False


def test_relative_paths_resolved_against_config_dir(tmp_path):
    raw = {
        "checks": VALID_CHECKS,
        "output": {"log_file": "runtime/monitor.log"},
        "alerts": {"webhook_enabled": False, "state_file": "runtime/state.json"},
    }
    cfg = load_config(write_cfg(tmp_path, raw))
    assert cfg.output.log_file == str((tmp_path / "runtime" / "monitor.log").resolve())
    assert cfg.alerts.state_file == str((tmp_path / "runtime" / "state.json").resolve())


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="tidak ditemukan"):
        load_config(tmp_path / "tidak-ada.json")


def test_invalid_json(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text("{bukan json", encoding="utf-8")
    with pytest.raises(ConfigError, match="bukan JSON valid"):
        load_config(str(p))


def test_empty_checks_rejected(tmp_path):
    with pytest.raises(ConfigError, match="'checks' wajib"):
        load_config(write_cfg(tmp_path, {"checks": []}))


def test_missing_checks_rejected(tmp_path):
    with pytest.raises(ConfigError, match="'checks' wajib"):
        load_config(write_cfg(tmp_path, {}))


def test_unknown_check_type_rejected(tmp_path):
    raw = {"checks": [{"type": "icmp-ping", "name": "x"}]}
    with pytest.raises(ConfigError, match="tidak dikenal"):
        load_config(write_cfg(tmp_path, raw))


def test_duplicate_names_rejected(tmp_path):
    raw = {"checks": [VALID_CHECKS[0], dict(VALID_CHECKS[0])]}
    with pytest.raises(ConfigError, match="duplikat"):
        load_config(write_cfg(tmp_path, raw))


def test_disk_warn_ge_crit_rejected(tmp_path):
    raw = {"checks": [{"type": "disk", "name": "d", "path": "/", "warn_pct": 90, "crit_pct": 90}]}
    with pytest.raises(ConfigError, match="lebih kecil"):
        load_config(write_cfg(tmp_path, raw))


def test_bool_rejected_as_number(tmp_path):
    raw = {"checks": [{"type": "disk", "name": "d", "path": "/", "warn_pct": True, "crit_pct": 90}]}
    with pytest.raises(ConfigError, match="wajib angka"):
        load_config(write_cfg(tmp_path, raw))


def test_port_out_of_range_rejected(tmp_path):
    raw = {"checks": [{"type": "tcp", "name": "t", "host": "127.0.0.1", "port": 0, "timeout_seconds": 1}]}
    with pytest.raises(ConfigError, match="port"):
        load_config(write_cfg(tmp_path, raw))


def test_unit_with_space_rejected(tmp_path):
    raw = {"checks": [{"type": "service", "name": "s", "unit": "demo http; rm -rf /"}]}
    with pytest.raises(ConfigError, match="'unit'"):
        load_config(write_cfg(tmp_path, raw))


def test_url_without_scheme_rejected(tmp_path):
    raw = {"checks": [{"type": "http", "name": "h", "url": "127.0.0.1/health", "timeout_seconds": 1}]}
    with pytest.raises(ConfigError, match="http"):
        load_config(write_cfg(tmp_path, raw))


def test_timeout_out_of_range_rejected(tmp_path):
    raw = {"checks": [{"type": "dns", "name": "n", "host": "x.test", "timeout_seconds": 61}]}
    with pytest.raises(ConfigError, match="timeout_seconds"):
        load_config(write_cfg(tmp_path, raw))


def test_bad_log_level_rejected(tmp_path):
    raw = {"checks": VALID_CHECKS, "output": {"log_level": "VERBOSE"}}
    with pytest.raises(ConfigError, match="log_level"):
        load_config(write_cfg(tmp_path, raw))
