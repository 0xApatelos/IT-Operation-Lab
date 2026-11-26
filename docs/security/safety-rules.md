# Keamanan & keselamatan lab

Dokumen ini mendefinisikan batas kepercayaan jaringan, aturan keselamatan
saat menyimulasikan insiden, konvensi label bukti, dan kebijakan secret.

## 1. Batas kepercayaan jaringan

| Zona | Isi | Kepercayaan |
|---|---|---|
| Windows host | VMware Workstation, kredensial pribadi Anda | Terpercaya (milik Anda) |
| VMnet1 (host-only) | Host + VM server, trafik HTTP :8080 dan SSH :22 | Lab-only — dianggap tepercaya **hanya** untuk latihan; jangan simpan data nyata di layanan lab |
| VMnet8 (NAT) | Arah keluar dari VM ke internet (apt update, DNS) | Internet publik — tidak ada inbound |
| Internet | — | Tidak tepercaya |

Aturan jaringan:

- **Tidak ada port-forwarding inbound** dari host/internet ke VM.
- Layanan lab bind ke `0.0.0.0` **hanya agar bisa dicapai host lewat VMnet1**;
  jangan ubah ke adapter bridged.
- Semua alamat IP dalam dokumentasi ini adalah **CONTOH**. Alamat aktual di VM
  Anda bisa berbeda — verifikasi dengan `ip -br a` (VM) dan `ipconfig`
  (Windows, lihat adapter VMware Network Adapter VMnet1).
- Simulasi gangguan jaringan hanya dilakukan di dalam VM yang disposable,
  setelah snapshot tersedia dan akses konsol (bukan hanya SSH) terbuka.

## 2. Aturan keselamatan simulasi insiden

1. **Jangan pernah mengisi filesystem root** untuk simulasi disk penuh —
   gunakan filesystem disposable berukuran terbatas (tmpfs/loop) atau fixture.
2. **Jangan mengubah DNS, firewall, permission, atau layanan host utama**
   Windows. Semua gangguan hanya di dalam VM lab atau pada layanan lab
   (`demo-http`).
3. **Jangan memutus akses SSH yang sedang dipakai** — skrip simulasi hanya
   menyentuh `demo-http`, bukan `ssh`.
4. **Sediakan akses konsol** (VMware console window) sebelum simulasi apa pun,
   sehingga gangguan jaringan tidak mengunci Anda keluar.
5. **Snapshot sebelum gangguan**: VMware Snapshot Manager, nama tersaran
   `02-lab-ready` (lihat docs/setup/).
6. **Beri peringatan sebelum langkah yang mengubah state** — skrip lab
   melakukan ini (`[PERINGATAN]`, konfirmasi `--yes` atau prompt).
7. Guard eksplisit di kode: `simulate_service_down.sh` dan
   `recover_service.sh` **menolak** layanan selain `demo-http`.
8. Tidak ada auto-remediation di seluruh repo: pemulihan selalu manual dan
   terverifikasi.

## 3. Konvensi label bukti

Lihat `docs/evidence/README.md`. Ringkas:

- `AKTUAL` = output mentah eksekusi nyata (dengan lingkungan dicatat).
- `CONTOH` = output sintetis untuk ilustrasi, selalu ditandai.
- Status pekerjaan: `implemented`, `tested`, `simulated` (drill terkontrol),
  `requires manual verification`, `planned` — dipakai konsisten di README dan
  dokumen insiden.

## 4. Kebijakan secret

- Tidak ada secret dalam source code, frontend, contoh log, atau dokumentasi.
- File `.env` ada di `.gitignore`; hanya `.env.example` berisi placeholder
  yang boleh di-commit (dipakai mulai Fase 2 untuk webhook/token).
- Token/URL webhook hanya dari environment variable, tidak pernah hard-coded.
- Portofolio ini memakai **data sintetis** — tidak ada tiket helpdesk nyata,
  percakapan pribadi, atau data organisasi lain.

## 5. Kebijakan akun & hak akses

- Layanan lab berjalan sebagai user sistem khusus `demo-http` (tanpa shell,
  tanpa home) dengan hardening systemd ringan (`NoNewPrivileges`,
  `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`).
- Skrip operasional yang mengubah state (`install`, `simulate`, `recover`,
  `uninstall`) meminta root secara eksplisit dan menolak berjalan tanpa `sudo`
  — kecuali `baseline.sh` yang sengaja tidak butuh root.
