"""Model data: hasil check dan laporan (dipakai lintas modul)."""

from __future__ import annotations

from dataclasses import dataclass

STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_UNSUPPORTED = "unsupported"
STATUS_UNKNOWN = "unknown"

# Status yang membuat laporan dianggap TIDAK sehat (exit code 1).
UNHEALTHY_STATUSES = frozenset({STATUS_FAIL, STATUS_UNKNOWN})


@dataclass(frozen=True)
class CheckResult:
    """Hasil satu pemeriksaan."""

    name: str
    check_type: str
    target: str
    status: str
    duration_ms: int
    detail: str


@dataclass
class Report:
    """Laporan lengkap satu eksekusi monitor."""

    started_at: str
    host: str
    monitor_version: str
    results: list[CheckResult]
    duration_ms: int

    def counts(self) -> dict[str, int]:
        counts = {
            STATUS_OK: 0,
            STATUS_WARN: 0,
            STATUS_FAIL: 0,
            STATUS_UNSUPPORTED: 0,
            STATUS_UNKNOWN: 0,
        }
        for r in self.results:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts

    def overall(self) -> str:
        unhealthy = any(r.status in UNHEALTHY_STATUSES for r in self.results)
        return "unhealthy" if unhealthy else "healthy"

    def exit_code(self) -> int:
        # Dokumentasi exit code (monitor/README.md):
        #   0 = sehat (ok/warn/unsupported saja)
        #   1 = minimal satu check fail/unknown
        #   2 = dipakai cli.py untuk kesalahan konfigurasi/eksekusi (di luar report)
        return 1 if self.overall() == "unhealthy" else 0

    def to_dict(self) -> dict:
        return {
            "monitor_version": self.monitor_version,
            "started_at": self.started_at,
            "host": self.host,
            "duration_ms": self.duration_ms,
            "overall": self.overall(),
            "exit_code": self.exit_code(),
            "counts": self.counts(),
            "results": [
                {
                    "name": r.name,
                    "check_type": r.check_type,
                    "target": r.target,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "detail": r.detail,
                }
                for r in self.results
            ],
        }
