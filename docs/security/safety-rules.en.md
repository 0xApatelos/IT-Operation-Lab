# Lab security & safety

English mirror of `docs/security/safety-rules.md` (Indonesian original is the
source of truth).

This document defines network trust boundaries, safety rules during incident
simulation, evidence label conventions, and the secrets policy.

## 1. Network trust boundaries

| Zone | Contents | Trust |
|---|---|---|
| Windows host | VMware Workstation, your personal credentials | Trusted (yours) |
| VMnet1 (host-only) | Host + server VM, HTTP :8080 and SSH :22 traffic | Lab-only — considered trusted **only** for practice; never store real data on lab services |
| VMnet8 (NAT) | Outbound path from the VM (apt updates, DNS) | Public internet — no inbound |
| Internet | — | Untrusted |

Network rules:

- **No inbound port-forwarding** from the host/internet to the VM.
- Lab services bind to `0.0.0.0` **only so the host can reach them via
  VMnet1**; never switch to a bridged adapter.
- Every IP address in this documentation is an **EXAMPLE**. Actual addresses
  on your VM will differ — verify with `ip -br a` (VM) and `ipconfig`
  (Windows: the VMware Network Adapter VMnet1 adapter).
- Network-disruption simulation happens only inside a disposable VM, after a
  snapshot exists and console access (not just SSH) is available.

## 2. Incident-simulation safety rules

1. **Never fill the root filesystem** to simulate a full disk — use a small
   disposable filesystem (tmpfs/loop) or a fixture.
2. **Never change the DNS, firewall, permissions, or main services** of the
   Windows host. All disruptions happen inside the lab VM or on the lab
   service (`demo-http`).
3. **Never cut the SSH session you are using** — simulation scripts only
   touch `demo-http`, never `ssh`.
4. **Console access first** (the VMware console window) before any
   simulation, so a network disruption cannot lock you out.
5. **Snapshot before disruption**: VMware Snapshot Manager, suggested names
   `02-lab-ready` (see docs/setup/).
6. **Warn before state-changing steps** — lab scripts do this
   (`[WARNING]`, `--yes` confirmation or a prompt).
7. Explicit guards in code: `simulate_service_down.sh` and
   `recover_service.sh` **refuse** any service other than `demo-http`.
8. No auto-remediation anywhere in the repo: recovery is always manual and
   verified.

## 3. Evidence label conventions

See `docs/evidence/README.en.md`. In short:

- `AKTUAL` (actual) = raw output of a real execution (with environment noted).
- `CONTOH` (example) = synthetic output for illustration, always marked.
- Work statuses: `implemented`, `tested`, `simulated` (a controlled drill),
  `requires manual verification`, `planned` — used consistently in the README
  and incident documents.

## 4. Secrets policy

- No secrets in source code, frontends, example logs, or documentation.
- `.env` is in `.gitignore`; only `.env.example` with placeholders may be
  committed (used from Phase 2 for webhooks/tokens).
- Webhook tokens/URLs come only from environment variables, never hard-coded.
- This portfolio uses **synthetic data** — no real helpdesk tickets, private
  conversations, or organizational data.

## 5. Accounts & privileges policy

- The lab service runs as the dedicated system user `demo-http` (no shell,
  no home) with light systemd hardening (`NoNewPrivileges`,
  `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`).
- State-changing operational scripts (`install`, `simulate`, `recover`,
  `uninstall`) explicitly require root and refuse to run without `sudo` —
  except `baseline.sh`, which deliberately needs no root.
