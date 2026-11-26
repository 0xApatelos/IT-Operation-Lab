# lab/ — lingkungan Homelab (Fase 1)

Folder ini menyediakan **layanan latihan** dan **skrip operasional** yang
menjadi objek pemeriksaan (baseline), objek insiden (INC-001), dan nantinya
objek pemantauan (monitor/, Fase 2) serta sumber runbook (assistant/, Fase 3).

## Isi

```
lab/
├── services/
│   └── demo-http/          # layanan HTTP latihan (stdlib-only Python)
│       ├── demo_http_server.py
│       └── demo-http.service   # template unit systemd (@@PYTHON_BIN@@, @@SERVICE_USER@@)
└── scripts/
    ├── install_demo_service.sh     # pasang layanan (sudo)
    ├── baseline.sh                 # baseline health check (exit 0/1/2)
    ├── simulate_service_down.sh    # INC-001: stop terkontrol demo-http (sudo)
    ├── recover_service.sh          # INC-001: pemulihan + verifikasi end-to-end (sudo)
    ├── simulate_disk_pressure.sh   # INC-002: fixture tmpfs disposable + isi ~90% (sudo)
    ├── recover_disk_pressure.sh    # INC-002: hapus isi fixture; --teardown unmount (sudo)
    ├── simulate_service_permission.sh # INC-004: chmod 000 file aplikasi lab + restart (sudo)
    ├── recover_service_permission.sh  # INC-004: chmod 755 kembali + start (sudo)
    ├── simulate_port_conflict.sh   # INC-005: instance lab liar menempati port 8080 (sudo)
    ├── recover_service_port.sh     # INC-005: kill terverifikasi cmdline + start (sudo)
    ├── uninstall_demo_service.sh   # teardown (sudo)
    └── runtime/                    # artefak eksekusi (di .gitignore): PID squatter, dsb.
```

## Alur pemakaian (lihat docs/setup/ untuk detail)

1. `sudo lab/scripts/install_demo_service.sh`
2. `lab/scripts/baseline.sh` → harus exit 0 (kondisi normal)
3. `lab/scripts/simulate_service_down.sh --yes` → gangguan terkontrol
4. `lab/scripts/baseline.sh` → exit 1 (gejala terdeteksi)
5. `lab/scripts/recover_service.sh` → pulihkan + verifikasi
6. `lab/scripts/baseline.sh` → kembali exit 0

## Catatan keselamatan

- Skrip simulasi **menolak** layanan apa pun selain `demo-http`.
- INC-002 memakai fixture **tmpfs disposable** di `/mnt/lab-disk-fixture`
  (path diperbaiki di kode, maksimum 256 MB) — root filesystem tidak pernah
  diisi; data fixture hilang saat unmount/reboot.
- INC-003 Level A **tidak mengubah konfigurasi resolver** sama sekali
  (gejala disimulasikan lewat nama `.invalid` yang memang tidak valid).
- INC-004 hanya mengubah mode **file aplikasi lab** (path tetap; menolak bila
  mode awal bukan 755) — tidak ada permission file sistem yang disentuh.
- INC-005 membuat **squatter lab** sebagai user layanan (bukan root, PID
  tercatat di `lab/runtime/`); pemulihan hanya membunuh PID yang cmdline-nya
  TERVERIFIKASI, dan menolak bila port dipegang proses tak dikenal.
- Tidak ada langkah yang menyentuh DNS, firewall, permission, atau layanan
  host utama.
