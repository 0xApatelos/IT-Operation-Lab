# Ringkasan Portofolio — untuk recruiter & persiapan wawancara

> Semua klaim di dokumen ini merujuk ke bukti eksekusi nyata di
> `docs/evidence/` (label lingkungan: sandbox Debian 13 + systemd, bukan VM).
> Tidak ada angka dampak bisnis, jumlah pengguna, atau penghematan waktu —
> tidak diukur, tidak dikarang. Status terperinci per fitur: `README.md`.
> Tangkapan layar eksekusi nyata (8 gambar): `docs/screenshots/README.md`.

## Elevator pitch (30 detik)

Repo ini membuktikan dua kompetensi lewat artefak, bukan klaim: lima skenario
insiden Linux yang dibangun–dipatahkan–didagnosis–dipulihkan end-to-end
(58 file bukti eksekusi nyata), dan asisten AI yang setiap jawabannya bisa
dilacak ke runbook serta menolak mengarang prosedur berisiko. **103 test
otomatis hijau, 0 pelanggaran keamanan pada evaluasi 21 kasus** — dan
kegagalan development dipertahankan apa adanya sebagai bukti cara kerja.

## Verifikasi cepat 5 menit (untuk perekrut)

| Menit | Buka | Yang terlihat |
|---|---|---|
| 1 | `docs/evidence/E41-monitor-integrasi-homelab.txt` | alur lengkap: sehat → gangguan → deteksi → pulih (exit 0→1→0) |
| 2 | `assistant/evaluation/report.md` | evaluasi jujur: metrik terpisah per aspek, kelemahan (kasus A8) dinyatakan |
| 3 | `docs/evidence/E45…E47` (CLI assistant) | menjawab berkutipan → abstain jujur → menolak injection |
| 4 | `docs/incidents/INC-001-service-down.md` §17 | kegagalan nyata (Access denied) + analisisnya, bukan disembunyikan |
| 5 | `docs/architecture/decisions.md` D14 & D16 | kedalaman teknis: dua signature kegagalan systemd; ekstraktif vs generatif |

## A. IT Support Homelab — `lab/` + `docs/`

**Ringkasan recruiter.** Lingkungan lab Linux terisolasi (VM Ubuntu target,
dieksekusi nyata di sandbox systemd) dengan satu layanan latihan dan **lima
skenario insiden** yang bisa direproduksi dan dipulihkan end-to-end: layanan
berhenti, disk melewati ambang, DNS gagal, permission salah, konflik port.
Setiap insiden punya dokumen 16 bagian (gejala → hipotesis → diagnostik →
root cause → perbaikan → verifikasi → pencegahan) plus runbook cepat, dengan
58 file bukti eksekusi.

**Tiga kontribusi teknis (didukung implementasi nyata):**
1. Layanan latihan stdlib-only + installer systemd dengan hardening ringan
   (user sistem khusus, `NoNewPrivileges`, `ProtectSystem=strict`) dan guard
   keselamatan di semua skrip operasional — bukti `E01`, `lab/scripts/`.
2. Baseline health check 5-dimensi (disk/service/DNS/TCP/HTTP) dengan
   konvensi exit code 0/1/2 terdokumentasi dan dapat dikonfigurasi via env —
   bukti `E02` (exit 0) dan `E04` (exit 1 saat insiden).
3. Simulasi insiden yang aman by design: fixture tmpfs disposable (tidak
   pernah mengisi root fs), guard nama layanan, kill hanya setelah verifikasi
   `/proc/<pid>/cmdline` — bukti `E10–E17` (disk), `E27–E33` (port).

**Satu contoh kegagalan & analisis.** Rekaman pertama simulasi konflik port
gagal (`E28`, exit 1): settle logic menunggu state `failed`, tetapi di bawah
`Restart=on-failure` kegagalan bind (~2,5 detik/cycle) **tidak pernah memicu
start-limit** sehingga unit terjebak `activating` tanpa henti — berbeda
signature dari kegagalan exit instan (`E22`, ~9 detik → `failed`). Perbaikan:
syarat sukses = unit tidak aktif ≥3 poll beruntun + port tetap dipegang
squatter (`E28b` exit 0). Temuan ini langsung menjadi desain monitor Fase 2
(check service = semua state ≠ `active` dianggap tidak sehat, D14).

**Satu trade-off untuk wawancara.** `Restart=on-failure` vs `always` (D6):
`always` lebih "self-healing" tetapi mengalahkan drill `systemctl stop` —
drill tidak lagi deterministik. Dipilih `on-failure` agar kegagalan buatan
tetap terlihat, dengan konsekuensi: kegagalan bind bisa berputar tanpa henti
(lihat kegagalan di atas) dan itulah mengapa monitor wajib memeriksa
service-layer, bukan hanya port.

## B. System Health Monitor — `monitor/`

**Ringkasan recruiter.** CLI Python (runtime **stdlib-only**, nol dependensi
produksi) yang mengotomasi pemeriksaan Homelab: 5 check dengan timeout,
konfigurasi JSON tervalidasi ketat, output teks + JSON dengan timestamp
timezone, logging JSON berotasi, webhook alert (URL via environment, dedup
antar eksekusi, retry terbatas) yang **tidak pernah mengubah hasil health
check**, scheduler systemd timer, dan 58 unit test deterministik tanpa
internet/VM.

**Tiga kontribusi teknis:**
1. Arsitektur adapter terpisah (disk/systemd/DNS/TCP/HTTP) sehingga semua
   check dapat diuji dengan fake tanpa kondisi mesin — 58 test lulus
   (`E34`), integration test lokal opt-in terhadap lab nyata (`E33b`).
2. Notifikasi aman: kegagalan webhook (retry + warning) tidak mengubah exit
   code dan tidak mencatat state dedup — alert dicoba lagi nanti; bukti
   kirim nyata + dedup tepat 1 POST (`E39`) dan mode kegagalan (`E40`).
3. Scheduler systemd: unit template diverifikasi `systemd-analyze verify`
   lalu **di-trigger nyata** — hasil monitor terekam di journald dan log JSON
   (`E42`).

**Satu contoh kegagalan & analisis.** Run test pertama: **10 dari 58 gagal**
— `_parse_alerts` mensyaratkan semua field padahal section `alerts` harus
punya default; ditambah satu test gagal karena polusi level logger antar test
(`setup_logging` mengeset parent logger). Perbaikan: helper default-tetap-
tervalidasi dan `caplog.set_level` — hasil akhir 58/58 (`E34`). Pelajaran:
validasi ketat harus tetap punya default yang jelas, dan test harus isolasi
terhadap state global.

**Satu trade-off untuk wawancara.** Stdlib-only runtime (D15): audit mudah,
install di VM minimal tanpa pip, nol risiko supply-chain — dengan konsekuensi
fitur ekosistem (metrik Prometheus, dashboard, alert-manager pusat) sengaja
tidak ada di MVP, dan logika pemeriksaan ada dua versi (bash Fase 1, Python
Fase 2) karena keduanya punya peran berbeda.

## C. AI Helpdesk Assistant — `assistant/` (Tahap A: search-only)

**Ringkasan recruiter.** Asisten helpdesk **documentation-grounded**: jawaban
adalah potongan verbatim dari runbook dengan kutipan sumber (document_id,
heading, path, chunk_id, hash) — bukan chatbot generatif. BM25 implementasi
stdlib, abstain jujur bila dokumentasi tidak mencakup, query injection
diberi label safety dan **secara struktural tidak bisa dipatuhi** (ekstraktif),
server FastAPI dengan citation dire-validasi sebelum tampil, evaluasi 21 kasus
sintetis tanpa pelanggaran keamanan.

**Tiga kontribusi teknis:**
1. Knowledge base dengan izin direktori **eksplisit** + guard path traversal +
   chunk metadata lengkap per heading (133 chunks / 11 dokumen, `E49`) —
   tidak pernah mengindeks seluruh repo.
2. Jawaban ekstraktif dengan citation yang hanya bisa dibangun dari chunk
   hasil retrieval (re-validasi di server), abstain dengan ambang terkalibrasi
   — bukti answered (`E45`), abstain (`E46`), laporan metrik terpisah
   (`evaluation/report.md`).
3. Uji keamanan: dokumen fixture berisi instruksi "IGNORE ALL PREVIOUS RULES"
   dipastikan diperlakukan sebagai konten (tampil verbatim + citation, tidak
   pernah menjadi instruksi baru), 6 pola injection terdeteksi & diberi label
   (`E47`, `tests/test_security.py`).

**Satu contoh kegagalan & analisis.** Evaluasi: hit@k 0.889 — kasus A8 tidak
hit (retrieved INC-001+INC-005; expected RB-001/INC-004). Analisis: INC-001
yang ter-retrieve sebenarnya memuat petunjuk reinstall (§14), jadi ekspektasi
kasus terlalu sempit. Keputusan: **dibiarkan apa adanya** (tidak di-tuning
setelah melihat hasil) dan didokumentasikan di `E48` + keterbatasan laporan;
kalibrasi ambang juga dinyatakan bukan set validasi independen. Pembelajaran
tambahan (`E53`): saat mirror EN tak sengaja masuk KB, hit@k bergeser
0.889 → 1.0 tanpa perubahan kode — bukti bahwa metrik retrieval sensitif
terhadap komposisi korpus; KB dikunci ke dokumen sumber kebenaran via
`exclude_globs` (D17) dan baseline 0.889 dikembalikan.

**Satu trade-off untuk wawancara.** Ekstraktif vs generatif (D16): jawaban
kaku dibanding LLM, tetapi 100% bisa diaudit ke sumber, tidak bisa mengarang
prosedur berisiko, dan bekerja offline tanpa biaya. Tahap B (adapter
provider) dirancang dengan config biaya eksplisit dari sumber resmi; sampai
diimplementasikan adapter menolak berjalan secara eksplisit — tidak ada angka
harga/token yang dikarang.

## Peta bukti cepat (untuk demo wawancara)

| Klaim | Bukti | Perintah repro |
|---|---|---|
| Instalasi service end-to-end | `E01` | `sudo lab/scripts/install_demo_service.sh` |
| Baseline sehat vs gagal | `E02` vs `E04` | `bash lab/scripts/baseline.sh` (sebelum/sesudah `simulate_service_down.sh`) |
| Kegagalan tanpa sudo (systemd melindungi unit) | `E03` | jalankan simulate tanpa `sudo` |
| Disk pressure aman (fixture tmpfs) | `E10`–`E17` | `simulate_disk_pressure.sh --yes --mount-only` → isi → recover |
| DNS: resolver sehat vs nama salah | `E18`–`E19` | `getent hosts nonexistent.invalid` vs `archive.ubuntu.com` |
| Port squatter + gejala penipu | `E28`–`E33` | `simulate_port_conflict.sh --yes` → `baseline.sh` → recover |
| Monitor: sehat→deteksi→pulih | `E41` | 5 perintah di header `E41` |
| Monitor: webhook nyata + dedup | `E39`–`E40` | header `E39` (receiver lokal) |
| Monitor: scheduler terverifikasi | `E42` | header `E42` |
| Assistant: answered / abstain / injection | `E45`–`E47` | `lab-assist query "..."` |
| Assistant: evaluasi 21 kasus | `E48` | `python3 assistant/evaluation/evaluate.py` |
| Assistant: server nyata | `E50` | `lab-assist serve` + curl (header `E50`) |
