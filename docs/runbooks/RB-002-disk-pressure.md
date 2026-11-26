# RB-002 — Runbook: kapasitas disk melewati ambang

Versi operasional cepat. Studi kasus lengkap: `docs/incidents/INC-002-disk-pressure.md`.

## Pemicu

`baseline.sh` exit 1 dengan `[FAIL] disk: <path> terpakai N% >= CRIT x%`
(monitor Fase 2 menghasilkan pola setara pada check `disk`).

## Dampak

Tergantung filesystem: root fs penuh bisa menghentikan service, log, dan
database. Pada lab: fixture disposable 32 MB — dampak nol, fokusnya latihan
prosedur.

## Lima menit pertama (triage)

| # | Perintah | Tujuan |
|---|---|---|
| 1 | `df -hP <path>` | Konfirmasi filesystem mana yang penuh dan seberapa parah |
| 2 | `df -iP <path>` | Bedakan kapasitas byte vs inode habis |
| 3 | `du -xsh /* 2>/dev/null \| sort -h` (lalu turun per level) | Temukan direktori terbesar (`-x` agar tidak keluar filesystem) |
| 4 | `ls -lhS <dir>` | Identifikasi file terbesar di direktori tersebut |

## Penyebab umum & tindakan

| Penyebab | Tindakan aman |
|---|---|
| Log tumbuh tanpa rotasi | pangkas dengan `truncate -s 0 <log>` **setelah** cek aplikasi; pasang logrotate |
| File/tmp/backup tua | hapus sesuai kebijakan data; jangan hapus file yang sedang dibuka proses (cek `lsof +L1`) |
| Core dump / crash artifact | hapus setelah dianalisis; matikan generator core bila tak dipakai |
| Kapasitas memang kurang | eskalasi: tambah disk/kuota — keputusan dengan pemilik sistem |
| Inode habis (bukan byte) | cari direktori dengan jutaan file kecil (`df -i`, `find ... \| wc -l`) |

## Setelah pemulihan

1. `bash lab/scripts/baseline.sh` (atau monitor) → exit 0.
2. Catat file yang dihapus/pindahkan (audit trail) — jangan hapus tanpa catat.

## Rollback

- Fixture lab: `sudo lab/scripts/recover_disk_pressure.sh --teardown`.
- Kasus nyata di VM: revert snapshot bila perubahan meragukan.

## Pencegahan

- Ambang WARN lebih rendah dari CRIT (lihat `DISK_WARN`/`DISK_CRIT` di baseline).
- Rotasi log + pembersihan terjadwal; monitoring berkala (Fase 2).
