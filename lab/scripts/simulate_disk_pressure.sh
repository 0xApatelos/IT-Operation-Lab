#!/usr/bin/env bash
# simulate_disk_pressure.sh — INC-002: menyimulasikan tekanan disk pada
# FILESYSTEM DISPOSABLE (tmpfs) berukuran kecil — BUKAN filesystem root.
#
# KESELAMATAN:
#   - Mountpoint DIPERBAIKI di kode: /mnt/lab-disk-fixture (tidak bisa diubah
#     lewat argumen). Skrip menolak bila path itu bukan tmpfs milik lab.
#   - Tmpfs hidup di RAM dengan ukuran kecil (default 32 MB) dan hilang saat
#     unmount/reboot — disposable by design. Root filesystem tidak tersentuh.
#   - Tidak ada perubahan pada fstab, systemd mount unit, atau host utama.
#
# Usage:
#   sudo lab/scripts/simulate_disk_pressure.sh --yes                 # mount + isi ~90%
#   sudo lab/scripts/simulate_disk_pressure.sh --yes --mount-only    # hanya mount (untuk baseline sehat)
#   Opsi: --size-mb 8..256 (default 32) · --fill-percent 10..95 (default 90)
#
# Exit code: 0 tekanan disk aktif / fixture siap; 1 gagal; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

MP="/mnt/lab-disk-fixture"   # DIPERBAIKI — guard terkuat: tidak ada argumen path
SIZE_MB=32
FILL_PCT=90
MOUNT_ONLY=0
ASSUME_YES=0

usage() {
  echo "Usage: sudo $0 [--yes] [--mount-only] [--size-mb 8-256] [--fill-percent 10-95]" >&2
  exit 2
}

is_uint() { case "${1:-}" in ''*[!0-9]*) return 1 ;; *) return 0 ;; esac; }

while [ $# -gt 0 ]; do
  case "$1" in
    --yes) ASSUME_YES=1; shift ;;
    --mount-only) MOUNT_ONLY=1; shift ;;
    --size-mb) SIZE_MB="${2:-}"; shift 2 ;;
    --fill-percent) FILL_PCT="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
done

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[$(TS)] [ERROR] jalankan dengan sudo: sudo lab/scripts/simulate_disk_pressure.sh --yes" >&2
  exit 2
fi
is_uint "$SIZE_MB" && [ "$SIZE_MB" -ge 8 ] && [ "$SIZE_MB" -le 256 ] || { echo "[$(TS)] [CONFIG] --size-mb harus 8..256 (dapat: '$SIZE_MB')" >&2; exit 2; }
is_uint "$FILL_PCT" && [ "$FILL_PCT" -ge 10 ] && [ "$FILL_PCT" -le 95 ] || { echo "[$(TS)] [CONFIG] --fill-percent harus 10..95 (dapat: '$FILL_PCT')" >&2; exit 2; }
for c in findmnt dd df; do
  command -v "$c" >/dev/null 2>&1 || { echo "[$(TS)] [CONFIG] dependensi hilang: $c" >&2; exit 2; }
done

if [ "$ASSUME_YES" -ne 1 ] && [ "$MOUNT_ONLY" -ne 1 ]; then
  echo "[$(TS)] [PERINGATAN] skrip akan mount tmpfs ${SIZE_MB} MB di ${MP} dan mengisinya ~${FILL_PCT}%."
  read -r -p "Ketik 'ya' untuk lanjut: " ans
  [ "$ans" = "ya" ] || { echo "[$(TS)] dibatalkan oleh pengguna"; exit 1; }
fi

# --- mount fixture (idempotent) --------------------------------------------
if [ "$(findmnt -n -o FSTYPE "$MP" 2>/dev/null || true)" = "tmpfs" ]; then
  echo "[$(TS)] fixture sudah ter-mount sebagai tmpfs di ${MP} (dipakai ulang, ukuran tidak diubah)"
else
  if [ -e "$MP" ] && [ -n "$(ls -A "$MP" 2>/dev/null)" ]; then
    echo "[$(TS)] [SAFETY] ${MP} ada, bukan tmpfs lab, dan TIDAK kosong — menolak agar tidak menutupi data apa pun" >&2
    exit 1
  fi
  mkdir -p "$MP"
  mount -t tmpfs -o "size=${SIZE_MB}m" tmpfs "$MP"
  echo "[$(TS)] tmpfs ${SIZE_MB} MB di-mount pada ${MP}"
fi

if [ "$MOUNT_ONLY" -eq 1 ]; then
  echo "[$(TS)] [OK] fixture siap (kosong). df -P ${MP}:"
  df -P "$MP"
  exit 0
fi

# --- isi sampai ambang -------------------------------------------------------
# Header blok tmpfs ~0, jadi kapasitas df -P praktis sama dengan ukuran mount.
TARGET_MB=$(( SIZE_MB * FILL_PCT / 100 ))
[ "$TARGET_MB" -ge 1 ] || TARGET_MB=1
echo "[$(TS)] mengisi ${MP}/lab-fill.bin ~${TARGET_MB} MB (target >= ${FILL_PCT}%)"
dd if=/dev/zero of="${MP}/lab-fill.bin" bs=1M count="$TARGET_MB" status=none
sync

PCT="$(df -P "$MP" | awk 'NR==2 {gsub(/%/,"",$5); print $5}')"
echo "[$(TS)] df -P ${MP} -> terpakai ${PCT}%"
df -P "$MP"

# Toleransi pembulatan 5 poin (ukuran tmpfs dibulatkan ke blok).
if [ "${PCT:-0}" -ge $(( FILL_PCT - 5 )) ]; then
  echo "[$(TS)] [OK] tekanan disk aktif. Gejala: DISK_PATH=${MP} DISK_WARN=50 DISK_CRIT=75 bash lab/scripts/baseline.sh  (harap exit 1)"
  echo "[$(TS)] pemulihan: sudo lab/scripts/recover_disk_pressure.sh"
  exit 0
else
  echo "[$(TS)] [GAGAL] pemakaian ${PCT}% di bawah target — periksa ukuran tmpfs" >&2
  exit 1
fi
