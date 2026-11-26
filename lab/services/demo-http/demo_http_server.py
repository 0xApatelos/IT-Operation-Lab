#!/usr/bin/env python3
"""demo-http: layanan HTTP kecil untuk latihan lab IT Support Homelab.

- Stdlib-only (tanpa dependensi pihak ketiga) agar mudah diaudit dan dijalankan
  di VM Ubuntu minimal tanpa pip.
- Endpoint:
    GET /        -> 200 JSON info layanan
    GET /health  -> 200 JSON {"status": "ok", ...}   (dipakai baseline & monitor)
    GET lainnya  -> 404 JSON
- Bukan server produksi: http.server adalah server pengembangan; cukup untuk
  skenario lab (aktif/berhenti/port/HTTP status).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_VERSION = "0.1.0"


def build_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"demo-http/{APP_VERSION}"

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (nama wajib dari BaseHTTPRequestHandler)
            if self.path in ("/", "/health"):
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "service": "demo-http",
                        "version": APP_VERSION,
                        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    },
                )
            else:
                self._send_json(404, {"error": "not found", "path": self.path})

        def log_message(self, fmt: str, *args: object) -> None:
            # Arahkan access log ke logging (stdout) agar masuk journald via unit systemd.
            logging.info("%s - %s", self.address_string(), fmt % args)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="demo-http: layanan HTTP latihan lab")
    parser.add_argument("--bind", default="0.0.0.0", help="alamat bind (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="port listen (default 8080)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    server = ThreadingHTTPServer((args.bind, args.port), build_handler())
    logging.info("demo-http %s listening on %s:%d", APP_VERSION, args.bind, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("demo-http dihentikan (KeyboardInterrupt)")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
