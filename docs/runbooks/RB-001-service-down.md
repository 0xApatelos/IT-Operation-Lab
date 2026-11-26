# RB-001 — Runbook: layanan demo-http berhenti

Versi operasional cepat (cheat-sheet). Studi kasus lengkap dengan analisis
root cause: `docs/incidents/INC-001-service-down.md`.

## Pemicu

- `baseline.sh` exit 1 dengan `[FAIL] service: demo-http status=inactive`
  dan/atau `[FAIL] tcp/http` ke 127.0.0.1:8080.
- `/health` tidak merespons dari host (`Test-NetConnection ... -Port 8080`
  gagal, CONTOH IP).

## Dampak

Lab-only: layanan latihan tidak dapat diakses. Tidak memengaruhi layanan
lain. Tidak ada urgency produksi.

## Lima menit pertama (triage)

| # | Perintah | Tujuan |
|---|---|---|
| 1 | `systemctl status demo-http --no-pager -l` | Kondisi unit: active/inactive/failed, exit code proses |
| 2 | `sudo journalctl -u demo-http --no-pager -n 50` | Log sebelum/ saat mati (butuh root atau grup `systemd-journal`) |
| 3 | `ss -ltn \| grep 8080` | Apakah port benar-benar tak didengarkan / dipakai proses lain |
| 4 | `curl -i -m 5 http://127.0.0.1:8080/health` | Verifikasi langsung dari dalam VM |

## Penyebab umum & tindakan

| Gejala status | Kemungkinan penyebab | Tindakan |
|---|---|---|
| `inactive` | dihentikan manual (mis. setelah drill) | `sudo lab/scripts/recover_service.sh` |
| `failed` | proses crash (lihat exit code di status) | baca journal → perbaiki penyebab → recover; unit punya `Restart=on-failure` jadi crash berulang berarti penyebab belum hilang |
| unit tidak ditemukan | belum di-install / terhapus | `sudo lab/scripts/install_demo_service.sh` |
| port bentrok | proses lain memakai 8080 | identifikasi via `ss -ltnp` (root); matikan proses lab lain, jangan sentuh proses host |
| python path berubah | upgrade python3 sistem | pasang ulang unit (installer men-template path python3 saat install) |

## Setelah pemulihan

1. `bash lab/scripts/baseline.sh` → **harus exit 0** (bukan cukup "service
   jalan" — verifikasi end-to-end memakai HTTP).
2. Catat waktu, penyebab, dan tindakan (untuk bukti/latihan).

## Eskalasi & rollback

- Jika recover gagal 15 detik: baca `journalctl -u demo-http -n 50`, lalu
  reinstall via installer.
- Terakhir: revert snapshot `02-lab-ready` (lihat `docs/setup/teardown.md`).

## Pencegahan

- Jalankan baseline terjadwal (Fase 2: `monitor/` dengan scheduler) agar
  layanan berhenti terdeteksi segera, bukan saat dipakai.
- Snapshot sebelum setiap perubahan pada unit/service.
