# INC-004 — Permission file salah

| Field | Nilai |
|---|---|
| ID | INC-004 |
| Judul | Permission file aplikasi lab salah (chmod drill) |
| Status | implemented + tested di sandbox · requires manual verification di VM |

## 1. ID dan judul

Drill "permission file salah": mode file aplikasi lab diubah ke `000`,
restart layanan gagal, gejala diamati, root cause dilacak dari journald
sampai `stat`, lalu dipulihkan.

## 2. Tujuan pembelajaran

- Membaca signature kegagalan "gagal start setelah restart" di systemd.
- Menghubungkan error proses (`Errno 13 Permission denied`) dengan mode file
  (`stat`/`ls -l`).
- Memahami bahwa proses yang SUDAH berjalan tidak langsung terpengaruh
  perubahan permission — kegagalan muncul saat restart/deploy.
- Menyadari bahwa gejala identik dengan INC-001 bisa berakar penyebab beda.

## 3. Prasyarat dan ruang lingkup

- `demo-http` ter-install (mode file 0755 dari installer); baseline sehat.
- Ruang lingkup: **hanya mode file** `/opt/demo-http/demo_http_server.py`
  (path diperbaiki di kode). Tidak ada permission file sistem yang disentuh.

## 4. Risiko dan langkah keselamatan

- File lab-only; mode yang benar diketahui (0755, dari installer) sehingga
  pemulihan deterministik.
- Skrip menolak bila mode awal bukan 755 (menghindari menumpuk kondisi salah)
  dan bila path ter-resolve di luar instalasi lab.
- Tanpa root: ditolak (exit 2 dengan pesan penggunaan).

## 5. Kondisi normal

Bukti: `E21-inc004-baseline-sehat.txt` — baseline 5/5 exit 0; mode file
`755 root:root`. Konteks jujur: sandbox direstart antar sesi sehingga
`demo-http` di-install ulang sebagai langkah setup lab (tercatat di E21).

## 6. Cara menyimulasikan masalah

```bash
sudo lab/scripts/simulate_service_permission.sh --yes
```

Skrip melakukan `chmod 000` lalu `systemctl restart demo-http` (restart =
operasi normal seperti deploy yang menemukan masalah). Tanpa `--yes`,
skrip meminta konfirmasi interaktif.

## 7. Gejala yang diamati

Bukti: `E23-inc004-gejala-baseline-gagal.txt` — exit 1, tiga check gagal:

```text
[FAIL] service: demo-http status=failed (diharapkan active)
[FAIL] tcp: 127.0.0.1:8080 gagal (refused/timeout/port tertutup)
[FAIL] http: koneksi ditolak ke http://127.0.0.1:8080/health (curl rc=7)
```

Pola gejala identik dengan INC-001 (layanan mati → port tertutup → HTTP
ditolak) — bagus untuk melatih bahwa diagnosis tidak berhenti di gejala.

## 8. Hipotesis

H1: unit gagal start karena file aplikasi tidak dapat dibaca/dieksekusi
(permission) — cocok dengan bukti journald (E24).
H2: bug aplikasi baru — tidak cocok (tidak ada perubahan kode; hanya mode file).
H3: port bentrok — tidak cocok (journald menunjukkan Permission denied, bukan
`Address already in use`; pembeda antara H1 dan H3 ada di journald).

## 9. Perintah diagnostik dan alasannya

| Perintah | Alasan |
|---|---|
| `systemctl status demo-http --no-pager -l` | Kondisi unit (`failed`), exit code proses (`status=2`), ExecStart |
| `sudo journalctl -u demo-http --no-pager -n 40` | Error proses asli + pola retry (butuh root; log unit sistem) |
| `stat -c '%a %U:%G %n' <file>` / `ls -l /opt/demo-http/` | Mengonfirmasi mode file sebagai penyebab |

Bukti: `E24-inc004-diagnostik-permission.txt` — `Active: failed (Result:
exit-code)`, `Main PID ... (code=exited, status=2)`, dan berulang kali:
`python3: can't open file '/opt/demo-http/demo_http_server.py': [Errno 13]
Permission denied` tiap ±2 detik (siklus `Restart=on-failure`), lalu
`stat` menunjukkan mode `000`.

## 10. Hasil observasi aktual

Dari E24: unit `failed`; python keluar status 2 dengan `[Errno 13] Permission
denied`; retry otomatis tiap ±2 detik sampai start-limit; mode file `000`.

## 11. Root cause

Mode file diubah ke `000` (sengaja disimulasikan). Pola nyata yang dilatih:
hardening/umask/owner yang salah membuat file tidak terbaca oleh user layanan
(`demo-http`), sehingga setiap start/restart gagal — sementara instansi yang
sudah berjalan tetap hidup sampai restart pertama.

## 12. Perbaikan

```bash
sudo lab/scripts/recover_service_permission.sh
```

(`chmod 755` + `systemctl reset-failed` + `systemctl start` + verifikasi
end-to-end service aktif DAN `/health` 200.)

## 13. Verifikasi sesudah perbaikan

Bukti: `E25-inc004-pemulihan.txt` — mode kembali `755 root:root`, pemulihan
terverifikasi (active + 200); `E26-inc004-baseline-pulih.txt` — baseline 5/5,
exit 0, mode `755`.

## 14. Rollback

- Perbaikan = mengembalikan mode ke nilai installer (0755); tidak ada
  perubahan lain. Bila ragu: `uninstall_demo_service.sh` lalu install ulang
  (installer adalah sumber kebenaran mode/owner).

## 15. Pencegahan

- Perlakukan installer sebagai sumber kebenaran: jangan `chmod` manual pada
  `/opt/demo-http/` di luar installer.
- Hindari `chmod -R` eksperimental pada direktori aplikasi; snapshot sebelum
  eksperimen permission.
- (Fase 2, planned) check mode/owner file kritis pada monitor.

## 16. Bukti

| Bukti | Isi | Hasil |
|---|---|---|
| `E21` | baseline sehat + mode 755 (+ konteks reinstall) | exit 0 |
| `E22` | simulasi chmod 000 + restart | unit `failed` |
| `E23` | gejala tiga-lapis | exit 1 |
| `E24` | diagnostik status/journald/stat | `Errno 13`, `status=2`, mode 000 |
| `E25` | pemulihan (chmod 755 + start) | terverifikasi |
| `E26` | baseline pulih + mode 755 | exit 0 |

## 17. Catatan analisis (untuk portofolio)

- **Gejala sama, akar beda:** gejala INC-004 identik dengan INC-001
  (service/tcp/http gagal), tetapi journald memisahkan keduanya dalam hitungan
  detik (`Permission denied` vs `Deactivated successfully`). Pelajaran:
  perbaiki penyebab, bukan gejala.
- **Detail signature:** python keluar `status=2` untuk "can't open file" dan
  systemd melabelinya `2/INVALIDARGUMENT` — angka status proses tidak selalu
  intuitif; baca pesan error prosesnya, bukan hanya angkanya.
- **Perilaku restart policy:** kegagalan exit instan (python gagal sebelum
  import apa pun) memicu start-limit dalam ~9 detik (state `failed`). Kontras
  dengan INC-005 yang gagal sedikit lebih lambat (bind) dan tidak pernah
  mencapai start-limit — dianalisis lebih lanjut di INC-005 §17.
