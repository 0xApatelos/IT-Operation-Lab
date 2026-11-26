"""Logika 5 check wajib. Fungsi murni terhadap adapters (dapat difake).

Pemetaan exception -> status:
  - kondisi terduga (refused, timeout, non-2xx, gaierror, OSError) -> fail
  - exception tak terduga -> unknown (tetap membuat laporan unhealthy)
  - platform tidak mendukung (mis. tanpa systemd) -> unsupported (tidak fail)
"""

from __future__ import annotations

import socket
import time
import urllib.error

from .adapters import Adapters, CheckTimeout, run_with_timeout
from .config import DiskCheck, DnsCheck, HttpCheck, ServiceCheck, TcpCheck
from .models import (
    STATUS_FAIL,
    STATUS_OK,
    STATUS_UNKNOWN,
    STATUS_UNSUPPORTED,
    STATUS_WARN,
    CheckResult,
)


def _result(check, target: str, status: str, detail: str, started: float) -> CheckResult:
    duration_ms = int((time.perf_counter() - started) * 1000)
    return CheckResult(
        name=check.name,
        check_type=check.type,
        target=target,
        status=status,
        duration_ms=duration_ms,
        detail=detail,
    )


def _format_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def check_disk(c: DiskCheck, ad: Adapters) -> CheckResult:
    started = time.perf_counter()
    try:
        total, used, _free = ad.disk.usage(c.path)
        pct = (used / total * 100.0) if total > 0 else 0.0
        if pct >= c.crit_pct:
            status, label = STATUS_FAIL, "fail"
        elif pct >= c.warn_pct:
            status, label = STATUS_WARN, "warn"
        else:
            status, label = STATUS_OK, "ok"
        detail = (
            f"{c.path}: {pct:.1f}% used "
            f"({_format_bytes(used)}/{_format_bytes(total)}), "
            f"thresholds warn {c.warn_pct}% crit {c.crit_pct}% -> {label}"
        )
        return _result(c, c.path, status, detail, started)
    except OSError as e:
        return _result(
            c, c.path, STATUS_FAIL, f"{c.path}: gagal membaca penggunaan disk ({e})", started
        )
    except Exception as e:  # noqa: BLE001
        return _result(
            c, c.path, STATUS_UNKNOWN, f"kesalahan tak terduga: {e.__class__.__name__}: {e}", started
        )


def check_service(c: ServiceCheck, ad: Adapters) -> CheckResult:
    started = time.perf_counter()
    if not ad.systemd.is_supported():
        return _result(
            c,
            c.unit,
            STATUS_UNSUPPORTED,
            "systemd tidak tersedia di platform ini — check dilewati (bukan kegagalan)",
            started,
        )
    try:
        state = ad.systemd.get_state(c.unit)
    except OSError as e:
        return _result(c, c.unit, STATUS_FAIL, f"{c.unit}: gagal memeriksa status ({e})", started)
    except Exception as e:  # noqa: BLE001
        return _result(
            c, c.unit, STATUS_UNKNOWN, f"kesalahan tak terduga: {e.__class__.__name__}: {e}", started
        )
    if state == "active":
        detail = f"{c.unit}: active"
        return _result(c, c.unit, STATUS_OK, detail, started)
    if state == "missing-unit":
        detail = f"{c.unit}: unit tidak ditemukan di sistem ini (belum ter-install?)"
    else:
        detail = f"{c.unit}: status={state} (diharapkan active)"
    return _result(c, c.unit, STATUS_FAIL, detail, started)


def check_dns(c: DnsCheck, ad: Adapters) -> CheckResult:
    started = time.perf_counter()
    try:
        ips = run_with_timeout(ad.dns.resolve, c.timeout_seconds, c.host)
        if not ips:
            return _result(
                c, c.host, STATUS_FAIL, f"{c.host}: resolusi tidak mengembalikan alamat", started
            )
        shown = ", ".join(ips[:3]) + (f" (+{len(ips) - 3} lain)" if len(ips) > 3 else "")
        return _result(c, c.host, STATUS_OK, f"{c.host} -> {shown} ({len(ips)} alamat)", started)
    except CheckTimeout:
        return _result(
            c, c.host, STATUS_FAIL, f"{c.host}: timeout resolusi setelah {c.timeout_seconds:g}s", started
        )
    except socket.gaierror as e:
        return _result(c, c.host, STATUS_FAIL, f"{c.host}: resolusi gagal ({e})", started)
    except OSError as e:
        return _result(c, c.host, STATUS_FAIL, f"{c.host}: gagal ({e.__class__.__name__})", started)
    except Exception as e:  # noqa: BLE001
        return _result(
            c, c.host, STATUS_UNKNOWN, f"kesalahan tak terduga: {e.__class__.__name__}: {e}", started
        )


def check_tcp(c: TcpCheck, ad: Adapters) -> CheckResult:
    started = time.perf_counter()
    target = f"{c.host}:{c.port}"
    try:
        ad.tcp.probe(c.host, c.port, c.timeout_seconds)
        return _result(c, target, STATUS_OK, f"{target} terhubung", started)
    except ConnectionRefusedError:
        return _result(c, target, STATUS_FAIL, f"{target}: connection refused", started)
    except TimeoutError:
        return _result(
            c, target, STATUS_FAIL, f"{target}: timeout setelah {c.timeout_seconds:g}s", started
        )
    except OSError as e:
        return _result(c, target, STATUS_FAIL, f"{target}: gagal ({e.__class__.__name__})", started)
    except Exception as e:  # noqa: BLE001
        return _result(
            c, target, STATUS_UNKNOWN, f"kesalahan tak terduga: {e.__class__.__name__}: {e}", started
        )


def _classify_url_error(reason: Exception) -> str:
    if isinstance(reason, TimeoutError):
        return "timeout"
    if isinstance(reason, ConnectionRefusedError):
        return "connection refused"
    if isinstance(reason, socket.gaierror):
        return "nama host tidak dapat diselesaikan"
    return f"{reason.__class__.__name__}: {reason}"


def check_http(c: HttpCheck, ad: Adapters) -> CheckResult:
    started = time.perf_counter()
    try:
        code = ad.http.get_status(c.url, c.timeout_seconds)
        return _result(c, c.url, STATUS_OK, f"GET {c.url} -> {code}", started)
    except urllib.error.HTTPError as e:
        return _result(c, c.url, STATUS_FAIL, f"GET {c.url} -> {e.code} (non-2xx)", started)
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, Exception):
            detail = _classify_url_error(reason)
        else:
            detail = str(reason)
        return _result(c, c.url, STATUS_FAIL, f"GET {c.url}: {detail}", started)
    except TimeoutError:
        return _result(
            c, c.url, STATUS_FAIL, f"GET {c.url}: timeout setelah {c.timeout_seconds:g}s", started
        )
    except OSError as e:
        return _result(c, c.url, STATUS_FAIL, f"GET {c.url}: gagal ({e.__class__.__name__})", started)
    except Exception as e:  # noqa: BLE001
        return _result(
            c, c.url, STATUS_UNKNOWN, f"kesalahan tak terduga: {e.__class__.__name__}: {e}", started
        )


_RUNNERS = {
    "disk": check_disk,
    "service": check_service,
    "dns": check_dns,
    "tcp": check_tcp,
    "http": check_http,
}


def run_check(cfg, adapters: Adapters) -> CheckResult:
    """Jalankan satu check sesuai tipe konfigurasinya."""
    runner = _RUNNERS.get(cfg.type)
    if runner is None:  # validator config sudah menolak; jaring pengaman saja
        return CheckResult(
            name=cfg.name,
            check_type=cfg.type,
            target="",
            status=STATUS_UNKNOWN,
            duration_ms=0,
            detail="tipe check tidak dikenal",
        )
    return runner(cfg, adapters)
