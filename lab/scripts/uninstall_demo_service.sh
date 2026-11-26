#!/usr/bin/env bash
# uninstall_demo_service.sh — teardown lengkap demo-http (pemulihan lingkungan).
# Membalik semua langkah install_demo_service.sh: stop/disable, hapus unit,
# hapus aplikasi, hapus user sistem (jika dibuat).
#
# Usage: sudo lab/scripts/uninstall_demo_service.sh
# Exit code: 0 sukses; 2 bukan root.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[ERROR] jalankan dengan sudo: sudo lab/scripts/uninstall_demo_service.sh" >&2
  exit 2
fi

echo "[$(TS)] stop & disable layanan..."
systemctl disable --now demo-http.service 2>/dev/null \
  || echo "[$(TS)] [INFO] unit tidak terpasang atau sudah tidak ada"

if [ -f /etc/systemd/system/demo-http.service ]; then
  rm -f /etc/systemd/system/demo-http.service
  systemctl daemon-reload
  echo "[$(TS)] [OK] unit file dihapus dari /etc/systemd/system/"
fi

if [ -d /opt/demo-http ]; then
  rm -rf /opt/demo-http
  echo "[$(TS)] [OK] /opt/demo-http dihapus"
fi

if id demo-http >/dev/null 2>&1 && command -v userdel >/dev/null 2>&1; then
  userdel demo-http && echo "[$(TS)] [OK] user sistem demo-http dihapus"
fi

echo "[$(TS)] teardown selesai. Snapshot VM tidak disentuh — untuk rollback level VM gunakan snapshot di hypervisor."
