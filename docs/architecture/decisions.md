# Keputusan teknis & trade-off (Fase 1)

Format ringkas ala ADR: konteks → keputusan → trade-off. Urutan tidak
menyatakan prioritas.

## D1 — Hypervisor: VMware Workstation Pro

- **Konteks:** host Windows 10/11, RAM 8–15 GB, disk kosong 30–60 GB; pilihan
  pemilik repo.
- **Keputusan:** VMware Workstation Pro. Sejak November 2024 gratis untuk
  penggunaan personal/komersial/edukasi tanpa license key (versi 17.5.2+);
  unduhan butuh akun Broadcom. Verifikasi ulang saat instalasi.
- **Trade-off:** unduhan via portal Broadcom (butuh akun); Hyper-V lebih
  "bawaan Windows" tetapi pilihan pemilik repo adalah VMware.

## D2 — OS VM: Ubuntu Server 24.04 LTS

- **Konteks:** butuh systemd, journald, netplan, dan dukungan jangka panjang.
- **Keputusan:** Ubuntu Server 24.04 LTS ("Noble Numbat"), dukungan standar
  hingga Mei 2029.
- **Trade-off:** ISO ±2 GB (unduhan sekali). Alternatif Debian lebih ringan
  tetapi panduan lab ditulis untuk Ubuntu LTS agar konsisten.

## D3 — Jaringan: host-only (VMnet1) + NAT (VMnet8), dua adapter

- **Konteks:** simulasi insiden butuh jaringan terisolasi; update paket butuh
  jalur keluar.
- **Keputusan:** adapter 1 = VMnet1 host-only (IP statik CONTOH
  192.168.200.10/24), adapter 2 = VMnet8 NAT (DHCP). Tanpa inbound dari
  internet.
- **Trade-off:** dua adapter lebih rumit dari satu NAT, tetapi mencerminkan
  praktik isolasi lab dan membuat skenario "layanan/port" tetap aman.

## D4 — Layanan latihan: Python stdlib-only (`http.server`)

- **Konteks:** butuh satu layanan sederhana yang mudah diaudit, tanpa pip.
- **Keputusan:** `demo_http_server.py` stdlib-only, endpoint `/health` JSON,
  port tetap 8080.
- **Trade-off:** `http.server` bukan server produksi — dinyatakan eksplisit
  di docstring. Untuk lab, kualitas auditabilitas > performa.

## D5 — systemd native, bukan Docker

- **Konteks:** tujuan portofolio adalah kemampuan IT operations (unit,
  journald, hardening); lingkungan pengembangan sandbox juga tanpa Docker.
- **Keputusan:** layanan dipasang sebagai unit systemd asli dengan user sistem
  khusus dan hardening ringan.
- **Trade-off:** kurang "cloud-native"; containerisasi ditunda sampai Fase 2+
  bila relevan.

## D6 — `Restart=on-failure`, bukan `always`

- **Konteks:** simulasi `systemctl stop` harus tetap berhenti (drill
  deterministik), tetapi crash nyata sebaiknya auto-recover.
- **Keputusan:** `Restart=on-failure` + `RestartSec=2`.
- **Trade-off:** `always` lebih "self-healing" tetapi mengalahkan simulasi
  stop manual; `on-failure` menjaga kedua perilaku tetap jelas.

## D7 — Baseline bash (Fase 1) vs monitor Python (Fase 2)

- **Konteks:** Fase 1 butuh pemeriksaan cepat tanpa dependensi; Fase 2 butuh
  output JSON, adapter OS, dan unit test pytest.
- **Keputusan:** `baseline.sh` (bash, stdlib) untuk Fase 1; `monitor/`
  (Python, pytest) dibangun di Fase 2 dengan exit code yang setara (0/1/2).
- **Trade-off:** logika pemeriksaan ditulis dua kali — disengaja, supaya versi
  Python dibangun dengan standar engineering penuh tanpa memblokir Fase 1.

## D8 — User sistem khusus + hardening unit ringan

- **Keputusan:** user `demo-http` (tanpa shell/home), `NoNewPrivileges`,
  `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`.
- **Trade-off:** sedikit lebih rumit dari default root; profil keamanan jauh
  lebih baik. Profil lengkap bisa dilihat via `systemd-analyze security`.

## D9 — Fallback installer bila `useradd`/`adduser` tidak ada

- **Konteks:** container minimal kadang tidak punya `useradd` di PATH.
- **Keputusan:** installer mencoba `useradd` → `adduser` → fallback user
  pemanggil dengan `[PERINGATAN]` eksplisit. Fallback hanya untuk dev.
- **Trade-off:** sedikit cabang ekstra di installer, tapi menghindari
  kegagalan instalasi diam-diam dan jujur soal konfigurasi yang berjalan.

## D10 — Port tetap 8080, tanpa flag konfigurasi di installer

- **Keputusan:** satu port tetap untuk seluruh lab agar baseline, runbook, dan
  monitor selalu konsisten.
- **Trade-off:** kurang fleksibel; bila port bentrok, ubah unit + konfigurasi
  monitor secara sadar (bukan diam-diam).

## D11 — Lisensi MIT

- **Konteks:** portofolio publik yang mungkin dipakai orang lain.
- **Keputusan:** MIT + catatan bahwa lisensi tidak mencakup aset pihak ketiga
  (VMware, Ubuntu, layanan AI). Lihat file `LICENSE`.

## D12 — Simulasi disk memakai fixture tmpfs disposable, bukan mengisi root fs

- **Konteks:** simulasi "disk penuh" berisiko merusak sistem bila memakai
  filesystem root; aturan keselamatan repo melarangnya.
- **Keputusan:** fixture **tmpfs 32 MB** (maks 256 MB) di path tetap
  `/mnt/lab-disk-fixture`, di-mount on-the-fly tanpa fstab; path diperbaiki di
  kode (tidak ada argumen path) dan skrip menolak mount non-lab di path itu.
- **Trade-off:** tmpfs hidup di RAM dan perilakunya sedikit berbeda dari disk
  fisik (mis. tidak merepresentasikan fragmentasi/kuota); bila ingin lebih
  dekat ke disk nyata, gunakan loop filesystem di VM disposable — tetap dengan
  ukuran terbatas. Konsistensi ambang baseline diuji dengan ambang yang
  diturunkan (50/75) via environment variable.

## D13 — INC-003 memakai dua level simulasi DNS

- **Konteks:** memutus resolver di host nyata berisiko dan melanggar aturan
  "jangan ubah DNS host utama".
- **Keputusan:** Level A (aman, sandbox): gejala disimulasikan dengan nama
  `.invalid` (RFC 6761) pada konfigurasi baseline — resolver tidak disentuh.
  Level B (VM disposable): memutus resolver sungguhan via netplan + snapshot
  rollback, berstatus `requires manual verification`.
- **Trade-off:** Level A tidak mencakup pola "resolver down" — dibatasi secara
  eksplisit di INC-003 §17 agar tidak overclaim.

## D14 — INC-004/005 menyentuh artefak lab nyata dengan guard deterministik

- **Konteks:** drill permission dan port harus mengubah kondisi nyata (mode
  file, pemilik port) agar signature kegagalannya autentik, tanpa menyentuh
  file/proses sistem.
- **Keputusan:** (a) INC-004: satu file aplikasi lab dengan mode installer yang
  diketahui (0755) — sim `chmod 000`, recover `chmod 755`; skrip menolak bila
  mode awal bukan 755 atau path di luar instalasi lab. (b) INC-005: squatter =
  proses lab yang sama dijalankan sebagai user layanan tanpa systemd, PID
  tercatat; kill hanya setelah verifikasi `/proc/<pid>/cmdline`, SIGKILL hanya
  dengan verifikasi ulang; unit dihentikan dulu untuk membatalkan siklus
  auto-restart (menghindari race self-heal).
- **Temuan nyata yang terdokumentasi:** di bawah `Restart=on-failure`, kegagalan
  exit instan (INC-004) mencapai start-limit dalam ~10 detik (state `failed`),
  sedangkan kegagalan bind (INC-005, cycle ~2,5 detik) tidak pernah memicu
  start-limit dan menyisakan state `activating` tanpa henti. Implikasi: monitor
  (Fase 2) harus menganggap semua state selain `active` sebagai tidak sehat.
- **Trade-off:** guard menambah cabang kode, tetapi membuat drill aman
  diulang tanpa risiko menyentuh proses host lain.

## D15 — Monitor stdlib-only dengan kontrak exit code yang setara baseline.sh

- **Konteks:** Fase 2 harus mengotomasi pemeriksaan Fase 1 tanpa menambah
  permukaan dependensi dan tetap mudah diaudit saat wawancara.
- **Keputusan:** runtime nol dependensi (stdlib), adapter OS dipisah
  (testable), config JSON tervalidasi ketat, exit code 0/1/2 dengan prioritas
  2 > 1 > 0 (setara konvensi baseline.sh), status `unsupported`/`unknown`
  eksplisit, webhook off-default dengan URL via env + dedup state file.
- **Temuan desain yang diwarisi Fase 1 (D14):** check service menganggap
  semua state selain `active` sebagai tidak sehat (termasuk `activating`
  tanpa henti) — langsung diimplementasikan sejak awal.
- **Trade-off:** logika pemeriksaan ada dua versi (bash Fase 1, Python Fase 2)
  — disengaja untuk pembelajaran; versi Python adalah jalur lanjutan (JSON,
  scheduler, alert) sementara baseline.sh tetap sebagai alat cepat tanpa
  instalasi.

## D16 — Assistant Tahap A: ekstraktif search-only, BM25 stdlib, ambang abstain

- **Konteks:** Fase 3 harus grounded pada runbook dengan citation yang bisa
  diperiksa, aman dari prompt injection, dan bekerja offline tanpa biaya.
- **Keputusan:** (a) jawaban **ekstraktif** (potongan verbatim dokumen) —
  secara struktural tidak bisa "mematuhi" instruksi injection; query berpola
  injection dideteksi dan diberi `safety_note`. (b) BM25 implementasi sendiri
  (stdlib) — corpus 133 chunks, dependensi retrieval (sklearn/rank_bm25/vektor
  DB) tidak menambah nilai di skala ini. (c) Abstain dengan ambang `min_score`
  8.0 — dikalibrasi sebagai titik tengah gap skor top-1 out-of-scope (max 5.69)
  vs answerable (min 10.54) pada 21 kasus; kalibrasi pada run dev terpisah,
  bukan set validasi independen (dinyatakan di laporan). (d) Citation hanya
  dibangun dari chunk hasil retrieval + re-validasi di server. (e) fastapi/
  uvicorn hanya untuk mode serve (import lazy) — CLI tetap stdlib-only.
- **Trade-off:** jawaban ekstraktif kaku dibanding LLM, tapi jujur, aman, dan
  bisa diaudit 100% ke sumber; Tahap B (provider) dirancang sebagai adapter
  dengan config biaya eksplisit — sampai diimplementasikan menolak berjalan
  secara eksplisit (tidak ada angka harga/token yang dikarang).

## D17 — Mirror terjemahan (`*.en.md`) dieksklusi dari KB assistant

- **Context:** dokumentasi kini bilingual (mirror `*.en.md` berdampingan di
  folder yang sama). allowed_dirs KB memuat docs/runbooks + docs/incidents —
  mirror EN nyaris ikut terindeks; ketika itu terjadi (tanpa sengaja, saat
  polish dokumentasi), evaluasi berubah 0.889 → 1.0 tanpa perubahan kode
  (E52/E53): KB sangat dipengaruhi komposisi korpus, ditambah risiko chunk
  near-duplicate dan citation ganda.
- **Decision:** config KB mendapat `exclude_globs` (default kosong);
  kb.config.json menyetel `["*.en.md"]`. KB hanya memuat dokumen sumber
  kebenaran (Indonesia); mirror EN adalah salinan presentasi untuk pembaca EN.
- **Trade-off:** assistant tidak bisa menjawab dari mirror EN — sesuai
  desain: KB kanonik satu bahasa. Bila nanti dibutuhkan jawaban bilingual,
  itu keputusan eksplisit (ubah exclude_globs + re-kalibrasi min_score),
  bukan efek samping penambahan file.
