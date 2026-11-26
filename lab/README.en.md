# lab/ — Homelab environment (Phase 1)

English mirror of `lab/README.md` (Indonesian original is the source of truth).

This folder provides the **practice service** and **operational scripts** that
serve as the object of baseline checks, the incident drills (INC-001..005),
and later the monitoring target (`monitor/`, Phase 2) and the runbook source
(`assistant/`, Phase 3).

## Contents

```
lab/
├── services/
│   └── demo-http/          # practice HTTP service (stdlib-only Python)
│       ├── demo_http_server.py
│       └── demo-http.service   # systemd unit template (@@PYTHON_BIN@@, @@SERVICE_USER@@)
└── scripts/
    ├── install_demo_service.sh     # install the service (sudo)
    ├── baseline.sh                 # baseline health check (exit 0/1/2)
    ├── simulate_service_down.sh    # INC-001: controlled stop of demo-http (sudo)
    ├── recover_service.sh          # INC-001: recovery + end-to-end verification (sudo)
    ├── simulate_disk_pressure.sh   # INC-002: disposable tmpfs fixture + fill ~90% (sudo)
    ├── recover_disk_pressure.sh    # INC-002: remove fixture content; --teardown unmounts (sudo)
    ├── simulate_service_permission.sh # INC-004: chmod 000 on the lab app file + restart (sudo)
    ├── recover_service_permission.sh  # INC-004: chmod 755 back + start (sudo)
    ├── simulate_port_conflict.sh   # INC-005: rogue lab instance takes port 8080 (sudo)
    ├── recover_service_port.sh     # INC-005: cmdline-verified kill + start (sudo)
    ├── uninstall_demo_service.sh   # teardown (sudo)
    └── runtime/                    # execution artifacts (gitignored): squatter PID, etc.
```

## Usage flow (see docs/setup/ for details)

1. `sudo lab/scripts/install_demo_service.sh`
2. `bash lab/scripts/baseline.sh` → must exit 0 (normal condition)
3. `sudo bash lab/scripts/simulate_service_down.sh --yes` → controlled outage
4. `bash lab/scripts/baseline.sh` → exit 1 (symptoms detected)
5. `sudo bash lab/scripts/recover_service.sh` → recover + verify
6. `bash lab/scripts/baseline.sh` → exit 0 again

Each incident has its own simulate/recover pair with the same safety guard
style (INC-002: `simulate_disk_pressure.sh`/`recover_disk_pressure.sh`;
INC-004: `..._permission...`; INC-005: `..._port...`).

## Safety notes

- Simulation scripts **refuse** any service other than `demo-http`.
- INC-002 uses a **disposable tmpfs fixture** at `/mnt/lab-disk-fixture`
  (hard-coded path, max 256 MB) — the root filesystem is never filled;
  fixture data disappears on unmount/reboot.
- INC-003 Level A **never touches resolver configuration** (symptoms are
  simulated via the inherently invalid `.invalid` name).
- INC-004 only changes the mode of the **lab application file** (hard-coded
  path; refuses unless the current mode is 755) — no system file permissions
  are touched.
- INC-005 spawns a **lab squatter** as the service user (not root, PID
  recorded under `lab/runtime/`); recovery only kills PIDs whose cmdline is
  VERIFIED, and refuses when the port is held by an unknown process.
- No step touches the DNS, firewall, permissions, or main services of the
  host machine.
