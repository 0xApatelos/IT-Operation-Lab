"""Konfigurasi monitor: load + validasi ketat (tanpa dependensi eksternal).

Prinsip:
- Semua nilai divalidasi (tipe, rentang, format). Kesalahan apa pun memicu
  ConfigError -> CLI keluar dengan exit code 2.
- Path relatif (log_file, state_file) di-resolve terhadap direktori file
  konfigurasi agar perilaku sama dijalankan dari folder mana pun.
- bool ditolak untuk field angka (bool adalah subclass int di Python).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Konfigurasi tidak valid atau tidak dapat dibaca (exit code 2)."""

_UNIT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._-]*$")
_HOST_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_TIMEOUT_MAX_SECONDS = 60.0
_KNOWN_TYPES = ("disk", "service", "dns", "tcp", "http")
_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass(frozen=True)
class DiskCheck:
    type: str
    name: str
    path: str
    warn_pct: int
    crit_pct: int


@dataclass(frozen=True)
class ServiceCheck:
    type: str
    name: str
    unit: str


@dataclass(frozen=True)
class DnsCheck:
    type: str
    name: str
    host: str
    timeout_seconds: float


@dataclass(frozen=True)
class TcpCheck:
    type: str
    name: str
    host: str
    port: int
    timeout_seconds: float


@dataclass(frozen=True)
class HttpCheck:
    type: str
    name: str
    url: str
    timeout_seconds: float


@dataclass(frozen=True)
class OutputConfig:
    log_file: str | None = None
    log_level: str = "INFO"


@dataclass(frozen=True)
class AlertConfig:
    webhook_enabled: bool = False
    webhook_url_env: str = "LAB_WEBHOOK_URL"
    webhook_timeout_seconds: float = 5.0
    retry_max: int = 2
    dedup_seconds: int = 300
    state_file: str | None = None


@dataclass(frozen=True)
class MonitorConfig:
    source_path: str
    checks: tuple[Any, ...]
    output: OutputConfig
    alerts: AlertConfig


# --- helper validasi kecil ---------------------------------------------------


def _require_dict(value: Any, ctx: str) -> dict:
    if not isinstance(value, dict):
        raise ConfigError(f"{ctx}: harus berupa object/dictionary")
    return value


def _require_str(d: dict, key: str, ctx: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ConfigError(f"{ctx}: '{key}' wajib string tidak kosong")
    return v


def _require_num(d: dict, key: str, ctx: str) -> float:
    v = d.get(key)
    # bool adalah subclass int -> tolak eksplisit agar warn_pct: true tidak lolos.
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ConfigError(f"{ctx}: '{key}' wajib angka (dapat: {v!r})")
    return float(v)


def _require_int(d: dict, key: str, ctx: str) -> int:
    v = _require_num(d, key, ctx)
    if v != int(v):
        raise ConfigError(f"{ctx}: '{key}' wajib bilangan bulat (dapat: {v!r})")
    return int(v)


def _require_timeout(d: dict, ctx: str) -> float:
    t = _require_num(d, "timeout_seconds", ctx)
    if not (0 < t <= _TIMEOUT_MAX_SECONDS):
        raise ConfigError(
            f"{ctx}: 'timeout_seconds' harus di rentang (0, {_TIMEOUT_MAX_SECONDS:g}] (dapat: {t!r})"
        )
    return t


def _optional_str(d: dict, key: str, ctx: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str) or not v.strip():
        raise ConfigError(f"{ctx}: '{key}' harus string tidak kosong atau null")
    return v


def _require_bool(d: dict, key: str, ctx: str) -> bool:
    v = d.get(key)
    if not isinstance(v, bool):
        raise ConfigError(f"{ctx}: '{key}' wajib boolean (dapat: {v!r})")
    return v


def _validate_port(v: int, ctx: str) -> int:
    if not (1 <= v <= 65535):
        raise ConfigError(f"{ctx}: port harus 1-65535 (dapat: {v})")
    return v


def _num_or(d: dict, key: str, default: float, lo: float, hi: float, ctx: str) -> float:
    """Nilai angka dengan default bila tidak ada; tetap divalidasi bila ada."""
    if key not in d:
        return float(default)
    v = _require_num(d, key, ctx)
    if not (lo <= v <= hi):
        raise ConfigError(f"{ctx}: '{key}' harus {lo:g}-{hi:g} (dapat: {v!r})")
    return v


def _int_or(d: dict, key: str, default: int, lo: int, hi: int, ctx: str) -> int:
    v = _num_or(d, key, float(default), float(lo), float(hi), ctx)
    if v != int(v):
        raise ConfigError(f"{ctx}: '{key}' wajib bilangan bulat (dapat: {v!r})")
    return int(v)


def _bool_or(d: dict, key: str, default: bool, ctx: str) -> bool:
    if key not in d:
        return default
    return _require_bool(d, key, ctx)


# --- parse per tipe check -----------------------------------------------------


def _parse_check(item: Any, idx: int, seen_names: set[str]) -> Any:
    ctx = f"checks[{idx}]"
    d = _require_dict(item, ctx)
    ctype = d.get("type")
    if ctype not in _KNOWN_TYPES:
        raise ConfigError(
            f"{ctx}: 'type' tidak dikenal: {ctype!r} (didukung: {', '.join(_KNOWN_TYPES)})"
        )
    name = _require_str(d, "name", ctx)
    if name in seen_names:
        raise ConfigError(f"{ctx}: nama check duplikat: '{name}'")
    seen_names.add(name)

    if ctype == "disk":
        path = _require_str(d, "path", ctx)
        warn = _require_int(d, "warn_pct", ctx)
        crit = _require_int(d, "crit_pct", ctx)
        if not (1 <= warn <= 99 and 1 <= crit <= 99):
            raise ConfigError(f"{ctx} ({name}): warn_pct/crit_pct harus 1-99")
        if warn >= crit:
            raise ConfigError(
                f"{ctx} ({name}): warn_pct ({warn}) harus lebih kecil dari crit_pct ({crit})"
            )
        return DiskCheck(type=ctype, name=name, path=path, warn_pct=warn, crit_pct=crit)

    if ctype == "service":
        unit = _require_str(d, "unit", ctx)
        if not _UNIT_RE.match(unit):
            raise ConfigError(
                f"{ctx} ({name}): 'unit' hanya boleh huruf/angka dan @ . _ - (tanpa spasi/slash)"
            )
        return ServiceCheck(type=ctype, name=name, unit=unit)

    if ctype == "dns":
        host = _require_str(d, "host", ctx)
        if not _HOST_RE.match(host):
            raise ConfigError(f"{ctx} ({name}): 'host' tidak valid: {host!r}")
        return DnsCheck(
            type=ctype, name=name, host=host, timeout_seconds=_require_timeout(d, ctx)
        )

    if ctype == "tcp":
        host = _require_str(d, "host", ctx)
        if not _HOST_RE.match(host):
            raise ConfigError(f"{ctx} ({name}): 'host' tidak valid: {host!r}")
        port = _validate_port(_require_int(d, "port", ctx), ctx)
        return TcpCheck(
            type=ctype, name=name, host=host, port=port, timeout_seconds=_require_timeout(d, ctx)
        )

    # ctype == "http"
    url = _require_str(d, "url", ctx)
    if not url.startswith(("http://", "https://")):
        raise ConfigError(f"{ctx} ({name}): 'url' harus diawali http:// atau https://")
    return HttpCheck(type=ctype, name=name, url=url, timeout_seconds=_require_timeout(d, ctx))


def _parse_output(d: Any, base_dir: Path) -> OutputConfig:
    ctx = "output"
    d = _require_dict(d, ctx)
    log_file = _optional_str(d, "log_file", ctx)
    if log_file and not Path(log_file).is_absolute():
        log_file = str((base_dir / log_file).resolve())
    level = d.get("log_level", "INFO")
    if level not in _LOG_LEVELS:
        raise ConfigError(
            f"{ctx}: 'log_level' harus salah satu dari {', '.join(_LOG_LEVELS)} (dapat: {level!r})"
        )
    return OutputConfig(log_file=log_file, log_level=level)


def _parse_alerts(d: Any, base_dir: Path) -> AlertConfig:
    ctx = "alerts"
    d = _require_dict(d, ctx)
    state_file = _optional_str(d, "state_file", ctx)
    if state_file and not Path(state_file).is_absolute():
        state_file = str((base_dir / state_file).resolve())
    env_name = d.get("webhook_url_env", "LAB_WEBHOOK_URL")
    if not isinstance(env_name, str) or not env_name.strip():
        raise ConfigError(f"{ctx}: 'webhook_url_env' wajib string tidak kosong")
    return AlertConfig(
        webhook_enabled=_bool_or(d, "webhook_enabled", False, ctx),
        webhook_url_env=env_name,
        webhook_timeout_seconds=_num_or(d, "webhook_timeout_seconds", 5.0, 1, 60, ctx),
        retry_max=_int_or(d, "retry_max", 2, 0, 5, ctx),
        dedup_seconds=_int_or(d, "dedup_seconds", 300, 0, 86400, ctx),
        state_file=state_file,
    )


def load_config(path: str | Path) -> MonitorConfig:
    """Baca dan validasi file konfigurasi JSON. Memunculkan ConfigError."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise ConfigError(f"file konfigurasi tidak ditemukan: {p}") from e
    except OSError as e:
        raise ConfigError(f"file konfigurasi tidak dapat dibaca: {p} ({e})") from e
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        raise ConfigError(f"konfigurasi bukan JSON valid: {p} ({e})") from e

    root = _require_dict(raw, "root")
    checks_raw = root.get("checks")
    if not isinstance(checks_raw, list) or not checks_raw:
        raise ConfigError("'checks' wajib berupa list dengan minimal satu check")

    seen: set[str] = set()
    checks = tuple(_parse_check(item, i, seen) for i, item in enumerate(checks_raw))

    base_dir = p.resolve().parent
    output = _parse_output(root.get("output", {}), base_dir)
    alerts = _parse_alerts(root.get("alerts", {}), base_dir)
    return MonitorConfig(source_path=str(p), checks=checks, output=output, alerts=alerts)
