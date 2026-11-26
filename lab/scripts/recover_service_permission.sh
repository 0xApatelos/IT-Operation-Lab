#!/usr/bin/env bash
# recover_service_permission.sh — INC-004: kembalikan mode file aplikasi lab
# ke 0755 (mode installer), reset start-limit, dan hidupkan layanan dengan
# verifikasi end-to-end (service aktif DAN /health 200).
#
# KESELAMATAN: path diperbaiki di kode (aplikasi lab saja); menolak non-root.
#
# Usage: sudo lab/scripts/recover_service_permission.sh
# Exit code: 0 pemulihan terverifikasi; 1 belum pulih; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

TARGET="/opt/demo-http/demo_http_server.py"   # DIPERBAIKI — sama dengan simulate
RESTORED_MODE="755"
SERVICE="demo-http"
PORT=8080

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[$(TS)] [ERROR] jalankan dengan sudo: sudo lab/scripts/recover_service_permission.sh" >&2
  exit 2
fi
command -v systemctl >/dev/null 2>&1 || { echo "[$(TS)] [ERROR] systemctl tidak tersedia" >&2; exit 1; }
[ -f "$TARGET" ] || { echo "[$(TS)] [CONFIG] ${TARGET} tidak ada — install layanan dulu" >&2; exit 2; }

chmod "$RESTORED_MODE" "$TARGET"
echo "[$(TS)] [OK] mode file dikembalikan: $(stat -c '%a %U:%G %n' "$TARGET")"

systemctl reset-failed "$SERVICE" 2>/dev/null || true
echo "[$(TS)] memulihkan: systemctl start ${SERVICE}"
systemctl start "$SERVICE"

i=1
while [ "$i" -le 15 ]; do
  if systemctl is-active --quiet "$SERVICE" 2>/dev/null \
     && curl -fsS -m 2 -o /dev/null "http://127.0.0.1:${PORT}/health" 2>/dev/null; then
    echo "[$(TS)] pemulihan TERVERIFIKASI: service aktif + GET /health 200 (percobaan ke-${i})"
    exit 0
  fi
  sleep 1
  i=$((i + 1))
done

echo "[$(TS)] [GAGAL] layanan belum sehat setelah 15 detik. Diagnostik lanjutan:"
echo "  systemctl status ${SERVICE} --no-pager -l"
echo "  sudo journalctl -u ${SERVICE} --no-pager -n 50"
exit 1
