#!/usr/bin/env bash
# recover_service_port.sh — INC-005: menghentikan squatter port 8080 (instance
# lab liar), membersihkan artefaknya, dan menghidupkan kembali unit demo-http
# dengan verifikasi end-to-end.
#
# KESELAMATAN (kill aman):
#   - Hanya PID yang tercatat di lab/runtime/port-squatter.pid yang dipertimbangkan.
#   - Sebelum kill, cmdline proses DIVERIFIKASI mengandung demo_http_server.py.
#     Jika tidak cocok → MENOLAK kill dan keluar dengan pesan.
#   - SIGKILL hanya dipakai bila verifikasi cmdline lolos ULANG setelah SIGTERM
#     dan proses masih hidup.
#
# Usage: sudo lab/scripts/recover_service_port.sh
# Exit code: 0 pemulihan terverifikasi; 1 gagal/ditolak; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

PORT=8080
SERVICE="demo-http"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${SCRIPT_DIR}/../runtime"
PID_FILE="${RUNTIME_DIR}/port-squatter.pid"
SQUATTER_LOG="/tmp/lab-port-squatter.log"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[$(TS)] [ERROR] jalankan dengan sudo: sudo lab/scripts/recover_service_port.sh" >&2
  exit 2
fi
command -v systemctl >/dev/null 2>&1 || { echo "[$(TS)] [ERROR] systemctl tidak tersedia" >&2; exit 1; }

# --- 0. hentikan siklus auto-restart unit (bila ada) sebelum menyentuh squatter ---
# Tanpa ini, setelah squatter dibunuh unit bisa self-heal lewat retry otomatis
# dan membuat pemeriksaan "port bebas" berjalan balapan dengan retry systemd.
systemctl stop "$SERVICE" 2>/dev/null || true
echo "[$(TS)] unit ${SERVICE} dihentikan (membatalkan siklus auto-restart bila ada)"

# --- 1. berhentikan squatter (PID tercatat + verifikasi cmdline) ---
PID="$(cat "$PID_FILE" 2>/dev/null || true)"
case "$PID" in ''*[!0-9]*) PID="" ;; esac

if [ -z "$PID" ]; then
  echo "[$(TS)] [INFO] tidak ada PID squatter tercatat (idempoten)"
elif [ ! -d "/proc/$PID" ]; then
  echo "[$(TS)] [INFO] PID ${PID} sudah tidak ada (stale) — bersihkan catatan"
  rm -f "$PID_FILE"
else
  CMDLINE="$(tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null || true)"
  case "$CMDLINE" in
    *demo_http_server.py*)
      echo "[$(TS)] verifikasi cmdline PID ${PID}: ${CMDLINE}"
      kill "$PID" 2>/dev/null || true
      for _ in $(seq 1 10); do [ -d "/proc/$PID" ] || break; sleep 1; done
      if [ -d "/proc/$PID" ]; then
        CMDLINE2="$(tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null || true)"
        case "$CMDLINE2" in
          *demo_http_server.py*)
            echo "[$(TS)] masih hidup setelah SIGTERM — verifikasi ulang lolos, kirim SIGKILL"
            kill -9 "$PID" || true
            sleep 1
            ;;
          *)
            echo "[$(TS)] [SAFETY] PID ${PID} berubah identitas — tidak dikirim SIGKILL" >&2
            exit 1
            ;;
        esac
      fi
      echo "[$(TS)] [OK] squatter PID ${PID} dihentikan"
      rm -f "$PID_FILE"
      ;;
    *)
      echo "[$(TS)] [SAFETY] cmdline PID ${PID} TIDAK cocok dengan squatter lab ('${CMDLINE}') — menolak kill" >&2
      exit 1
      ;;
  esac
fi

rm -f "$SQUATTER_LOG" 2>/dev/null || true

# --- 2. pastikan port benar-benar bebas ---
if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "[$(TS)] [SAFETY] port ${PORT} MASIH didengarkan proses tak dikenal — unit tidak akan bisa start." >&2
  echo "[$(TS)] [SAFETY] identifikasi dulu: sudo ss -ltnp | grep ${PORT} — jangan kill sembarangan." >&2
  exit 1
fi
echo "[$(TS)] [OK] port ${PORT} bebas"

# --- 3. hidupkan unit dengan verifikasi end-to-end ---
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
