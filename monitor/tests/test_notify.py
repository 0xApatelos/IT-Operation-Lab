"""Unit test webhook notifier: dedup, kegagalan tidak memengaruhi hasil, env-based URL."""

from __future__ import annotations

import urllib.error

import pytest

from monitor_lab.config import AlertConfig
from monitor_lab.models import STATUS_FAIL, STATUS_OK, CheckResult, Report
from monitor_lab.notify import WebhookNotifier


def make_report(fail=True) -> Report:
    results = [
        CheckResult("svc", "service", "demo-http", STATUS_FAIL if fail else STATUS_OK, 5, "detail"),
    ]
    return Report(
        started_at="2026-01-01T00:00:00+00:00",
        host="test-host",
        monitor_version="test",
        results=results,
        duration_ms=5,
    )


def make_cfg(tmp_path, **overrides) -> AlertConfig:
    defaults = {
        "webhook_enabled": True,
        "webhook_url_env": "TEST_HOOK_URL",
        "webhook_timeout_seconds": 1,
        "retry_max": 0,
        "dedup_seconds": 300,
        "state_file": str(tmp_path / "runtime" / "alert-state.json"),
    }
    defaults.update(overrides)
    return AlertConfig(**defaults)


@pytest.fixture
def hook_url(monkeypatch):
    monkeypatch.setenv("TEST_HOOK_URL", "http://127.0.0.1:1/hook")
    return "http://127.0.0.1:1/hook"


def test_disabled_by_default(tmp_path):
    notifier = WebhookNotifier(AlertConfig())  # webhook_enabled=False
    assert notifier.notify(make_report()) is False


def test_no_send_when_healthy(tmp_path, hook_url):
    notifier = WebhookNotifier(make_cfg(tmp_path))
    assert notifier.notify(make_report(fail=False)) is False


def test_send_and_dedup(tmp_path, hook_url, monkeypatch):
    calls = {"n": 0}

    def fake_post(self, url, data):
        calls["n"] += 1
        return True

    monkeypatch.setattr(WebhookNotifier, "_post", fake_post)
    notifier = WebhookNotifier(make_cfg(tmp_path))

    assert notifier.notify(make_report()) is True
    assert calls["n"] == 1
    # Eksekusi kedua dalam jendela dedup -> tidak mengirim ulang.
    assert notifier.notify(make_report()) is False
    assert calls["n"] == 1
    # State file tercatat.
    assert (tmp_path / "runtime" / "alert-state.json").exists()


def test_send_failure_does_not_raise_or_record(tmp_path, hook_url, monkeypatch, caplog):
    import logging

    def failing_post(self, url, data):
        raise urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))

    monkeypatch.setattr(WebhookNotifier, "_post", failing_post)
    # Isolasi level logger: setup_logging dari test lain bisa mengeset level
    # parent 'monitor_lab' ke ERROR (polusi antar test) — kunci level eksplisit.
    caplog.set_level(logging.WARNING, logger="monitor_lab.notify")
    notifier = WebhookNotifier(make_cfg(tmp_path))

    report = make_report()
    assert notifier.notify(report) is False
    assert report.results[0].status == STATUS_FAIL  # hasil health check utuh
    assert not (tmp_path / "runtime" / "alert-state.json").exists()  # tidak dicatat sebagai sukses
    assert any("tidak terpengaruh" in r.getMessage() for r in caplog.records)


def test_retry_then_success(tmp_path, hook_url, monkeypatch):
    attempts = {"n": 0}

    def flaky_post(self, url, data):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise urllib.error.URLError("sementara gagal")
        return True

    monkeypatch.setattr(WebhookNotifier, "_post", flaky_post)
    monkeypatch.setattr("monitor_lab.notify.time.sleep", lambda _s: None)
    notifier = WebhookNotifier(make_cfg(tmp_path, retry_max=1))
    assert notifier.notify(make_report()) is True
    assert attempts["n"] == 2


def test_missing_env_url_skips(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_HOOK_URL", raising=False)
    notifier = WebhookNotifier(make_cfg(tmp_path))
    assert notifier.notify(make_report()) is False
