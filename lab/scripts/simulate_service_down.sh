#!/usr/bin/env bash
# simulate_service_down.sh — menyimulasikan insiden "layanan berhenti" (INC-001)
# secara TERKONTROL pada layanan lab.
#
# KESELAMATAN:
#   - Skrip ini hanya menerima layanan 'demo-http'. Nama lain DITOLAK agar
#     tidak ada risiko menghentikan layanan host yang penting.
#   - systemctl stop bersifat sementara: tanpa perubahan konfigurasi, layanan
#     kembali dengan 'systemctl start' atau recover_service.sh (restart polisi
#     unit hanya berlaku untuk crash, bukan stop manual).
#
# Usage:
#   sudo lab/scripts/simulate_service_down.sh --yes   # non-interaktif (dipakai untuk bukti)
#   sudo lab/scripts/simulate_service_down.sh         # interaktif, minta konfirmasi
#
# Alasan butuh root: menghentikan unit sistem systemd memerlukan hak root
# (percobaan tanpa sudo ditolak systemd: 'Access denied' — lihat bukti E03).
#
# Exit code: 0 simulasi aktif (layanan kini berhenti); 1 ditolak/gagal; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

ALLOWED_SERVICE="demo-http"
SERVICE="demo-http"
ASSUME_YES=0

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[ERROR] jalankan dengan sudo: sudo lab/scripts/simulate_service_down.sh --yes" >&2
  exit 2
fi

usage() {
  echo "Usage: $0 [--service demo-http] [--yes]" >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --service) SERVICE="${2:-}"; shift 2 ;;
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
done
[ -n "$SERVICE" ] || usage

# Guard keselamatan: hanya layanan lab yang boleh dihentikan.
if [ "$SERVICE" != "$ALLOWED_SERVICE" ]; then
  echo "[$(TS)] [SAFETY] hanya '${ALLOWED_SERVICE}' yang diizinkan untuk simulasi (diminta: '${SERVICE}'). Ditolak." >&2
  exit 1
fi
command -v systemctl >/dev/null 2>&1 || { echo "[$(TS)] [ERROR] systemctl tidak tersedia" >&2; exit 1; }

if [ "$ASSUME_YES" -ne 1 ]; then
  echo "[$(TS)] [PERINGATAN] skrip ini akan MENYETOP layanan '${SERVICE}' di host ini."
  read -r -p "Ketik 'ya' untuk lanjut: " ans
  [ "$ans" = "ya" ] || { echo "[$(TS)] dibatalkan oleh pengguna"; exit 1; }
fi

echo "[$(TS)] menyimulasikan insiden: systemctl stop ${SERVICE}"
systemctl stop "$SERVICE"

state="$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
echo "[$(TS)] status layanan kini: ${state:-unknown} (diharapkan: inactive)"
echo "[$(TS)] gejala dapat diamati dengan: lab/scripts/baseline.sh  (harap exit 1)"
echo "[$(TS)] pemulihan: lab/scripts/recover_service.sh"
exit 0
