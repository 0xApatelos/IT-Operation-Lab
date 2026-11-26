# INC-005 — Konflik port layanan (port 8080 dikuap proses lain)

| Field | Nilai |
|---|---|
| ID | INC-005 |
| Judul | Port layanan diklaim instance liar (port conflict drill) |
| Status | implemented + tested di sandbox · requires manual verification di VM |

## 1. ID dan judul

Drill "port diklaim proses lain": instance lab liar (proses
`demo_http_server.py` yang sama, dijalankan **tanpa** systemd) menempati port
8080, sehingga unit `demo-http` gagal start (bind: `Address already in use`) —
sementara pemeriksaan TCP/HTTP dari luar **tampak sehat**.

## 2. Tujuan pembelajaran

- Membaca signature kegagalan bind (`OSError: [Errno 98] Address already in
  use`) di journald.
- Menggunakan `ss -ltnp` untuk mengidentifikasi pemilik port dan
  `/proc/<pid>/cmdline` untuk mengidentifikasi prosesnya.
- Memahami jebakan **"TCP/HTTP OK ≠ layanan terkelola sehat"**: yang menjawab
  port bisa proses yang salah. Alasan kuat mengapa monitor perlu check
  service-layer, bukan hanya port.
- Kill aman: hanya menghentikan proses yang cmdline-nya terverifikasi.

## 3. Prasyarat dan ruang lingkup

- `demo-http` ter-install; baseline sehat.
- Ruang lingkup: unit `demo-http` dan **squatter lab yang dibuat skrip**
  (proses milik user `demo-http`, PID tercatat di `lab/runtime/`).
  Tidak ada proses host lain yang disentuh.

## 4. Risiko dan langkah keselamatan

- Squatter berjalan sebagai user layanan (bukan root), log di `/tmp`, PID
  tercatat di `lab/runtime/port-squatter.pid` (folder di `.gitignore`).
- Skrip **menolak** memulai simulasi bila port sudah didengarkan proses tak
  dikenal.
- Recover **menolak** kill bila cmdline PID tidak cocok dengan
  `demo_http_server.py`; SIGKILL hanya setelah verifikasi ulang post-SIGTERM.
- Recover menghentikan siklus auto-restart unit **sebelum** kill (menghindari
  race: unit self-heal memperebutkan port).

## 5. Kondisi normal

Bukti: `E27-inc005-baseline-sehat.txt` — baseline 5/5 exit 0; `ss -ltnp`
menunjukkan port 8080 didengarkan proses python3 milik unit; unit `active`.

## 6. Cara menyimulasikan masalah

```bash
sudo lab/scripts/simulate_port_conflict.sh --yes
```

Skrip: stop unit → jalankan squatter (PID tercatat) → verifikasi squatter
mendengarkan → `systemctl start demo-http` (gagal bind) → tunggu unit tidak
aktif. Tanpa `--yes`, minta konfirmasi interaktif.

## 7. Gejala yang diamati

Bukti: `E29-inc005-gejala-deceptif.txt` — exit 1 dengan pola yang
**menipu**:

```text
[FAIL] service: demo-http status=activating (diharapkan active)
[OK]   tcp: 127.0.0.1:8080 terhubung
[OK]   http: GET http://127.0.0.1:8080/health -> 200 ...
```

TCP dan HTTP lolos karena **squatter** yang menjawab (instance lab sama ikut
menyajikan `/health`). Hanya check service-level yang menangkap masalah.

## 8. Hipotesis

H1: unit gagal start karena port dipakai proses lain — cocok dengan journald
(E30: `Address already in use`).
H2: binary/kode rusak — tidak cocok (tidak ada perubahan; squatter menjalankan
kode yang sama dengan sukses).
H3: permission — tidak cocok (error bind, bukan `Errno 13`).

## 9. Perintah diagnostik dan alasannya

| Perintah | Alasan |
|---|---|
| `systemctl status demo-http --no-pager -l` | State unit (`activating (auto-restart)`, `status=1/FAILURE`) |
| `sudo journalctl -u demo-http --no-pager -n 30` | Penyebab per percobaan: `OSError: [Errno 98] Address already in use` |
| `sudo ss -ltnp '( sport = :8080 )'` | PID proses pemilik port (butuh root untuk nama proses) |
| `tr '\0' ' ' < /proc/<pid>/cmdline` | Identifikasi proses pemilik port: instance liar vs unit |
| `systemctl show -p MainPID demo-http` | Pembanding: MainPID unit vs PID pemilik port |

Bukti: `E30-inc005-diagnostik-port.txt` — unit `activating (auto-restart)`;
journald menunjukkan traceback berakhir di `OSError: [Errno 98] Address
already in use` per percobaan; pemilik port = PID squatter (cmdline
`python3 -u /opt/demo-http/demo_http_server.py --port 8080`, **bukan** anak
unit systemd).

## 10. Hasil observasi aktual

Dari E30: unit terus mencoba start dan gagal bind; port dipegang PID squatter
yang cmdline-nya terverifikasi sebagai `demo_http_server.py` di luar systemd.
(Perbandingan: INC-001 mematikan layanan juga menghasilkan port tertutup;
di sini port justru TERBUKA oleh proses yang salah.)

## 11. Root cause

Instance duplikat tanpa manajemen (pola nyata: deploy ganda, proses orphan
pasca-crash, jalankan manual lupa systemd) menempati port sebelum unit start.
Unit punya `Restart=on-failure`, sehingga mencoba start terus-menerus dan
tetap tidak aktif.

## 12. Perbaikan

```bash
sudo lab/scripts/recover_service_port.sh
```

Urutan aman: `systemctl stop` (batalkan siklus auto-restart) → verifikasi
cmdline PID squatter → SIGTERM (→ SIGKILL hanya dengan verifikasi ulang) →
cek port bebas → `reset-failed` + `start` → verifikasi end-to-end.

## 13. Verifikasi sesudah perbaikan

Bukti: `E31-inc005-pemulihan.txt` — squatter PID 2643 dihentikan setelah
verifikasi cmdline, port bebas, unit pulih (active + 200);
`E32-inc005-baseline-pulih.txt` — baseline 5/5 exit 0;
`E33-inc005-endstate-bersih.txt` — tepat 1 proses `python3` demo-http (milik
unit), port dipegang unit, artefak runtime bersih.

## 14. Rollback

- Skrip pemulihan idempoten (tanpa PID tercatat → langkah kill dilewati).
- Bila port dipegang proses TIDAK dikenal: jangan kill sembarangan —
  identifikasi dulu (`ss -ltnp` + `/proc/<pid>/cmdline`), eskalasi sesuai
  kebijakan.

## 15. Pencegahan

- Satu sumber kebenaran untuk menjalankan layanan: selalu via systemd unit;
  jangan menjalankan `python3 demo_http_server.py` manual di server.
- (Fase 2, planned) monitor dengan check service-level + identitas proses,
  bukan hanya port/HTTP.
- Snapshot sebelum eksperimen yang memengaruhi layanan.

## 16. Bukti

| Bukti | Isi | Hasil |
|---|---|---|
| `E27` | baseline sehat + pendengar milik unit | exit 0 |
| `E28` | **kegagalan rekaman pertama** (settle logic terlalu sempit) | exit 1 — lihat §17 |
| `E28b` | cleanup terverifikasi + simulasi ulang yang sukses | exit 0, unit tidak aktif |
| `E29` | gejala penipu: service FAIL, tcp/http OK | exit 1 |
| `E30` | diagnostik status/journald/ss/cmdline | `Errno 98`, squatter teridentifikasi |
| `E31` | pemulihan (kill terverifikasi + start) | terverifikasi |
| `E32` | baseline pulih | exit 0 |
| `E33` | end-state bersih (+ pelajaran `pgrep -f`) | tepat 1 proses unit |

## 17. Catatan analisis (untuk portofolio)

- **Kegagalan rekaman pertama (E28):** settle logic menunggu state `failed`,
  tetapi unit terjebak `activating (auto-restart)` tanpa henti. Analisis: di
  bawah `Restart=on-failure`, kegagalan **exit instan** (INC-004: python gagal
  sebelum import, ~9 detik mencapai `StartLimitBurst=5/10s` → state `failed`)
  berbeda signature dari kegagalan **bind** (python selesai import dulu, cycle
  ~2,5 detik → tidak pernah memicu start-limit → `activating` terus). Perbaikan:
  syarat sukses = unit tidak aktif (state apa pun selain `active`) selama ≥3
  poll beruntun + port masih dipegang squatter.
- **Implikasi desain monitor (Fase 2):** state unit bisa `failed` ATAU
  `activating` tanpa henti — keduanya tidak sehat. Check service harus
  `state != "active"` (bukan `== "failed"`), dan check port/HTTP saja dapat
  memberi keyakinan palsu (E29). Ini alasan arsitektur monitor memiliki
  multiple check layers.
- **Gotcha diagnostik (E33):** `pgrep -f <pattern>` mencocokkan seluruh
  cmdline termasuk proses perekaman bukti itu sendiri (false positive 3 vs 1).
  Solusi: filter berdasarkan nama proses (`comm`) — pelajaran nyata untuk
  membuat skrip diagnostik yang andal.
