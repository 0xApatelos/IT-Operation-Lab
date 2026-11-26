#!/usr/bin/env bash
# baseline.sh — pemeriksaan kesehatan dasar untuk IT Support Homelab (Fase 1).
#
# Memeriksa: kapasitas disk, status layanan systemd, resolusi DNS, port TCP,
# dan HTTP health check (dengan timeout).
# Ini versi bash untuk Fase 1; versi Python terstruktur (JSON, adapter, notifikasi)
# dibangun di Fase 2 pada monitor/ dengan skema exit code yang setara.
#
# Exit code:
#   0 = semua pemeriksaan sehat (check UNSUPPORTED tidak dihitung gagal)
#   1 = minimal satu pemeriksaan gagal
#   2 = kesalahan konfigurasi atau eksekusi (dependensi hilang, ambang tidak valid)
# Prioritas: kesalahan konfigurasi selalu exit 2, menang atas exit 1.
#
# Konfigurasi via environment variable (semua opsional):
#   DISK_PATH   (default /)                  path yang diperiksa
#   DISK_WARN   (default 80)                 ambang peringatan % (tidak membuat exit 1)
#   DISK_CRIT   (default 90)                 ambang kritis %
#   SERVICE_NAME (default demo-http)         unit systemd yang diperiksa
#   DNS_HOST    (default archive.ubuntu.com) hostname untuk uji resolusi
#   TCP_HOST    (default 127.0.0.1)          target uji TCP
#   TCP_PORT    (default 8080)               port uji TCP
#   HTTP_URL    (default http://127.0.0.1:8080/health)
#   HTTP_TIMEOUT (default 5)                 detik
#
# Catatan:
#   - Tidak butuh root.
#   - Di host tanpa systemd (mis. macOS), check layanan dilaporkan UNSUPPORTED.
#   - Check DNS memerlukan jalur keluar (mis. adapter NAT di VM). Pada jaringan
#     host-only penuh, set DNS_HOST=localhost atau isi hasilnya akan gagal.

set -u

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

DISK_PATH="${DISK_PATH:-/}"
DISK_WARN="${DISK_WARN:-80}"
DISK_CRIT="${DISK_CRIT:-90}"
SERVICE_NAME="${SERVICE_NAME:-demo-http}"
DNS_HOST="${DNS_HOST:-archive.ubuntu.com}"
TCP_HOST="${TCP_HOST:-127.0.0.1}"
TCP_PORT="${TCP_PORT:-8080}"
HTTP_URL="${HTTP_URL:-http://127.0.0.1:8080/health}"
HTTP_TIMEOUT="${HTTP_TIMEOUT:-5}"

HEALTHY=0
FAILED=0
UNSUPPORTED=0

fail_config() {
  echo "[$(TS)] [CONFIG-ERROR] $1" >&2
  exit 2
}

# --- validasi konfigurasi ---------------------------------------------------
case "${DISK_WARN}${DISK_CRIT}" in
  *[!0-9]*) fail_config "DISK_WARN dan DISK_CRIT harus angka (dapat: '${DISK_WARN}', '${DISK_CRIT}')" ;;
esac
[ "$DISK_WARN" -lt "$DISK_CRIT" ] || fail_config "DISK_WARN (${DISK_WARN}) harus lebih kecil dari DISK_CRIT (${DISK_CRIT})"
case "$TCP_PORT" in
  ''*[!0-9]*) fail_config "TCP_PORT harus angka (dapat: '${TCP_PORT}')" ;;
esac
[ "$TCP_PORT" -ge 1 ] && [ "$TCP_PORT" -le 65535 ] || fail_config "TCP_PORT di luar rentang 1-65535"
case "$TCP_HOST" in
  *[!A-Za-z0-9._-]*) fail_config "TCP_HOST hanya boleh berisi huruf, angka, titik, garis bawah, minus" ;;
esac

for c in df timeout curl; do
  command -v "$c" >/dev/null 2>&1 || fail_config "dependensi wajib tidak ada: $c"
done

echo "[$(TS)] baseline: mulai (host=$(hostname), user=$(id -un))"

# --- 1. kapasitas disk ------------------------------------------------------
if pct=$(df -P "$DISK_PATH" 2>/dev/null | awk 'NR==2 {gsub(/%/,"",$5); print $5}'); then
  if [ -n "$pct" ]; then
    if [ "$pct" -ge "$DISK_CRIT" ]; then
      echo "[$(TS)] [FAIL] disk: ${DISK_PATH} terpakai ${pct}% >= CRIT ${DISK_CRIT}%"
      FAILED=$((FAILED + 1))
    elif [ "$pct" -ge "$DISK_WARN" ]; then
      echo "[$(TS)] [WARN] disk: ${DISK_PATH} terpakai ${pct}% >= WARN ${DISK_WARN}% (masih dihitung sehat)"
      HEALTHY=$((HEALTHY + 1))
    else
      echo "[$(TS)] [OK] disk: ${DISK_PATH} terpakai ${pct}% (warn ${DISK_WARN}% crit ${DISK_CRIT}%)"
      HEALTHY=$((HEALTHY + 1))
    fi
  else
    echo "[$(TS)] [FAIL] disk: output df tidak terbaca untuk ${DISK_PATH}"
    FAILED=$((FAILED + 1))
  fi
else
  fail_config "df gagal untuk path ${DISK_PATH} (path tidak ada?)"
fi

# --- 2. status layanan systemd ----------------------------------------------
if command -v systemctl >/dev/null 2>&1; then
  if systemctl cat "${SERVICE_NAME}.service" >/dev/null 2>&1; then
    state="$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || true)"
    if [ "$state" = "active" ]; then
      echo "[$(TS)] [OK] service: ${SERVICE_NAME} active"
      HEALTHY=$((HEALTHY + 1))
    else
      echo "[$(TS)] [FAIL] service: ${SERVICE_NAME} status=${state:-unknown} (diharapkan active)"
      FAILED=$((FAILED + 1))
    fi
  else
    echo "[$(TS)] [FAIL] service: unit ${SERVICE_NAME}.service tidak ditemukan (belum di-install?)"
    FAILED=$((FAILED + 1))
  fi
else
  echo "[$(TS)] [UNSUPPORTED] service: systemctl tidak tersedia di platform ini"
  UNSUPPORTED=$((UNSUPPORTED + 1))
fi

# --- 3. resolusi DNS ---------------------------------------------------------
if command -v getent >/dev/null 2>&1; then
  dns_ip="$(getent hosts "$DNS_HOST" 2>/dev/null | awk 'NR==1 {print $1}')"
  if [ -n "$dns_ip" ]; then
    echo "[$(TS)] [OK] dns: ${DNS_HOST} -> ${dns_ip}"
    HEALTHY=$((HEALTHY + 1))
  else
    echo "[$(TS)] [FAIL] dns: resolusi ${DNS_HOST} gagal"
    FAILED=$((FAILED + 1))
  fi
else
  echo "[$(TS)] [UNSUPPORTED] dns: getent tidak tersedia"
  UNSUPPORTED=$((UNSUPPORTED + 1))
fi

# --- 4. konektivitas TCP ------------------------------------------------------
# /dev/tcp adalah fitur bash; timeout membatasi waktu tunggu koneksi.
if timeout 3 bash -c "exec 3<>/dev/tcp/${TCP_HOST}/${TCP_PORT}" 2>/dev/null; then
  echo "[$(TS)] [OK] tcp: ${TCP_HOST}:${TCP_PORT} terhubung"
  HEALTHY=$((HEALTHY + 1))
else
  echo "[$(TS)] [FAIL] tcp: ${TCP_HOST}:${TCP_PORT} gagal (refused/timeout/port tertutup)"
  FAILED=$((FAILED + 1))
fi

# --- 5. HTTP health check -----------------------------------------------------
http_out="$(curl -fsS -m "$HTTP_TIMEOUT" -o /dev/null -w '%{http_code} %{time_total}s' "$HTTP_URL" 2>/dev/null)"
http_rc=$?
case $http_rc in
  0)
    echo "[$(TS)] [OK] http: GET ${HTTP_URL} -> ${http_out}"
    HEALTHY=$((HEALTHY + 1))
    ;;
  22)
    echo "[$(TS)] [FAIL] http: respons non-2xx dari ${HTTP_URL} (${http_out:-tanpa kode})"
    FAILED=$((FAILED + 1))
    ;;
  7)
    echo "[$(TS)] [FAIL] http: koneksi ditolak ke ${HTTP_URL} (curl rc=7)"
    FAILED=$((FAILED + 1))
    ;;
  28)
    echo "[$(TS)] [FAIL] http: timeout ${HTTP_TIMEOUT}s pada ${HTTP_URL} (curl rc=28)"
    FAILED=$((FAILED + 1))
    ;;
  *)
    echo "[$(TS)] [FAIL] http: curl rc=${http_rc} pada ${HTTP_URL}"
    FAILED=$((FAILED + 1))
    ;;
esac

# --- ringkasan & exit ----------------------------------------------------------
TOTAL=$((HEALTHY + FAILED + UNSUPPORTED))
echo "[$(TS)] ringkasan: sehat=${HEALTHY} gagal=${FAILED} unsupported=${UNSUPPORTED} total=${TOTAL}"
if [ "$FAILED" -gt 0 ]; then
  echo "[$(TS)] baseline: TIDAK SEHAT -> exit 1"
  exit 1
fi
echo "[$(TS)] baseline: SEHAT -> exit 0"
exit 0
