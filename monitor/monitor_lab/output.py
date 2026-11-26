"""Output laporan: ringkasan teks manusiawi + JSON terstruktur."""

from __future__ import annotations

import json

from .models import Report

_WIDTH_STATUS = 12
_WIDTH_NAME = 26


def render_text(report: Report) -> str:
    counts = report.counts()
    lines = [
        f"monitor {report.monitor_version} @ {report.host} — {report.started_at}",
    ]
    for r in report.results:
        lines.append(f"  {r.status.upper():<{_WIDTH_STATUS}} {r.name:<{_WIDTH_NAME}} {r.detail}")
    lines.append(
        "  ringkasan: "
        + " ".join(f"{k}={v}" for k, v in counts.items())
        + f" | {report.overall()} | exit={report.exit_code()}"
    )
    lines.append(f"  durasi: {report.duration_ms} ms")
    return "\n".join(lines)


def render_json(report: Report) -> str:
    """JSON satu-baris-terformat; timestamp ISO-8601 dengan timezone."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
