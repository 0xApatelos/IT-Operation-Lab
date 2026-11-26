# monitor/ — System Health Monitor (Fase 2)

CLI Python yang mengotomasi pemeriksaan yang digunakan pada Homelab (Fase 1).
CLI-first (tanpa dashboard), runtime **stdlib-only** (nol dependensi produksi),
dua dependensi dev: `pytest` dan `ruff`.

## Status

| Bagian | Status |
|---|---|
| 5 check: disk, service (systemd), DNS, TCP, HTTP | implemented + tested (unit) + integration (sandbox) |
| Konfigurasi JSON tervalidasi ketat | implemented + tested |
| Output teks + JSON, timestamp timezone | implemented + tested |
| Exit code 0/1/2 sesuai dokumentasi | implemented + tested |
| Logging JSON + rotasi (512 KiB × 3) | implemented + tested |
| Webhook adapter (off default, env-based, dedup, retry) | implemented + tested (+ bukti nyata sandbox) |
| Scheduler systemd timer (Ubuntu VM) | implemented; unit diverifikasi `systemd-analyze verify`; eksekusi periodik di VM = requires manual verification |
| Auto-remediation | **tidak ada (sengaja, sesuai desain MVP)** |

## Arsitektur

```
config.py    → load + validasi ketat (ConfigError → exit 2)
checks.py    → 5 check murni (menerima adapters; exception → status terdefinisi)
adapters.py  → OS-specific: systemctl (subprocess list-argv, tanpa shell),
               disk (shutil), DNS (getaddrinfo + guard timeout thread),
               TCP (socket.create_connection), HTTP (urllib + timeout)
output.py    → teks manusiawi + JSON terstruktur
notify.py    → webhook opsional (env-based URL, dedup state file, retry terbatas)
cli.py       → argparse, orkestrasi, exit code
```

Status check: `ok`, `warn` (hanya disk; tidak membuat exit 1), `fail`,
`unsupported` (platform tidak mendukung — bukan kegagalan), `unknown`
(exception tak terduga — dihitung tidak sehat).

## Exit code

| Kode | Arti |
|---|---|
| 0 | seluruh pemeriksaan sehat (ok/warn/unsupported) |
| 1 | minimal satu check `fail` atau `unknown` |
| 2 | kesalahan konfigurasi/eksekusi CLI (config hilang/invalid, dll.) |

**Prioritas: 2 > 1 > 0.** Kegagalan pengiriman alert atau gagal menulis
`--json-out` TIDAK mengubah exit code (warning di log saja).

## Install & jalankan

```bash
cd it-operations-ai-lab
python3 -m venv .venv
.venv/bin/pip install -e 'monitor[dev]'
.venv/bin/lab-monitor --config monitor/config.example.json          # contoh tanpa menyalin
# konfigurasi milik Anda:
cp monitor/config.example.json monitor/config.json   # (config.json di .gitignore)
.venv/bin/lab-monitor --config monitor/config.json --format text    # default
.venv/bin/lab-monitor --config monitor/config.json --format json    # JSON ke stdout
.venv/bin/lab-monitor --config monitor/config.json --json-out runtime-laporan.json
```

Alternatif tanpa install: `python3 -m monitor_lab --config ...` dari folder
`monitor/`.

### Referensi konfigurasi (monitor/config.example.json)

- `checks`: list; `type` salah satu `disk|service|dns|tcp|http`; `name` unik.
  - `disk`: `path`, `warn_pct` < `crit_pct` (1–99).
  - `service`: `unit` (hanya huruf/angka dan `@ . _ -` — divalidasi agar aman
    untuk argv).
  - `dns`: `host`, `timeout_seconds` (0–60].
  - `tcp`: `host`, `port` (1–65535), `timeout_seconds`.
  - `http`: `url` (http/https), `timeout_seconds`. 2xx = ok, non-2xx = fail.
- `output`: `log_file` (relatif di-resolve terhadap folder config),
  `log_level` (DEBUG/INFO/WARNING/ERROR).
- `alerts`: `webhook_enabled` (**false default**), `webhook_url_env` (nama
  env berisi URL — token/URL tidak pernah di file config), `retry_max` (0–5),
  `dedup_seconds` (0–86400), `state_file` (dedup antar eksekusi).

Path relatif di-resolve terhadap direktori file konfigurasi sehingga
perilaku konsisten dijalankan dari folder mana pun (termasuk oleh systemd).

## Alert webhook

- URL dari environment: `LAB_WEBHOOK_URL=http://…` (lihat nama env di config).
- Payload hanya berisi hasil check (host, waktu, check fail/unknown + detail)
  — tanpa secret dan tanpa isi environment.
- Dedup: satu kirim per kombinasi (host, check, status) dalam jendela
  `dedup_seconds`; state di `state_file` agar berlaku antar eksekusi scheduler.
  State hanya dicatat saat sukses → alert yang gagal dicoba lagi eksekusi
  berikutnya.
- Retry: `retry_max` percobaan ulang dengan jeda singkat; kegagalan = warning.

## Testing

```bash
.venv/bin/pytest monitor/tests                 # unit test (deterministik, mock, tanpa internet)
.venv/bin/pytest monitor/tests -m integration  # integration lokal (butuh demo-http aktif)
.venv/bin/ruff check monitor/monitor_lab monitor/tests
```

Unit test memakai fake adapters (tanpa VM/internet/secret) dan mencakup:
kondisi sehat, disk melewati ambang, service inactive/failed/missing,
DNS gagal & timeout, TCP refused & timeout, HTTP non-2xx & refused &
timeout & host tidak dikenal, konfigurasi tidak valid (termasuk bool untuk
angka, port 0, warn≥crit, unit ber-spasi), platform tidak mendukung,
kegagalan notifikasi (hasil health tetap utuh), dedup & retry, exit code,
dan skema JSON.

## Scheduler (Ubuntu VM — systemd timer)

Setelah `lab-monitor` ter-install di `.venv` dan `monitor/config.json` ada:

```bash
sudo cp monitor/scheduler/lab-monitor.service monitor/scheduler/lab-monitor.timer /etc/systemd/system/
sudo sed -i "s|@@REPO_DIR@@|$HOME/it-operations-ai-lab|; s|@@SERVICE_USER@@|labadmin|" \
  /etc/systemd/system/lab-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable --now lab-monitor.timer
systemctl list-timers lab-monitor.timer          # verifikasi jadwal
sudo systemctl start lab-monitor.service         # trigger manual sekali
journalctl -u lab-monitor.service -n 20          # lihat hasil eksekusi
```

Timer: `OnBootSec=2min`, `OnUnitActiveSec=5min`, `Persistent=true`.
Unit template diverifikasi dengan `systemd-analyze verify` (bukti E42);
eksekusi periodik di VM = requires manual verification.

## Integrasi Homelab (alur wajib)

Alur terdokumentasi dengan bukti aktual di `docs/evidence/E41`:
baseline sehat (monitor exit 0) → gangguan terkontrol
(`simulate_service_down.sh`) → monitor mendeteksi (exit 1, detail
`status=inactive`) → perbaikan manual (`recover_service.sh`) → monitor exit 0.

## Keputusan teknis & trade-off

- **Stdlib-only runtime**: mudah diaudit & di-install di VM minimal; kosong
  dari fitur seperti prometheus-exporter (disengaja, MVP).
- **DNS via getaddrinfo + guard timeout thread**: resolver sistem bisa
  blocking tanpa timeout — guard thread membatasi durasi check (thread yang
  masih hidup bersifat daemon, tidak menahan proses keluar).
- **TCP/HTTP sebagai konektivitas utama**; tidak ada ICMP (sesuai desain).
- **`unknown` ≠ `fail` secara label, sama-sama exit 1**: exception tak terduga
  tidak boleh dianggap sehat.
- **Webhook URL via env, bukan config**: mencegah secret masuk git.
- **Percent disk via `shutil.disk_usage`**: bisa berbeda tipis dari `df -P`
  (df menghitung reserved blocks) — dinyatakan eksplisit.

## Keterbatasan

- MVP tanpa dashboard, tanpa auto-remediation, tanpa notifikasi email/IM.
- Dedup bersifat per-host lokal (state file), bukan alert-manager pusat.
- Check service hanya systemd (platform lain → `unsupported`).
