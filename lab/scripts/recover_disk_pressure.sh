#!/usr/bin/env bash
# recover_disk_pressure.sh — INC-002: pemulihan setelah simulasi tekanan disk.
# Default : hapus file fixture lab-fill.bin (fixture tetap ter-mount, bisa di-drill ulang).
# --teardown : hapus file, unmount fixture, dan hapus mountpoint (kembalikan kondisi awal).
#
# KESELAMATAN:
#   - Hanya menyentuh /mnt/lab-disk-fixture (path diperbaiki di kode) dan file
#     bernama lab-fill.bin di dalamnya. Tidak ada path lain yang bisa diberikan.
#   - Menolak bila mount di path itu bukan tmpfs (menghindari menyentuh mount
#     milik sistem).
#
# Usage: sudo lab/scripts/recover_disk_pressure.sh [--teardown]
# Exit code: 0 sukses; 1 gagal; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

MP="/mnt/lab-disk-fixture"   # DIPERBAIKI — sama dengan simulate_disk_pressure.sh
TEARDOWN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --teardown) TEARDOWN=1; shift ;;
    -h|--help) echo "Usage: sudo $0 [--teardown]" >&2; exit 2 ;;
    *) echo "Usage: sudo $0 [--teardown]" >&2; exit 2 ;;
  esac
done

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[$(TS)] [ERROR] jalankan dengan sudo: sudo lab/scripts/recover_disk_pressure.sh" >&2
  exit 2
fi

FSTYPE="$(findmnt -n -o FSTYPE "$MP" 2>/dev/null || true)"

if [ -n "$FSTYPE" ] && [ "$FSTYPE" != "tmpfs" ]; then
  echo "[$(TS)] [SAFETY] ${MP} ter-mount dengan FSTYPE='${FSTYPE}' (bukan tmpfs lab) — menolak" >&2
  exit 1
fi

if [ -e "${MP}/lab-fill.bin" ]; then
  rm -f "${MP}/lab-fill.bin"
  echo "[$(TS)] [OK] ${MP}/lab-fill.bin dihapus"
else
  echo "[$(TS)] [INFO] ${MP}/lab-fill.bin tidak ada (tidak apa-apa)"
fi

if [ "$TEARDOWN" -eq 1 ]; then
  if [ -n "$FSTYPE" ]; then
    umount "$MP"
    rmdir "$MP"
    echo "[$(TS)] [OK] fixture di-unmount dan mountpoint dihapus — lingkungan kembali seperti awal"
  else
    [ -d "$MP" ] && rmdir "$MP" 2>/dev/null || true
    echo "[$(TS)] [INFO] tidak ada mount aktif di ${MP}; mountpoint dibersihkan bila ada"
  fi
  exit 0
fi

if [ -n "$FSTYPE" ]; then
  PCT="$(df -P "$MP" | awk 'NR==2 {gsub(/%/,"",$5); print $5}')"
  echo "[$(TS)] df -P ${MP} -> terpakai ${PCT}% (fixture tetap ter-mount untuk drill ulang)"
  echo "[$(TS)] verifikasi penuh: DISK_PATH=${MP} DISK_WARN=50 DISK_CRIT=75 bash lab/scripts/baseline.sh  (harap exit 0)"
  echo "[$(TS)] teardown penuh: sudo lab/scripts/recover_disk_pressure.sh --teardown"
fi
exit 0
