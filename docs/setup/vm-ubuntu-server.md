# Setup lab: VMware Workstation + Ubuntu Server 24.04 LTS (dari nol)

Panduan ini menyiapkan lingkungan Fase 1 pada host Windows 10/11 dengan RAM
8–15 GB dan disk kosong 30–60 GB.

**Status:** `requires manual verification` — panduan ditulis berdasarkan
spesifikasi terverifikasi (VMware gratis personal use, Ubuntu 24.04 LTS
didukung s.d. Mei 2029), tetapi eksekusi di VM milik pemilik repo belum
dilakukan. Tandai selesai setiap langkah saat benar-benar dijalankan.

## Prasyarat

| Item | Nilai |
|---|---|
| Host | Windows 10/11, akun administrator |
| RAM host | ≥ 8 GB (12 GB lebih nyaman) |
| Disk kosong | ≥ 30 GB (VM pakai 25 GB + ISO 2 GB) |
| Hypervisor | VMware Workstation Pro 17.5.2+ — gratis untuk personal use, tanpa license key; unduh dari Broadcom Support Portal (butuh akun gratis) |
| OS VM | Ubuntu Server 24.04 LTS (ISO dari ubuntu.com/download/server) |
| Opsional | Git untuk Windows (memudahkan mengambil repo), tapi bisa diganti `scp` bawaan Windows |

## Ringkasan arsitektur yang akan dibangun

- VMnet1 **host-only** → jaringan lab host ↔ VM (IP CONTOH: 192.168.200.0/24).
- VMnet8 **NAT** → jalur keluar VM untuk `apt update` (tanpa inbound).
- VM: 2 vCPU, 2 GB RAM, 25 GB disk, Ubuntu Server 24.04 LTS.
- Layanan lab: `demo-http.service` di port 8080.

Detail diagram: `docs/architecture/network-diagram.md`.

## Langkah 1 — Pasang VMware Workstation

1. Buat akun gratis di support.broadcom.com, unduh VMware Workstation Pro
   (versi 17.5.2 atau lebih baru).
2. Instal dengan opsi default; pilih **"Use VMware Workstation for Personal
   Use"** saat diminta lisensi (tidak perlu key).
3. Setelah terpasang, buka *Edit → Virtual Network Editor*, pastikan ada
   **VMnet1 (host-only)** dan **VMnet8 (NAT)**. **Catat subnet VMnet1
   aktual** (mis. CONTOH 192.168.200.0/24) — nilai di seluruh dokumentasi ini
   adalah CONTOH dan harus diganti dengan subnet Anda.

## Langkah 2 — Buat VM Ubuntu Server

1. Unduh ISO Ubuntu Server 24.04 LTS.
2. *File → New Virtual Machine → Typical → Installer disc image file* → pilih ISO.
3. Spesifikasi: **2 vCPU, 2 GB RAM, 25 GB disk (single file)**, nama VM
   mis. `lab-server`.
4. Sebelum menyalakan VM, buka *Edit virtual machine settings → Add →
   Network Adapter* sehingga ada:
   - **Adapter 1: Custom → VMnet1 (host-only)**
   - **Adapter 2: Custom → VMnet8 (NAT)**

## Langkah 3 — Instalasi OS (±15 menit)

Saat wizard installer Ubuntu:

1. Pilih bahasa English; keyboard sesuai Anda.
2. Tanpa proxy; mirror default.
3. Buat akun: username `labadmin`, password kuat (**jangan dicatat di repo**).
4. Centang **Install OpenSSH server**.
5. Lewati snap featured (tidak dibutuhkan).
6. Selesai → reboot → login via konsol VMware.

## Langkah 4 — Update & verifikasi adapter

```bash
sudo apt update && sudo apt full-upgrade -y
ip -br link          # catat nama interface (CONTOH: ens160 = host-only, ens161 = NAT)
ip -br addr          # adapter NAT biasanya dapat IP DHCP dari VMnet8
```

Uji jalur keluar: `curl -I https://archive.ubuntu.com` → harus `200/301`.

## Langkah 5 — IP statik di sisi host-only (netplan)

> **CONTOH** — sesuaikan nama interface dan subnet dengan hasil Langkah 4.

```yaml
# /etc/netplan/01-lab.yaml  (chmod 600 — netplan menuntut ini)
network:
  version: 2
  ethernets:
    ens160:                          # CONTOH: interface host-only
      addresses: [192.168.200.10/24] # CONTOH: IP VM di jaringan lab
    ens161:                          # CONTOH: interface NAT
      dhcp4: true
```

```bash
sudo chmod 600 /etc/netplan/01-lab.yaml
sudo netplan apply
ip -br addr   # verifikasi IP host-only sesuai CONTOH yang Anda pilih
```

Dari Windows (PowerShell), verifikasi host ↔ VM:

```powershell
ping 192.168.200.10          # CONTOH IP VM Anda
Test-NetConnection 192.168.200.10 -Port 22   # CONTOH; cek SSH lab
```

## Langkah 6 — Snapshot "01-clean-install"

VMware: *VM → Snapshot → Take Snapshot*, nama `01-clean-install`.
Ini titik rollback pertama sebelum insiden disimulasikan.

## Langkah 7 — Salin repository ke VM

Dari PowerShell (Windows 10/11 punya OpenSSH client bawaan):

```powershell
cd <folder tempat repo berada>
scp -r it-operations-ai-lab labadmin@192.168.200.10:~/
```

Alternatif: `git clone` setelah repo di-push ke GitHub (butuh keputusan &
izin push oleh pemilik repo), atau VMware shared folder.

## Langkah 8 — Pasang layanan lab

```bash
cd ~/it-operations-ai-lab
sudo bash lab/scripts/install_demo_service.sh
```

Skrip ini membuat user sistem `demo-http`, menyalin aplikasi ke
`/opt/demo-http`, memasang unit systemd (dengan hardening), enable --now,
dan memverifikasi `/health`.

## Langkah 9 — Baseline (kondisi normal)

```bash
bash lab/scripts/baseline.sh    # tanpa root; harap exit 0, 5/5 sehat
```

Jika check DNS gagal: jaringan host-only tidak punya jalur keluar — pastikan
adapter NAT aktif (Langkah 5) atau set `DNS_HOST=localhost` sementara dan
catat alasannya di dokumen insiden.

## Langkah 10 — Snapshot "02-lab-ready" & verifikasi akhir

1. Snapshot `02-lab-ready` — titik sebelum simulasi insiden.
2. Dari Windows: `Test-NetConnection 192.168.200.10 -Port 8080` (CONTOH IP)
   → `TcpTestSucceeded : True`.
3. Dari browser host: `http://192.168.200.10:8080/health` (CONTOH IP) → JSON
   `{"status": "ok", ...}`.

Selanjutnya: `docs/incidents/README.md` (lima skenario insiden dengan bukti)
dan `docs/setup/teardown.md` (pemulihan lingkungan).

## Checklist status

| Langkah | Status |
|---|---|
| 1–3 instalasi VMware + OS | requires manual verification |
| 4–5 update + netplan | requires manual verification |
| 6–7 snapshot + transfer repo | requires manual verification |
| 8–10 service + baseline + snapshot | requires manual verification (alur yang sama sudah teruji di sandbox — lihat `docs/evidence/`) |
