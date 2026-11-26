# INC-001 — Layanan demo-http berhenti

| Field | Nilai |
|---|---|
| ID | INC-001 |
| Judul | Layanan demo-http berhenti (service stopped drill) |
| Status | implemented + tested di sandbox · requires manual verification di VM |

## 1. ID dan judul

Drill terkontrol "layanan berhenti": menyimulasikan `demo-http` mati,
mengamati gejala, mendiagnosis, memulihkan, dan memverifikasi pemulihan.

## 2. Tujuan pembelajaran

- Menggunakan systemd (`systemctl status/is-active`) dan journald untuk
  diagnosis layanan.
- Menghubungkan gejala dari tiga lapisan yang berbeda: status unit, koneksi
  TCP, dan respons HTTP.
- Memahami hak akses: mengapa `systemctl stop` unit sistem butuh root.
- Mempraktikkan siklus incident: baseline → gangguan → gejala → diagnosis →
  perbaikan → verifikasi.

## 3. Prasyarat dan ruang lingkup

- Lingkungan: VM Ubuntu Server 24.04 LTS per `docs/setup/` (atau host Linux
  dengan systemd untuk latihan). Alur yang sama sudah diuji di sandbox —
  bukti di `docs/evidence/`.
- `demo-http` terpasang via `install_demo_service.sh`; baseline sehat
  (exit 0).
- Ruang lingkup: hanya unit `demo-http`. Tidak menyentuh SSH, DNS, firewall,
  atau layanan lain.

## 4. Risiko dan langkah keselamatan

- Risiko rendah: layanan lab-only, port 8080, tanpa data nyata.
- Skrip simulasi **menolak** layanan selain `demo-http` (guard di kode).
- Simulasi memakai `systemctl stop` (bukan kill -9): bersih, tanpa kerusakan
  state; `Restart=on-failure` tidak menghidupkan ulang stop manual, sehingga
  drill deterministik.
- Jalankan dengan `sudo`; akses konsol VM tersedia sebagai jalur cadangan.

## 5. Kondisi normal

Bukti: `E02-baseline-sehat.txt` — baseline 5/5 sehat, exit 0:

```text
[OK] disk: / terpakai 17% (warn 80% crit 90%)
[OK] service: demo-http active
[OK] dns: archive.ubuntu.com -> ...
[OK] tcp: 127.0.0.1:8080 terhubung
[OK] http: GET http://127.0.0.1:8080/health -> 200 ...
```

## 6. Cara menyimulasikan masalah

```bash
sudo lab/scripts/simulate_service_down.sh --yes
```

Tanpa `--yes`, skrip meminta konfirmasi interaktif. Flag dipakai pada
eksekusi bukti karena non-interaktif.

## 7. Gejala yang diamati

Bukti: `E04-gejala-baseline-gagal.txt` — exit 1, tiga check gagal serentak:

```text
[FAIL] service: demo-http status=inactive (diharapkan active)
[FAIL] tcp: 127.0.0.1:8080 gagal (refused/timeout/port tertutup)
[FAIL] http: koneksi ditolak ke http://127.0.0.1:8080/health (curl rc=7)
```

Dari sisi host: HTTP `:8080` dan `/health` tidak terjangkau. Gejala dari tiga
lapisan (unit/TCP/HTTP) merujuk ke kondisi yang sama.

## 8. Hipotesis

H1: proses demo-http tidak berjalan (paling mungkin — unit `inactive`).
H2: proses berjalan tetapi tidak mendengarkan di 8080 (port bentrok/bind
salah) — tidak cocok karena TCP/HTTP keduanya gagal dan status unit
`inactive`.
H3: masalah jaringan host-only — tidak cocok karena DNS tetap OK dan gagalnya
hanya pada layanan lab.

## 9. Perintah diagnostik dan alasannya

| Perintah | Alasan |
|---|---|
| `systemctl status demo-http --no-pager -l` | Kondisi unit: active/inactive/failed, PID, exit code proses terakhir |
| `sudo journalctl -u demo-http --no-pager -n 30` | Log systemd+aplikasi di sekitar kejadian (mulai/berhenti) |
| `ss -ltn \| grep 8080` | Memastikan tidak ada yang mendengarkan port tersebut |

Bukti: `E05-diagnostik-status.txt` (status `inactive`),
`E06-diagnostik-journalctl.txt` (journald merekam `Stopping...` →
`Deactivated successfully` → `Stopped` — konsisten dengan stop terkontrol).

Catatan akses yang ditemukan: `journalctl` **tanpa sudo** tidak melihat log
unit sistem ("No entries"); log unit sistem butuh root atau grup
`systemd-journal`. Ini dicatat sebagai pembelajaran, bukan sebagai hasil
rekayasa.

## 10. Hasil observasi aktual

Ringkas dari `E05` dan `E06` (output mentah ada di file bukti):

- `systemctl is-active demo-http` → `inactive`.
- journald: `Stopping demo-http.service...`, `Deactivated successfully`,
  `Stopped demo-http.service ...`.
- Port 8080 tak didengarkan (didukung oleh FAIL tcp pada baseline).

## 11. Root cause

Penyebab drill: layanan dihentikan sengaja via `systemctl stop` sebagai
simulasi kegagalan. Pada insiden nyata pola yang sama muncul ketika layanan
dihentikan manual/konfigurasi hilang; unit dengan `Restart=on-failure` tidak
menghidupkan kembali layanan yang di-**stop** (bukan crash) — perbedaan
penting yang dilatih di drill ini.

## 12. Perbaikan

```bash
sudo lab/scripts/recover_service.sh
```

(`systemctl start demo-http` + loop verifikasi service aktif **dan**
`/health` 200, maksimum 15 detik.)

## 13. Verifikasi sesudah perbaikan

Bukti: `E07-pemulihan-recover.txt` — `pemulihan TERVERIFIKASI: service aktif
+ GET /health 200 (percobaan ke-2)`; dan `E08-baseline-sehat-ulang.txt` —
baseline kembali 5/5, exit 0.

## 14. Rollback

- Perbaikan bersifat menambah (start layanan); tidak ada perubahan konfigurasi
  yang perlu dibatalkan.
- Jika unit rusak: `sudo lab/scripts/uninstall_demo_service.sh` lalu install
  ulang; terakhir, revert snapshot `02-lab-ready`.

## 15. Pencegahan

- Pemantauan terjadwal: baseline/monitor dijalankan berkala (Fase 2:
  `monitor/` + scheduler) agar layanan berhenti terdeteksi cepat.
- Snapshot sebelum perubahan unit/konfigurasi.
- Dokumentasi runbook (RB-001) agar pemulihan tidak ditebak.

## 16. Bukti

| Bukti | Isi | Hasil |
|---|---|---|
| `E02` | baseline sebelum | exit 0 |
| `E03` | **kegagalan nyata** percobaan pertama | lihat bagian 17 |
| `E03b` | simulasi dengan sudo | exit 0, layanan inactive |
| `E04` | gejala baseline | exit 1, 3 check gagal |
| `E05`, `E06` | diagnostik status & journald | inactive; stop tercatat |
| `E07` | pemulihan | exit 0, terverifikasi |
| `E08` | baseline sesudah | exit 0 |
| `E09` | teardown | exit 0 |

## 17. Contoh kegagalan nyata saat drill pertama (untuk portofolio)

Percobaan pertama menjalankan `simulate_service_down.sh` **tanpa sudo**.
`systemctl stop` ditolak systemd: `Access denied` (exit 4) — layanan tetap
aktif, baseline tetap exit 0 (bukti: `E03-percobaan-tanpa-sudo-gagal.txt`).

**Analisis:** systemd melindungi unit sistem dari manipulasi user biasa —
perilaku yang benar, bukan bug. Perbaikan: kedua skrip (simulate/recover)
kini menolak berjalan tanpa root (exit 2 + pesan penggunaan yang benar), dan
dokumentasi menyebut `sudo` secara eksplisit. Efek samping positif: kegagalan
ini mendokumentasikan batas hak akses yang nyata, bukan asumsi.
