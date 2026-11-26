# Lab setup: VMware Workstation + Ubuntu Server 24.04 LTS (from scratch)

English mirror of `docs/setup/vm-ubuntu-server.md` (Indonesian original is
the source of truth).

This guide prepares the Phase-1 environment on a Windows 10/11 host with
8–15 GB RAM and 30–60 GB free disk.

**Status:** `requires manual verification` — the guide was written from
verified facts (VMware free for personal use, Ubuntu 24.04 LTS supported
until May 2029), but the execution on the owner's VM has not happened yet.
Mark each step as done only after actually running it.

## Prerequisites

| Item | Value |
|---|---|
| Host | Windows 10/11, administrator account |
| Host RAM | ≥ 8 GB (12 GB is more comfortable) |
| Free disk | ≥ 30 GB (VM uses 25 GB + a 2 GB ISO) |
| Hypervisor | VMware Workstation Pro 17.5.2+ — free for personal use, no license key; download from the Broadcom Support Portal (free account needed) |
| VM OS | Ubuntu Server 24.04 LTS (ISO from ubuntu.com/download/server) |
| Optional | Git for Windows (easier repo transfer), or plain `scp` shipped with Windows |

## Architecture summary to be built

- VMnet1 **host-only** → the host ↔ VM lab network (EXAMPLE IP:
  192.168.200.0/24).
- VMnet8 **NAT** → the VM's outbound path for `apt update` (no inbound).
- VM: 2 vCPU, 2 GB RAM, 25 GB disk, Ubuntu Server 24.04 LTS.
- Lab service: `demo-http.service` on port 8080.

Diagram details: `docs/architecture/network-diagram.en.md`.

## Step 1 — Install VMware Workstation

1. Create a free account at support.broadcom.com, download VMware Workstation
   Pro (17.5.2 or newer).
2. Install with the default options; choose **"Use VMware Workstation for
   Personal Use"** when asked for a license (no key needed).
3. After installation, open *Edit → Virtual Network Editor* and make sure
   **VMnet1 (host-only)** and **VMnet8 (NAT)** exist. **Note the actual
   VMnet1 subnet** (e.g., EXAMPLE 192.168.200.0/24) — the values used in this
   documentation are EXAMPLES and must be replaced with your subnet.

## Step 2 — Create the Ubuntu Server VM

1. Download the Ubuntu Server 24.04 LTS ISO.
2. *File → New Virtual Machine → Typical → Installer disc image file* → pick
   the ISO.
3. Specs: **2 vCPU, 2 GB RAM, 25 GB disk (single file)**, VM name e.g.
   `lab-server`.
4. Before powering on, open *Edit virtual machine settings → Add → Network
   Adapter* so there are:
   - **Adapter 1: Custom → VMnet1 (host-only)**
   - **Adapter 2: Custom → VMnet8 (NAT)**

## Step 3 — OS installation (±15 minutes)

In the Ubuntu installer wizard:

1. Language English; your keyboard layout.
2. No proxy; default mirror.
3. Create the account: username `labadmin`, a strong password (**never
   record it in the repo**).
4. Check **Install OpenSSH server**.
5. Skip featured snaps (not needed).
6. Done → reboot → log in via the VMware console.

## Step 4 — Update & verify adapters

```bash
sudo apt update && sudo apt full-upgrade -y
ip -br link          # note interface names (EXAMPLE: ens160 = host-only, ens161 = NAT)
ip -br addr          # the NAT adapter usually gets a DHCP address from VMnet8
```

Test outbound: `curl -I https://archive.ubuntu.com` → should return `200/301`.

## Step 5 — Static IP on the host-only side (netplan)

> **EXAMPLE** — adjust interface names and the subnet to your Step-4 results.

```yaml
# /etc/netplan/01-lab.yaml  (chmod 600 — netplan requires it)
network:
  version: 2
  ethernets:
    ens160:                          # EXAMPLE: the host-only interface
      addresses: [192.168.200.10/24] # EXAMPLE: the VM's IP in the lab network
    ens161:                          # EXAMPLE: the NAT interface
      dhcp4: true
```

```bash
sudo chmod 600 /etc/netplan/01-lab.yaml
sudo netplan apply
ip -br addr   # verify the host-only IP matches the EXAMPLE you chose
```

From Windows (PowerShell), verify host ↔ VM:

```powershell
ping 192.168.200.10          # EXAMPLE VM IP
Test-NetConnection 192.168.200.10 -Port 22   # EXAMPLE; check lab SSH
```

## Step 6 — Snapshot "01-clean-install"

VMware: *VM → Snapshot → Take Snapshot*, name `01-clean-install`.
This is the first rollback point before any incident simulation.

## Step 7 — Copy the repository to the VM

From PowerShell (Windows 10/11 ships an OpenSSH client):

```powershell
cd <folder containing the repo>
scp -r it-operations-ai-lab labadmin@192.168.200.10:~/
```

Alternatives: `git clone` once the repo is pushed to GitHub (requires the
owner's decision & permission), or a VMware shared folder.

## Step 8 — Install the lab service

```bash
cd ~/it-operations-ai-lab
sudo bash lab/scripts/install_demo_service.sh
```

This script creates the `demo-http` system user, copies the app to
`/opt/demo-http`, installs the hardened systemd unit, enable --now, and
verifies `/health`.

## Step 9 — Baseline (normal condition)

```bash
bash lab/scripts/baseline.sh    # no root; expect exit 0, 5/5 healthy
```

If the DNS check fails: the host-only network has no outbound path — make
sure the NAT adapter is active (Step 5) or temporarily set
`DNS_HOST=localhost` and record the reason in the incident document.

## Step 10 — Snapshot "02-lab-ready" & final verification

1. Snapshot `02-lab-ready` — the point before incident simulation.
2. From Windows: `Test-NetConnection 192.168.200.10 -Port 8080` (EXAMPLE IP)
   → `TcpTestSucceeded : True`.
3. From the host browser: `http://192.168.200.10:8080/health` (EXAMPLE IP) →
   JSON `{"status": "ok", ...}`.

Next: `docs/incidents/README.en.md` (five incident scenarios with evidence)
and `docs/setup/teardown.en.md` (environment recovery).

## Status checklist

| Step | Status |
|---|---|
| 1–3 VMware + OS installation | requires manual verification |
| 4–5 update + netplan | requires manual verification |
| 6–7 snapshot + repo transfer | requires manual verification |
| 8–10 service + baseline + snapshot | requires manual verification (the same flow was tested in the sandbox — see `docs/evidence/`) |
