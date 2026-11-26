#!/usr/bin/env bash
# simulate_service_permission.sh — INC-004: menyimulasikan permission file
# aplikasi lab yang salah (chmod 000) sehingga restart layanan gagal.
#
# KESELAMATAN:
#   - File target DIPERBAIKI di kode: /opt/demo-http/demo_http_server.py
#     (aplikasi lab). Tidak ada argumen path; skrip menolak file di luar
#     instalasi lab.
#   - Menolak bila mode awal bukan 0755 (mode yang dipasang installer) agar
#     kondisi salah tidak menumpuk tanpa disadari.
#   - Hanya mode file lab yang berubah; tidak ada permission file sistem.
#
# Usage: sudo lab/scripts/simulate_service_permission.sh --yes
# Exit code: 0 kondisi gagal tersimulasi (unit tidak aktif); 1 gagal; 2 usage salah.
set -euo pipefail

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

TARGET="/opt/demo-http/demo_http_server.py"   # DIPERBAIKI — guard terkuat
EXPECTED_MODE="755"                            # mode yang dipasang installer
SERVICE="demo-http"
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) echo "Usage: sudo $0 [--yes]" >&2; exit 2 ;;
    *) echo "Usage: sudo $0 [--yes]" >&2; exit 2 ;;
  esac
done

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[$(TS)] [ERROR] jalankan dengan sudo: sudo lab/scripts/simulate_service_permission.sh --yes" >&2
  exit 2
fi
for c in systemctl stat; do
  command -v "$c" >/dev/null 2>&1 || { echo "[$(TS)] [CONFIG] dependensi hilang: $c" >&2; exit 2; }
done

if [ ! -f "$TARGET" ]; then
  echo "[$(TS)] [CONFIG] ${TARGET} tidak ada — install layanan dulu: sudo lab/scripts/install_demo_service.sh" >&2
  exit 2
fi
case "$(readlink -f "$TARGET")" in
  /opt/demo-http/*) ;;   # ok — bagian instalasi lab
  *) echo "[$(TS)] [SAFETY] target ter-resolve di luar instalasi lab: $(readlink -f "$TARGET") — menolak" >&2; exit 1 ;;
esac

MODE_NOW="$(stat -c '%a' "$TARGET")"
if [ "$MODE_NOW" != "$EXPECTED_MODE" ]; then
  echo "[$(TS)] [SAFETY] mode file kini ${MODE_NOW} (bukan ${EXPECTED_MODE}) — menolak menumpuk simulasi." >&2
  echo "[$(TS)] [SAFETY] jalankan 'sudo lab/scripts/recover_service_permission.sh' untuk mengembalikan mode." >&2
  exit 1
fi

if [ "$ASSUME_YES" -ne 1 ]; then
  echo "[$(TS)] [PERINGATAN] skrip akan chmod 000 pada ${TARGET} lalu me-restart ${SERVICE} (restart akan gagal)."
  read -r -p "Ketik 'ya' untuk lanjut: " ans
  [ "$ans" = "ya" ] || { echo "[$(TS)] dibatalkan oleh pengguna"; exit 1; }
fi

chmod 000 "$TARGET"
echo "[$(TS)] mode file kini: $(stat -c '%a' "$TARGET") (000)"

# Restart adalah operasi normal (deploy/apply konfigurasi) yang akan menemukan masalah.
echo "[$(TS)] memicu: systemctl restart ${SERVICE} (diharapkan gagal)"
systemctl restart "$SERVICE" 2>&1 || echo "[$(TS)] restart gagal seperti diharapkan"

# Tunggu unit settle (unit punya Restart=on-failure; start-limit akan menahan
# retry cepat). Maksimum 30 detik.
STATE="activating"
for _ in $(seq 1 30); do
  STATE="$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
  [ "$STATE" != "active" ] && [ "$STATE" != "activating" ] && break
  sleep 1
done

if [ "$STATE" = "active" ] || [ "$STATE" = "activating" ]; then
  echo "[$(TS)] [GAGAL] unit masih ${STATE} — simulasi tidak mencapai kondisi gagal" >&2
  exit 1
fi

echo "[$(TS)] [OK] kondisi tersimulasi: unit ${SERVICE} kini: ${STATE}"
echo "[$(TS)] gejala: bash lab/scripts/baseline.sh   (harap exit 1)"
echo "[$(TS)] pemulihan: sudo lab/scripts/recover_service_permission.sh"
exit 0
