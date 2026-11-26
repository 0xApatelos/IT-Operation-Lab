# INC-002 — Kapasitas disk melewati ambang

| Field | Nilai |
|---|---|
| ID | INC-002 |
| Judul | Kapasitas disk melewati ambang (disk pressure drill) |
| Status | implemented + tested di sandbox · requires manual verification di VM |

## 1. ID dan judul

Drill terkontrol "disk penuh": mengisi **filesystem disposable** (tmpfs 32 MB)
sampai melewati ambang kritis, mengamati deteksi baseline, mendiagnosis,
memulihkan, dan membongkar fixture.

## 2. Tujuan pembelajaran

- Membaca `df -P` (per filesystem) dan memakai `du`/`ls` untuk menemukan
  penyebab pemakaian disk.
- Memahami ambang WARN vs CRIT dan bedanya (WARN tidak membuat exit 1).
- Mempraktikkan simulasi disk yang **aman**: fixture terbatas, bukan root fs.
- Memahami karakter tmpfs: hidup di RAM, hilang saat unmount/reboot.

## 3. Prasyarat dan ruang lingkup

- `baseline.sh` tersedia; `demo-http` terpasang (supaya baseline memuat 5 check).
- Ruang lingkup: **hanya** `/mnt/lab-disk-fixture` (path diperbaiki di kode,
  tidak bisa diarahkan ke path lain). Root fs tidak tersentuh.

## 4. Risiko dan langkah keselamatan

- **Tidak pernah mengisi filesystem root** — simulasi memakai tmpfs disposable
  berukuran kecil (default 32 MB, maksimum 256 MB) yang hidup di RAM.
- Skrip menolak bila mountpoint sudah terisi oleh mount non-lab atau berisi
  data (guard di `simulate_disk_pressure.sh` dan `recover_disk_pressure.sh`).
- Tidak ada perubahan fstab/unit mount sistem; unmount membalik semuanya.

## 5. Kondisi normal

Bukti: `E11-inc002-baseline-sehat-fixture.txt` — fixture kosong, baseline
5/5 sehat, exit 0. `df -P`: 0% (warn 50, crit 75 — ambang diturunkan agar
dapat diuji pada fixture 32 MB).

## 6. Cara menyimulasikan masalah

```bash
sudo bash lab/scripts/simulate_disk_pressure.sh --yes --mount-only   # siapkan fixture kosong
sudo bash lab/scripts/simulate_disk_pressure.sh --yes                # isi ~90%
```

(`--yes` dipakai karena eksekusi bukti non-interaktif; tanpa itu skrip minta
konfirmasi `ya`.)

## 7. Gejala yang diamati

Bukti: `E13-inc002-gejala-baseline-gagal.txt` — satu faktor gagal, exit 1:

```text
[FAIL] disk: /mnt/lab-disk-fixture terpakai 88% >= CRIT 75%
```

Check lain tetap OK (service, DNS, TCP, HTTP) — insiden bersifat satu faktor.

## 8. Hipotesis

H1: file besar/penumpukan file di filesystem terkait (paling mungkin).
H2: filesystem terlalu kecil untuk beban normal — tidak cocok karena pemakaian
melonjak mendadak dari 0%.
H3: inode habis (bukan kapasitas byte) — tidak cocok untuk kasus ini karena
df menunjukkan persentase kapasitas byte; dapat diperiksa dengan `df -i`.

## 9. Perintah diagnostik dan alasannya

| Perintah | Alasan |
|---|---|
| `df -h /mnt/lab-disk-fixture` | Kapasitas & pemakaian per filesystem (konfirmasi melewati ambang) |
| `du -sh /mnt/lab-disk-fixture/*` | Mengungkap direktori/file terbesar di dalamnya |
| `ls -lh /mnt/lab-disk-fixture` | Mengonfirmasi nama & ukuran file penyebab |
| `df -i /mnt/lab-disk-fixture` | (opsional) membedakan hipotesis inode vs byte |

Bukti: `E14-inc002-diagnostik-disk.txt` — `du` menunjuk
`lab-fill.bin` 28 MB sebagai penyebab.

## 10. Hasil observasi aktual

Dari E14: `tmpfs 32M 28M 4.0M 88% /mnt/lab-disk-fixture`; file penyebab
`lab-fill.bin` 28M (root-owned, dibuat dd oleh skrip simulasi).

## 11. Root cause

File `lab-fill.bin` sengaja dibuat skrip simulasi (28 MB = 90% dari 32 MB)
sebagai pengganti pola nyata: log/backup/queue yang tumbuh tanpa rotasi atau
pembersihan. Drill ini melatih deteksi ambang dan penelusuran penyebab,
bukan penyebab teknisnya.

## 12. Perbaikan

```bash
sudo bash lab/scripts/recover_disk_pressure.sh     # hapus lab-fill.bin
```

(Pada kasus nyata: pindahkan/hapus/pangkas file besar sesuai kebijakan data,
atau tambah kapasitas — di luar ruang lingkup drill.)

## 13. Verifikasi sesudah perbaikan

Bukti: `E16-inc002-baseline-pulih.txt` — disk 0%, baseline 5/5 sehat, exit 0.

## 14. Rollback

- `sudo bash lab/scripts/recover_disk_pressure.sh --teardown` — unmount fixture
  dan hapus mountpoint (bukti: `E17-inc002-teardown-fixture.txt`).
- Data di tmpfs hilang saat unmount/reboot; tidak ada jejak di disk.

## 15. Pencegahan

- Monitoring terjadwal dengan ambang WARN lebih rendah (mis. 80%) agar ada
  waktu bereaksi sebelum CRIT (Fase 2: `monitor/` + scheduler).
- Rotasi log (logrotate) dan kuota untuk direktori yang tumbuh.

## 16. Bukti

| Bukti | Isi | Hasil |
|---|---|---|
| `E10` | mount fixture 32 MB kosong | df 0% |
| `E11` | baseline sehat pada fixture kosong | exit 0, 5/5 |
| `E12` | isi fixture ~90% | df 88% |
| `E13` | gejala satu-faktor | exit 1, disk FAIL |
| `E14` | diagnostik df/du/ls | `lab-fill.bin` 28 MB |
| `E15` | pemulihan (hapus file) | df 0% |
| `E16` | baseline pulih | exit 0, 5/5 |
| `E17` | teardown fixture | tidak ada mount tersisa |

## 17. Catatan kegagalan proses rekaman (untuk portofolio)

Rekaman pertama `E11` salah prosedur: fixture masih berisi sisa isi `E12`
(88%) sehingga "baseline sehat" yang terekam justru FAIL disk. Koreksi:
fixture di-teardown, di-mount ulang kosong, lalu baseline direkam ulang (5/5,
exit 0) — dengan catatan koreksi eksplisit di header `E11`. Pelajaran:
**kondisi normal harus direkam dari state yang benar-benar bersih**, dan bukti
yang salah tidak dihapus diam-diam melainkan dikoreksi dengan penjelasan.
