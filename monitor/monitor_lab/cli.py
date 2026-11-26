"""CLI lab-monitor: parse argumen, jalankan check, cetak laporan, exit code.

Exit code (dokumentasi lengkap di monitor/README.md):
  0 = seluruh pemeriksaan sehat (status ok/warn/unsupported)
  1 = minimal satu check fail/unknown
  2 = kesalahan konfigurasi atau eksekusi CLI (menang atas 0/1)

Prioritas exit code: 2 (config/eksekusi) > 1 (unhealthy) > 0 (healthy).
"""

from __future__ import annotations

import argparse
import logging
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .adapters import build_default_adapters
from .checks import run_check
from .config import ConfigError, MonitorConfig, load_config
from .logging_setup import setup_logging
from .models import Report
from .notify import WebhookNotifier
from .output import render_json, render_text

log = logging.getLogger("monitor_lab.cli")

# Titik injeksi untuk unit test (demonkeypatch).
build_adapters = build_default_adapters


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lab-monitor",
        description="System Health Monitor untuk IT operations lab (Fase 2).",
        epilog=(
            "Exit code: 0 = sehat, 1 = ada check fail/unknown, "
            "2 = kesalahan konfigurasi/eksekusi (menang atas lainnya). "
            "Warn dan unsupported tidak membuat exit 1."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        required=True,
        help="path file konfigurasi JSON (lihat monitor/config.example.json)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="format output ke stdout (default: text)",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="path opsional untuk menulis laporan JSON (mis. untuk arsip/CI)",
    )
    parser.add_argument("--version", action="version", version=f"monitor-lab {__version__}")
    return parser.parse_args(argv)


def _run_checks(cfg: MonitorConfig) -> Report:
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    adapters = build_adapters()
    results = [run_check(c, adapters) for c in cfg.checks]
    duration_ms = int((time.perf_counter() - started) * 1000)
    return Report(
        started_at=started_at,
        host=socket.gethostname(),
        monitor_version=__version__,
        results=results,
        duration_ms=duration_ms,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"[CONFIG-ERROR] {e}", file=sys.stderr)
        return 2

    setup_logging(cfg.output.log_file, cfg.output.log_level)
    log.info("monitor mulai: config=%s checks=%d", cfg.source_path, len(cfg.checks))

    report = _run_checks(cfg)

    print(render_json(report) if args.format == "json" else render_text(report))

    if args.json_out:
        try:
            Path(args.json_out).write_text(render_json(report), encoding="utf-8")
        except OSError as e:
            # Gagal menulis arsip tidak boleh menyembunyikan hasil health check.
            log.warning("gagal menulis --json-out %s: %s (exit code tetap dari health)", args.json_out, e)

    try:
        WebhookNotifier(cfg.alerts).notify(report)
    except Exception as e:  # noqa: BLE001 - pertahanan ekstra: alert tak boleh memengaruhi exit
        log.warning("webhook error tak terduga: %s (exit code tetap dari health)", e)

    log.info(
        "monitor selesai: overall=%s exit=%d durasi=%dms",
        report.overall(),
        report.exit_code(),
        report.duration_ms,
    )
    return report.exit_code()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
