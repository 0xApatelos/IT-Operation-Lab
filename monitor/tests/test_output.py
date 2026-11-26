"""Unit test output: skema JSON (timestamp timezone) & ringkasan teks."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from monitor_lab.models import STATUS_FAIL, STATUS_OK, STATUS_UNSUPPORTED, CheckResult, Report
from monitor_lab.output import render_json, render_text


def make_report() -> Report:
    return Report(
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        host="test-host",
        monitor_version="test",
        results=[
            CheckResult("disk-root", "disk", "/", STATUS_OK, 5, "/: 10.0% used"),
            CheckResult("svc", "service", "demo-http", STATUS_FAIL, 7, "demo-http: status=failed"),
            CheckResult("svc2", "service", "other", STATUS_UNSUPPORTED, 0, "unsupported"),
        ],
        duration_ms=12,
    )


def test_json_schema_fields():
    data = json.loads(render_json(make_report()))
    for key in (
        "monitor_version",
        "started_at",
        "host",
        "duration_ms",
        "overall",
        "exit_code",
        "counts",
        "results",
    ):
        assert key in data
    assert data["overall"] == "unhealthy"
    assert data["exit_code"] == 1
    assert data["counts"]["ok"] == 1
    assert data["counts"]["fail"] == 1
    assert data["counts"]["unsupported"] == 1
    result = data["results"][0]
    assert {"name", "check_type", "target", "status", "duration_ms", "detail"} == set(result.keys())


def test_json_timestamp_has_timezone():
    data = json.loads(render_json(make_report()))
    parsed = datetime.fromisoformat(data["started_at"])
    assert parsed.tzinfo is not None  # timestamp dengan timezone (wajib)


def test_healthy_report_exit_zero():
    report = make_report()
    report.results = [r for r in report.results if r.status != STATUS_FAIL]
    data = json.loads(render_json(report))
    assert data["overall"] == "healthy"
    assert data["exit_code"] == 0


def test_text_contains_summary_and_statuses():
    text = render_text(make_report())
    assert "OK" in text and "FAIL" in text and "UNSUPPORTED" in text
    assert "ringkasan:" in text
    assert "unhealthy" in text
    assert "exit=1" in text
