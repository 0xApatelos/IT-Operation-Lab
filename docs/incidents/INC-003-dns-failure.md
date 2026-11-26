# INC-003 — Resolusi DNS gagal

| Field | Nilai |
|---|---|
| ID | INC-003 |
| Judul | Resolusi DNS gagal (name resolution drill) |
| Status | implemented + tested di sandbox (Level A) · Level B requires manual verification di VM |

## 1. ID dan judul

Drill "resolusi DNS gagal": baseline dijalankan dengan target DNS yang tidak
dapat diselesaikan, gejala diamati, diagnosis memisahkan "resolver rusak"
vs "nama/target salah", lalu baseline pulih dengan target normal.

## 2. Tujuan pembelajaran

- Memahami cara baseline memeriksa resolusi (`getent` memakai mekanisme
  resolusi sistem: nsswitch → resolv.conf).
- Membedakan dua hipotesis DNS: resolver bermasalah (SEMUA nama gagal) vs
  nama/target salah atau record hilang (hanya satu gagal).
- Mengenali exit code `getent` (2 = name/service not known).

## 3. Prasyarat dan ruang lingkup

- `baseline.sh` tersedia; `demo-http` aktif.
- Ruang lingkup: **tanpa perubahan konfigurasi resolver**. Yang disimulasikan
  adalah **kegagalan resolusi untuk satu nama** (`nonexistent.invalid`,
  TLD `.invalid` dijamin tidak valid oleh RFC 6761).

## 4. Risiko dan langkah keselamatan

- Level A (dilakukan): risiko nol terhadap konfigurasi — hanya membaca.
- Level B (rencana, di VM): memutus resolver sementara dengan mengubah
  resolv.conf/netplan di **VM disposable** — wajib snapshot sebelum, rollback
  sesudah, dan akses konsol tersedia. **Tidak dilakukan di host utama.**

## 5. Kondisi normal

Bukti: `E20-inc003-baseline-pulih.txt` — `dns: archive.ubuntu.com -> ...`,
baseline 5/5 sehat, exit 0.

## 6. Cara menyimulasikan masalah

```bash
DNS_HOST=nonexistent.invalid bash lab/scripts/baseline.sh
```

(Level A. Level B: di VM disposable, arahkan nameserver ke alamat yang tidak
menjawab, mis. `192.0.2.1` dari blok dokumentasi TEST-NET-1, lalu `netplan
apply`; rollback via snapshot.)

## 7. Gejala yang diamati

Bukti: `E18-inc003-gejala-dns-gagal.txt` — satu faktor gagal, exit 1:

```text
[FAIL] dns: resolusi nonexistent.invalid gagal
```

Check lain tetap OK — insiden bersifat satu faktor.

## 8. Hipotesis

H1: nama/target tidak ada atau salah (cocok: hanya satu nama gagal).
H2: resolver down/konfigurasi rusak — **tidak cocok** karena nama umum tetap
terselesaikan; dapat dibuktikan dengan perbandingan di E19.
H3: jalur keluar ke DNS terputus — tidak cocok dengan bukti yang sama.

## 9. Perintah diagnostik dan alasannya

| Perintah | Alasan |
|---|---|
| `getent hosts nonexistent.invalid ; echo $?` | Mekanisme resolusi sistem; rc=2 = name/service not known |
| `getent hosts archive.ubuntu.com ; echo $?` | Pembanding: memisahkan "resolver rusak" vs "nama salah" |
| `resolvectl status` / `cat /etc/resolv.conf` | (Level B / VM) melihat resolver aktif — tidak dijalankan di sandbox karena tidak mengubah apa pun |

Bukti: `E19-inc003-diagnostik-getent.txt` — nama simulasi rc=2 (tanpa output),
nama umum rc=0 (9 alamat IPv6) → resolver bekerja, nama yang gagal memang
tidak ada. Hipotesis H1 terkonfirmasi.

## 10. Hasil observasi aktual

Dari E19: `getent hosts nonexistent.invalid` → tanpa output, rc=2;
`getent hosts archive.ubuntu.com` → 9 alamat, rc=0.

## 11. Root cause

Nama `nonexistent.invalid` sengaja dipakai sebagai kondisi sintetis yang
memang tidak dapat diselesaikan. Pola nyata yang dilatih: record DNS hilang
(satu nama gagal, resolver sehat) — bedakan dengan resolver down (semua nama
gagal) sebelum menyentuh konfigurasi.

## 12. Perbaikan

Kembalikan target ke nama yang benar (di drill: jalankan baseline dengan
`DNS_HOST` default):

```bash
bash lab/scripts/baseline.sh
```

(Pada kasus nyata: perbaiki record di authoritative DNS atau koreksi nama di
konfigurasi klien.)

## 13. Verifikasi sesudah perbaikan

Bukti: `E20-inc003-baseline-pulih.txt` — baseline 5/5 sehat, exit 0.

## 14. Rollback

Level A tidak mengubah apa pun (tidak ada rollback yang diperlukan).
Level B: revert snapshot VM `02-lab-ready`.

## 15. Pencegahan

- Monitoring terjadwal (Fase 2: check DNS di `monitor/`) dengan beberapa
  hostname penting, bukan satu.
- Dokumentasikan resolver yang diharapkan (mis. DNS internal lab) agar
  diagnosis cepat.

## 16. Bukti

| Bukti | Isi | Hasil |
|---|---|---|
| `E18` | gejala: resolusi nama `.invalid` gagal | exit 1, dns FAIL |
| `E19` | diagnostik perbandingan dua nama | rc=2 vs rc=0 → nama salah, resolver sehat |
| `E20` | baseline pulih | exit 0, 5/5 |

## 17. Batas metode (kejujuran eksperimen)

Level A **tidak** menyimulasikan kerusakan resolver — hanya kegagalan
resolusi satu nama. Kesimpulan dari drill ini berlaku untuk pola "nama tidak
ada/target salah". Pola "resolver down" (Level B) memerlukan VM disposable
dan berstatus `requires manual verification` — jangan disimpulkan dari Level A.
