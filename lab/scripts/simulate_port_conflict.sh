#!/usr/bin/env bash
# simulate_port_conflict.sh — INC-005: menyimulasikan konflik port 8080.
# Sebuah instance lab "liar" (squatter) — proses demo_http_server.py yang sama,
# dijalankan TANPA systemd sebagai user layanan demo-http — menempati port,
# sehingga unit demo-http gagal start (bind: Address already in use).
#
# KESELAMATAN:
#   - Squatter = proses lab yang dikendalikan skrip, bukan proses host lain.
#     PID dicatat ke lab/runtime/port-squatter.pid (folder di .gitignore).
#   - Skrip MENOLAK bila port 8080 sudah didengarkan proses tak dikenal.
#   - Pemulihan (recover_service_port.sh) hanya membunuh PID yang cmdline-nya
#     TERVERIFIKASI mengandung demo_http_server.py.
#
# Usage: sudo lab/scripts/simulate_port_conflict.sh --yes
# Exit code: 0 kondisi konflik tersimulasi; 1 gagal/ditolak; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

PORT=8080
SERVICE="demo-http"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${SCRIPT_DIR}/../runtime"
PID_FILE="${RUNTIME_DIR}/port-squatter.pid"
SQUATTER_LOG="/tmp/lab-port-squatter.log"   # dibuat oleh user demo-http di /tmp
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) echo "Usage: sudo $0 [--yes]" >&2; exit 2 ;;
    *) echo "Usage: sudo $0 [--yes]" >&2; exit 2 ;;
  esac
done

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[$(TS)] [ERROR] jalankan dengan sudo: sudo lab/scripts/simulate_port_conflict.sh --yes" >&2
  exit 2
fi
for c in systemctl ss; do
  command -v "$c" >/dev/null 2>&1 || { echo "[$(TS)] [CONFIG] dependensi hilang: $c" >&2; exit 2; }
done
systemctl cat "${SERVICE}.service" >/dev/null 2>&1 \
  || { echo "[$(TS)] [CONFIG] unit ${SERVICE} belum ter-install" >&2; exit 2; }
id demo-http >/dev/null 2>&1 || { echo "[$(TS)] [CONFIG] user demo-http tidak ada — install layanan dulu" >&2; exit 2; }

if [ "$ASSUME_YES" -ne 1 ]; then
  echo "[$(TS)] [PERINGATAN] skrip akan: stop ${SERVICE} -> jalankan instance lab liar di port ${PORT}"
  echo "[$(TS)] [PERINGATAN] (sebagai user demo-http, PID dicatat) -> mencoba start ${SERVICE} (gagal bind)."
  read -r -p "Ketik 'ya' untuk lanjut: " ans
  [ "$ans" = "ya" ] || { echo "[$(TS)] dibatalkan oleh pengguna"; exit 1; }
fi

# --- 1. stop layanan terkelola (layanan lab; diizinkan) ---
systemctl stop "$SERVICE"
echo "[$(TS)] ${SERVICE} dihentikan"

# --- 2. guard: port harus benar-benar bebas sebelum squatter mulai ---
if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "[$(TS)] [SAFETY] port ${PORT} SUDAH didengarkan proses tak dikenal — simulasi dibatalkan." >&2
  echo "[$(TS)] [SAFETY] identifikasi dulu: sudo ss -ltnp | grep ${PORT} — jangan kill sembarangan." >&2
  exit 1
fi

# --- 3. jalankan squatter sebagai user demo-http (bukan root), PID dicatat ---
install -d -m 0755 "$RUNTIME_DIR"
SQUATTER_PID="$(sudo -n -u demo-http sh -c "nohup python3 -u /opt/demo-http/demo_http_server.py --port ${PORT} > ${SQUATTER_LOG} 2>&1 & echo \$!")"
case "$SQUATTER_PID" in
  ''*[!0-9]*) echo "[$(TS)] [GAGAL] PID squatter tidak valid: '${SQUATTER_PID}'" >&2; exit 1 ;;
esac
echo "$SQUATTER_PID" > "$PID_FILE"
echo "[$(TS)] squatter mulai: PID ${SQUATTER_PID} (log: ${SQUATTER_LOG})"

# --- 4. verifikasi squatter benar-benar mendengarkan ---
LISTENING=0
for _ in $(seq 1 10); do
  if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then LISTENING=1; break; fi
  sleep 1
done
if [ "$LISTENING" -ne 1 ]; then
  echo "[$(TS)] [GAGAL] squatter tidak mendengarkan port ${PORT}. Isi log:" >&2
  cat "$SQUATTER_LOG" >&2 || true
  exit 1
fi
echo "[$(TS)] [OK] port ${PORT} kini didengarkan oleh PID ${SQUATTER_PID} (di luar systemd)"

# --- 5. coba start unit (diharapkan gagal bind) ---
echo "[$(TS)] memicu: systemctl start ${SERVICE} (diharapkan gagal: Address already in use)"
systemctl start "$SERVICE" 2>&1 || echo "[$(TS)] start gagal seperti diharapkan"

# --- 6. tunggu unit tidak lagi active (kondisi konflik tercapai) ---
# Dua signature kegagalan mungkin terjadi di bawah Restart=on-failure:
#   a) kegagalan exit instan (mis. permission denied) -> start-limit-hit dalam ~10 detik,
#      state menjadi 'failed'
#   b) kegagalan bind (~0.5s per percobaan; import python lalu OSError) -> auto-restart
#      terus-menerus (cycle ~2.5s tidak memicu StartLimitBurst=5/10s), state tetap 'activating'
# Keduanya berarti unit TIDAK aktif. Syarat sukses: state != 'active' selama >=3 poll beruntun,
# dan port masih didengarkan squatter.
NOT_ACTIVE_STREAK=0
STATE="unknown"
for _ in $(seq 1 60); do
  STATE="$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
  if [ "$STATE" != "active" ]; then
    NOT_ACTIVE_STREAK=$((NOT_ACTIVE_STREAK + 1))
    [ "$NOT_ACTIVE_STREAK" -ge 3 ] && break
  else
    NOT_ACTIVE_STREAK=0
  fi
  sleep 1
done

if [ "$NOT_ACTIVE_STREAK" -lt 3 ]; then
  echo "[$(TS)] [GAGAL] unit masih active — simulasi tidak mencapai kondisi konflik" >&2
  exit 1
fi
if ! ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "[$(TS)] [GAGAL] port ${PORT} tidak lagi didengarkan — kondisi konflik tidak stabil" >&2
  exit 1
fi

echo "[$(TS)] [OK] kondisi tersimulasi: unit ${SERVICE} tidak aktif (state: ${STATE}); port ${PORT} dipegang PID ${SQUATTER_PID}"
echo "[$(TS)] [INFO] state 'activating' = auto-restart berulang (Restart=on-failure); state 'failed' = start-limit-hit"
echo "[$(TS)] gejala: bash lab/scripts/baseline.sh   (harap exit 1 — perhatikan service FAIL tetapi tcp/http OK)"
echo "[$(TS)] pemulihan: sudo lab/scripts/recover_service_port.sh"
exit 0
