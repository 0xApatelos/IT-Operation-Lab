# RB-005 — Runbook: konflik port layanan

Versi operasional cepat. Studi kasus lengkap: `docs/incidents/INC-005-port-conflict.md`.

## Pemicu

- Unit tidak aktif dengan journald `OSError: [Errno 98] Address already in
  use` (bind gagal).
- **Awas:** tcp/http ke port bisa TETAP OK karena proses lain yang menempati
  port ikut menjawab — cek selalu service-level, bukan hanya port.

## Dampak

Layanan terkelola tidak pernah aktif (auto-restart tanpa henti atau
start-limit); lalu lintas dilayani oleh proses yang bukan unit systemd.

## Lima menit pertama (triage)

| # | Perintah | Tujuan |
|---|---|---|
| 1 | `sudo journalctl -u <unit> --no-pager -n 30` | Konfirmasi penyebab bind: `Errno 98` |
| 2 | `sudo ss -ltnp '( sport = :8080 )'` | PID/proses pemilik port (butuh root) |
| 3 | `tr '\0' ' ' < /proc/<pid>/cmdline` | Identifikasi proses pemilik port |
| 4 | `systemctl show -p MainPID <unit>` | Pembanding: main PID unit vs pemilik port |

## Penyebab umum & tindakan

| Penyebab | Tindakan aman |
|---|---|
| Instance liar/duplikat (deploy ganda, jalankan manual) | hentikan instance liar **setelah verifikasi identitas** (cmdline), lalu start unit |
| Proses orphan pasca-crash | sama seperti di atas; perbaiki supaya selalu start via systemd |
| Layanan lain memang butuh port itu | pindahkan salah satu ke port lain (keputusan sadar, ubah unit + konfigurasi monitor) |
| Socket lama di TIME_WAIT | jarang untuk listener; tunggu/cek `ss -tan` bila pola aneh |

**Jangan** kill proses tanpa verifikasi identitas. Di lab, gunakan
`recover_service_port.sh` yang memverifikasi cmdline sebelum kill.

## Setelah pemulihan

1. `bash lab/scripts/baseline.sh` → exit 0.
2. Verifikasi tidak ada proses liar tersisa (di lab: E33 memakai filter
   `comm=python3`, bukan `pgrep -f` bebas — lihat gotcha di INC-005 §17).

## Rollback

- Skrip pemulihan idempoten; bila pemilik port proses tak dikenal →
  identifikasi dulu, jangan kill sembarangan.

## Pencegahan

- Satu cara menjalankan layanan: systemd unit. Dilarang jalankan manual
  `python3 demo_http_server.py` di server.
- (Fase 2, planned) monitor service-level + identitas proses.
