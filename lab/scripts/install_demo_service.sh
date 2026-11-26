#!/usr/bin/env bash
# install_demo_service.sh — pasang demo-http sebagai layanan systemd.
# Target utama: Ubuntu Server 24.04 LTS VM. Jalankan dengan sudo.
# Tidak butuh koneksi internet (semua file disalin dari repository lokal).
#
# Yang dilakukan skrip ini:
#   1. membuat user sistem khusus demo-http (lihat fallback di bawah)
#   2. menyalin demo_http_server.py ke /opt/demo-http/
#   3. memasang unit /etc/systemd/system/demo-http.service dari template repo
#   4. systemctl enable --now demo-http
#   5. verifikasi GET /health di http://127.0.0.1:8080
#
# Fallback (dicatat eksplisit): jika useradd/adduser tidak tersedia (mis.
# container minimal), layanan berjalan sebagai user pemanggil. Ini hanya
# untuk pengujian dev — konfigurasi target tetap user sistem khusus.
#
# Exit code: 0 sukses; 1 gagal instalasi/verifikasi; 2 penggunaan salah.
set -euo pipefail

APP_USER="demo-http"
INSTALL_DIR="/opt/demo-http"
PORT=8080
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../services/demo-http"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[ERROR] jalankan dengan sudo: sudo lab/scripts/install_demo_service.sh" >&2
  exit 2
fi

for f in "${SRC_DIR}/demo_http_server.py" "${SRC_DIR}/demo-http.service"; do
  [ -f "$f" ] || { echo "[ERROR] file sumber tidak ada: $f — jalankan dari dalam repository" >&2; exit 2; }
done

PYTHON_BIN="$(command -v python3 || true)"
[ -x "${PYTHON_BIN:-}" ] || { echo "[ERROR] python3 tidak ditemukan" >&2; exit 2; }

# --- 1. user layanan -------------------------------------------------------
UNIT_USER=""
if id "$APP_USER" >/dev/null 2>&1; then
  UNIT_USER="$APP_USER"
  echo "[INFO] user ${APP_USER} sudah ada"
elif command -v useradd >/dev/null 2>&1; then
  useradd --system --home-dir /nonexistent \
    --shell "$(command -v nologin || echo /usr/sbin/nologin)" "$APP_USER"
  UNIT_USER="$APP_USER"
  echo "[INFO] user sistem ${APP_USER} dibuat"
elif command -v adduser >/dev/null 2>&1; then
  adduser --system --group --no-create-home --home /nonexistent "$APP_USER" >/dev/null
  UNIT_USER="$APP_USER"
  echo "[INFO] user sistem ${APP_USER} dibuat (adduser)"
else
  UNIT_USER="${SUDO_USER:-$(id -un)}"
  echo "[PERINGATAN] useradd/adduser tidak tersedia — layanan berjalan sebagai '${UNIT_USER}' (fallback dev, bukan konfigurasi target)"
fi

# --- 2. salin aplikasi -----------------------------------------------------
install -d -m 0755 "$INSTALL_DIR"
install -m 0755 "${SRC_DIR}/demo_http_server.py" "${INSTALL_DIR}/demo_http_server.py"

# --- 3. unit systemd -------------------------------------------------------
sed -e "s|@@PYTHON_BIN@@|${PYTHON_BIN}|g" \
    -e "s|@@SERVICE_USER@@|${UNIT_USER}|g" \
    "${SRC_DIR}/demo-http.service" > /etc/systemd/system/demo-http.service
chmod 0644 /etc/systemd/system/demo-http.service

# --- 4. aktifkan -----------------------------------------------------------
systemctl daemon-reload
systemctl enable --now demo-http.service

# --- 5. verifikasi ---------------------------------------------------------
HEALTHY=0
for _ in $(seq 1 10); do
  if curl -fsS -m 2 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then HEALTHY=1; break; fi
  sleep 1
done
if [ "$HEALTHY" -ne 1 ]; then
  echo "[ERROR] layanan tidak merespons /health dalam 10 detik. Diagnostik:" >&2
  echo "  systemctl status demo-http --no-pager -l" >&2
  echo "  journalctl -u demo-http --no-pager -n 50" >&2
  exit 1
fi

echo "[OK] demo-http aktif di port ${PORT} (user: ${UNIT_USER}, python: ${PYTHON_BIN})"
echo "Langkah berikutnya:"
echo "  lab/scripts/baseline.sh                        # baseline sehat (harap exit 0)"
echo "  lab/scripts/simulate_service_down.sh --yes     # simulasi insiden INC-001"
echo "  lab/scripts/recover_service.sh                 # pemulihan"
