# RB-003 — Runbook: resolusi DNS gagal

Versi operasional cepat. Studi kasus lengkap: `docs/incidents/INC-003-dns-failure.md`.

## Pemicu

`baseline.sh` exit 1 dengan `[FAIL] dns: resolusi <host> gagal`
(monitor Fase 2 menghasilkan pola setara pada check `dns`).

## Dampak

Dependen: apt update gagal, service yang memvalidasi hostname bisa down,
koneksi keluar berbasis nama tidak berfungsi. Koneksi by-IP tetap bisa.

## Lima menit pertama (triage)

| # | Perintah | Tujuan |
|---|---|---|
| 1 | `getent hosts <host> ; echo $?` | rc=2 = nama tidak dikenal; rc tanpa output lain = indikasi lain |
| 2 | `getent hosts <host-pembanding-yang-umum> ; echo $?` | Memisahkan "resolver rusak" (semua gagal) vs "nama salah" (satu gagal) |
| 3 | `cat /etc/resolv.conf` (VM: `resolvectl status`) | Resolver aktif & nameserver yang dipakai |
| 4 | uji by-IP: `curl -m 5 -I http://127.0.0.1:8080/health` | Konfirmasi masalah terbatas pada nama, bukan jaringan |

## Penyebab umum & tindakan

| Penyebab | Tindakan aman |
|---|---|
| Nama/record salah atau hilang | koreksi nama di konfigurasi; perbaiki record di DNS authoritative |
| Nameserver tidak dijawab | cek jalur ke nameserver (firewall/route); pakai nameserver cadangan |
| resolv.conf tertimpa (mis. salah netplan) | perbaiki konfigurasi sumber (netplan) lalu `netplan apply` |
| Cache DNS membeku | restart resolver lokal (`resolvectl flush-caches`) |

**Jangan** mengubah resolver di host utama Windows/Hypervisor. Perubahan
resolver hanya di VM disposable dengan snapshot.

## Setelah pemulihan

`bash lab/scripts/baseline.sh` → exit 0 (check DNS OK).

## Rollback

- Drill Level A: tidak ada perubahan (hanya membaca).
- Level B di VM: revert snapshot `02-lab-ready`.

## Pencegahan

- Monitor beberapa hostname penting sekaligus (Fase 2).
- Konfigurasi resolver terversi (netplan, bukan edit manual yang bisa tertimpa).
