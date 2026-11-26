"""Unit test 5 check + helper timeout (semua pakai fake adapters)."""

from __future__ import annotations

import socket
import time
import urllib.error

import pytest

from monitor_lab.adapters import CheckTimeout, run_with_timeout
from monitor_lab.checks import check_disk, check_dns, check_http, check_service, check_tcp
from monitor_lab.config import DiskCheck, DnsCheck, HttpCheck, ServiceCheck, TcpCheck
from monitor_lab.models import (
    STATUS_FAIL,
    STATUS_OK,
    STATUS_UNSUPPORTED,
    STATUS_WARN,
)
from tests.fakes import FakeDisk, FakeDns, FakeHttp, FakeSystemd, FakeTcp

# --- run_with_timeout ---------------------------------------------------------


def test_run_with_timeout_returns_value():
    assert run_with_timeout(lambda a, b: a + b, 2, 1, 2) == 3


def test_run_with_timeout_raises_on_slow():
    def slow():
        time.sleep(1.0)

    with pytest.raises(CheckTimeout):
        run_with_timeout(slow, 0.1)


def test_run_with_timeout_propagates_exception():
    def boom():
        raise ValueError("meledak")

    with pytest.raises(ValueError, match="meledak"):
        run_with_timeout(boom, 1)


# --- disk ----------------------------------------------------------------------


def test_disk_ok():
    c = DiskCheck(type="disk", name="d", path="/", warn_pct=80, crit_pct=90)
    r = check_disk(c, FakeAdaptersDisk(FakeDisk(total=1000, used=100)))
    assert r.status == STATUS_OK


def test_disk_warn():
    c = DiskCheck(type="disk", name="d", path="/", warn_pct=50, crit_pct=90)
    r = check_disk(c, FakeAdaptersDisk(FakeDisk(total=1000, used=600)))
    assert r.status == STATUS_WARN


def test_disk_over_threshold():
    c = DiskCheck(type="disk", name="d", path="/", warn_pct=50, crit_pct=90)
    r = check_disk(c, FakeAdaptersDisk(FakeDisk(total=1000, used=950)))
    assert r.status == STATUS_FAIL
    assert "95.0%" in r.detail


def test_disk_unreadable_is_fail():
    c = DiskCheck(type="disk", name="d", path="/x", warn_pct=50, crit_pct=90)
    r = check_disk(c, FakeAdaptersDisk(FakeDisk(error=OSError("path tidak ada"))))
    assert r.status == STATUS_FAIL


class FakeAdaptersDisk:
    """Wrapper tipis karena check_disk hanya butuh ad.disk."""

    def __init__(self, disk):
        self.disk = disk


class FakeAdaptersService:
    def __init__(self, systemd):
        self.systemd = systemd


class FakeAdaptersDns:
    def __init__(self, dns):
        self.dns = dns


class FakeAdaptersTcp:
    def __init__(self, tcp):
        self.tcp = tcp


class FakeAdaptersHttp:
    def __init__(self, http):
        self.http = http


# --- service --------------------------------------------------------------------


def test_service_active_ok():
    c = ServiceCheck(type="service", name="s", unit="demo-http")
    r = check_service(c, FakeAdaptersService(FakeSystemd(states={"demo-http": "active"})))
    assert r.status == STATUS_OK


def test_service_inactive_fails():
    c = ServiceCheck(type="service", name="s", unit="demo-http")
    r = check_service(c, FakeAdaptersService(FakeSystemd(states={"demo-http": "inactive"})))
    assert r.status == STATUS_FAIL
    assert "inactive" in r.detail


def test_service_failed_fails():
    c = ServiceCheck(type="service", name="s", unit="demo-http")
    r = check_service(c, FakeAdaptersService(FakeSystemd(states={"demo-http": "failed"})))
    assert r.status == STATUS_FAIL


def test_service_missing_unit_fails():
    c = ServiceCheck(type="service", name="s", unit="nope")
    r = check_service(c, FakeAdaptersService(FakeSystemd(states={})))
    assert r.status == STATUS_FAIL
    assert "tidak ditemukan" in r.detail


def test_service_unsupported_platform():
    c = ServiceCheck(type="service", name="s", unit="demo-http")
    r = check_service(c, FakeAdaptersService(FakeSystemd(supported=False)))
    assert r.status == STATUS_UNSUPPORTED


# --- dns --------------------------------------------------------------------------


def test_dns_ok():
    c = DnsCheck(type="dns", name="n", host="ok.test", timeout_seconds=2)
    r = check_dns(c, FakeAdaptersDns(FakeDns(mapping={"ok.test": ["9.9.9.9", "1.1.1.1"]})))
    assert r.status == STATUS_OK


def test_dns_fail():
    c = DnsCheck(type="dns", name="n", host="missing.test", timeout_seconds=2)
    r = check_dns(c, FakeAdaptersDns(FakeDns(mapping={})))
    assert r.status == STATUS_FAIL
    assert "resolusi gagal" in r.detail


def test_dns_timeout():
    c = DnsCheck(type="dns", name="n", host="slow.test", timeout_seconds=0.2)
    r = check_dns(c, FakeAdaptersDns(FakeDns(mapping={"slow.test": ["1.1.1.1"]}, delay=1.0)))
    assert r.status == STATUS_FAIL
    assert "timeout" in r.detail


# --- tcp ----------------------------------------------------------------------------


def test_tcp_ok():
    c = TcpCheck(type="tcp", name="t", host="127.0.0.1", port=8080, timeout_seconds=1)
    r = check_tcp(c, FakeAdaptersTcp(FakeTcp()))
    assert r.status == STATUS_OK


def test_tcp_refused():
    c = TcpCheck(type="tcp", name="t", host="127.0.0.1", port=9999, timeout_seconds=1)
    r = check_tcp(c, FakeAdaptersTcp(FakeTcp(error=ConnectionRefusedError())))
    assert r.status == STATUS_FAIL
    assert "refused" in r.detail


def test_tcp_timeout():
    c = TcpCheck(type="tcp", name="t", host="10.255.255.1", port=9, timeout_seconds=1)
    r = check_tcp(c, FakeAdaptersTcp(FakeTcp(error=TimeoutError())))
    assert r.status == STATUS_FAIL
    assert "timeout" in r.detail


# --- http -----------------------------------------------------------------------------


def test_http_2xx_ok():
    c = HttpCheck(type="http", name="h", url="http://127.0.0.1/health", timeout_seconds=1)
    r = check_http(c, FakeAdaptersHttp(FakeHttp(code=200)))
    assert r.status == STATUS_OK


def test_http_non_2xx():
    c = HttpCheck(type="http", name="h", url="http://127.0.0.1/broken", timeout_seconds=1)
    err = urllib.error.HTTPError(
        url=c.url, code=500, msg="Internal Server Error", hdrs=None, fp=None
    )
    r = check_http(c, FakeAdaptersHttp(FakeHttp(error=err)))
    assert r.status == STATUS_FAIL
    assert "500" in r.detail


def test_http_refused():
    c = HttpCheck(type="http", name="h", url="http://127.0.0.1:9/health", timeout_seconds=1)
    err = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
    r = check_http(c, FakeAdaptersHttp(FakeHttp(error=err)))
    assert r.status == STATUS_FAIL
    assert "refused" in r.detail


def test_http_timeout():
    c = HttpCheck(type="http", name="h", url="http://slow.invalid/health", timeout_seconds=1)
    err = urllib.error.URLError(TimeoutError("timed out"))
    r = check_http(c, FakeAdaptersHttp(FakeHttp(error=err)))
    assert r.status == STATUS_FAIL
    assert "timeout" in r.detail


def test_http_unknown_host():
    c = HttpCheck(type="http", name="h", url="http://missing.invalid/", timeout_seconds=1)
    err = urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))
    r = check_http(c, FakeAdaptersHttp(FakeHttp(error=err)))
    assert r.status == STATUS_FAIL
    assert "tidak dapat diselesaikan" in r.detail
