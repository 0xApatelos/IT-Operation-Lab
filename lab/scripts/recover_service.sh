#!/usr/bin/env bash
# recover_service.sh — memulihkan layanan lab yang berhenti dan memverifikasi
# pemulihan secara end-to-end (service aktif DAN HTTP /health 200).
#
# KESELAMATAN: hanya untuk layanan 'demo-http' (guard sama dengan skrip simulasi).
#
# Usage: sudo lab/scripts/recover_service.sh [--service demo-http]
#
# Alasan butuh root: menjalankan unit sistem systemd memerlukan hak root
# (sama seperti simulate_service_down.sh).
#
# Exit code: 0 pemulihan terverifikasi; 1 belum pulih dalam batas waktu; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

ALLOWED_SERVICE="demo-http"
SERVICE="demo-http"
PORT=8080
MAX_TRIES=15

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[ERROR] jalankan dengan sudo: sudo lab/scripts/recover_service.sh" >&2
  exit 2
fi

usage() {
  echo "Usage: $0 [--service demo-http]" >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --service) SERVICE="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
done
[ -n "$SERVICE" ] || usage

if [ "$SERVICE" != "$ALLOWED_SERVICE" ]; then
  echo "[$(TS)] [SAFETY] hanya '${ALLOWED_SERVICE}' yang diizinkan (diminta: '${SERVICE}'). Ditolak." >&2
  exit 1
fi
command -v systemctl >/dev/null 2>&1 || { echo "[$(TS)] [ERROR] systemctl tidak tersedia" >&2; exit 1; }

echo "[$(TS)] memulihkan: systemctl start ${SERVICE}"
systemctl start "$SERVICE"

i=1
while [ "$i" -le "$MAX_TRIES" ]; do
  if systemctl is-active --quiet "$SERVICE" 2>/dev/null \
     && curl -fsS -m 2 -o /dev/null "http://127.0.0.1:${PORT}/health" 2>/dev/null; then
    echo "[$(TS)] pemulihan TERVERIFIKASI: service aktif + GET /health 200 (percobaan ke-${i})"
    exit 0
  fi
  sleep 1
  i=$((i + 1))
done

echo "[$(TS)] [GAGAL] layanan belum sehat setelah ${MAX_TRIES} detik. Diagnostik lanjutan:"
echo "  systemctl status ${SERVICE} --no-pager -l"
echo "  journalctl -u ${SERVICE} --no-pager -n 50"
exit 1
