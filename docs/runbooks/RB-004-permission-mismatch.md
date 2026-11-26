# RB-004 — Runbook: permission file salah

Versi operasional cepat. Studi kasus lengkap: `docs/incidents/INC-004-permission-mismatch.md`.

## Pemicu

Unit tidak aktif dengan journald `Permission denied` / `Errno 13` saat
membaca file aplikasi; sering muncul **setelah restart/deploy**, padahal
layanan sebelumnya berjalan normal.

## Dampak

Layanan gagal start dan terus gagal (atau auto-restart tanpa henti) sampai
permission diperbaiki.

## Lima menit pertama (triage)

| # | Perintah | Tujuan |
|---|---|---|
| 1 | `systemctl status <unit> --no-pager -l` | State unit + exit code proses (status=2 indikatif "can't open file") |
| 2 | `sudo journalctl -u <unit> --no-pager -n 40` | Error asli: `Errno 13 Permission denied` vs `Errno 98 Address already in use` |
| 3 | `stat -c '%a %U:%G %n' <file aplikasi>` | Mode/owner aktual vs yang diharapkan dari installer |
| 4 | `sudo -u <user layanan> head -1 <file>` | Reproduksi akses dari perspektif user layanan |

## Penyebab umum & tindakan

| Penyebab | Tindakan aman |
|---|---|
| chmod terlalu ketat (mis. 000/600) | kembalikan mode sesuai installer (`0755` untuk file lab) |
| owner/group salah | `chown` sesuai installer; cek `systemctl cat <unit>` untuk `User=` |
| umask instalasi salah | pasang ulang via installer (sumber kebenaran), jangan patch manual |
| direktori induk tidak bisa dilewati | cek mode setiap komponen path (`namei -l <file>`) |

## Setelah pemulihan

`bash lab/scripts/baseline.sh` → exit 0 (atau monitor Fase 2 sehat).
Catat mode/owner sebelum dan sesudah (audit trail).

## Rollback

- Perubahan permission = mengembalikan ke nilai installer; bila ragu,
  `sudo lab/scripts/uninstall_demo_service.sh` + install ulang.

## Pencegahan

- Jangan `chmod -R` manual pada direktori aplikasi; semua perubahan via
  installer/version control.
- Snapshot sebelum eksperimen permission.
- (Fase 2, planned) check mode file kritis di monitor.
