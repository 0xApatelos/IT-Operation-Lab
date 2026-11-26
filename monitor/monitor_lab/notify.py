"""Notifikasi webhook (opsional, DINONAKTIFKAN secara default).

Prinsip:
- URL webhook berasal dari environment variable (nama env dikonfigurasi),
  BUKAN dari source code/config — jadi tidak ada secret di repo.
- Dedup: satu alert per kombinasi (host, check, status) dalam jendela
  dedup_seconds, dicatat di state file agar bertahan antar eksekusi
  (monitor dijalankan berkala oleh scheduler sebagai proses baru).
- Kegagalan pengiriman TIDAK mengubah hasil health check dan TIDAK mengubah
  exit code — hanya warning di log. State dedup hanya dicatat saat sukses,
  sehingga alert yang gagal dikirim dicoba lagi pada eksekusi berikutnya.
- Payload tidak memuat secret atau isi environment, hanya hasil check.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

from . import __version__
from .config import AlertConfig
from .models import UNHEALTHY_STATUSES, Report

log = logging.getLogger("monitor_lab.notify")


class WebhookNotifier:
    def __init__(self, cfg: AlertConfig) -> None:
        self.cfg = cfg

    def notify(self, report: Report) -> bool:
        """Kirim alert bila ada check unhealthy. Return True bila terkirim."""
        if not self.cfg.webhook_enabled:
            return False
        failing = [r for r in report.results if r.status in UNHEALTHY_STATUSES]
        if not failing:
            return False

        url = os.environ.get(self.cfg.webhook_url_env, "").strip()
        if not url:
            log.warning(
                "webhook enabled tetapi environment variable %s kosong — alert dilewati",
                self.cfg.webhook_url_env,
            )
            return False

        key = f"{report.host}:" + ",".join(sorted(f"{r.name}:{r.status}" for r in failing))
        now = time.time()
        state = self._load_state()
        last = state.get(key)
        if isinstance(last, (int, float)) and (now - last) < self.cfg.dedup_seconds:
            log.info("alert untuk %s dilewati (dedup %ss)", key, self.cfg.dedup_seconds)
            return False

        payload = {
            "monitor_version": report.monitor_version,
            "host": report.host,
            "started_at": report.started_at,
            "overall": report.overall(),
            "failing": [
                {
                    "name": r.name,
                    "check_type": r.check_type,
                    "target": r.target,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "detail": r.detail,
                }
                for r in failing
            ],
        }
        sent = self._post_with_retry(url, payload)
        if sent:
            state[key] = now
            self._save_state(state)
            log.info("alert terkirim ke webhook (%d check unhealthy)", len(failing))
        else:
            log.warning(
                "gagal mengirim webhook setelah %d percobaan — hasil health check tidak terpengaruh",
                self.cfg.retry_max + 1,
            )
        return sent

    # --- internals (dipisah agar mudah difake di unit test) -------------------

    def _post_with_retry(self, url: str, payload: dict) -> bool:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        attempts = self.cfg.retry_max + 1
        for i in range(attempts):
            try:
                return self._post(url, data)
            except Exception as e:  # noqa: BLE001 - kegagalan network apa pun bukan fatal
                log.warning("percobaan webhook %d/%d gagal: %s", i + 1, attempts, e)
                if i < attempts - 1:
                    time.sleep(min(0.5 * (i + 1), 2.0))
        return False

    def _post(self, url: str, data: bytes) -> bool:
        req = Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": f"monitor-lab/{__version__}"},
            method="POST",
        )
        with urlopen(req, timeout=self.cfg.webhook_timeout_seconds) as resp:
            code = int(resp.getcode())
            return 200 <= code < 300

    def _load_state(self) -> dict:
        if not self.cfg.state_file:
            return {}
        try:
            text = Path(self.cfg.state_file).read_text(encoding="utf-8")
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_state(self, state: dict) -> None:
        if not self.cfg.state_file:
            return
        path = Path(self.cfg.state_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
