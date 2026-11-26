# INC-001 — demo-http service stopped

English mirror of `docs/incidents/INC-001-service-down.md` (Indonesian
original is the source of truth).

| Field | Value |
|---|---|
| ID | INC-001 |
| Title | demo-http service stopped (service-stopped drill) |
| Status | implemented + tested in the sandbox · requires manual verification on the VM |

## 1. ID and title

A controlled "service stopped" drill: deliberately stopping `demo-http`,
observing symptoms, diagnosing, recovering, and verifying the recovery.

## 2. Learning objectives

- Use systemd (`systemctl status/is-active`) and journald for service
  diagnosis.
- Connect symptoms across three layers: unit status, TCP connection, and the
  HTTP response.
- Understand permissions: why stopping a system unit requires root.
- Practice the incident cycle: baseline → outage → symptoms → diagnosis →
  fix → verification.

## 3. Prerequisites and scope

- Environment: the Ubuntu Server 24.04 VM per `docs/setup/` (or any Linux
  host with systemd for practice). The same flow was tested in the sandbox —
  evidence in `docs/evidence/`.
- `demo-http` installed via `install_demo_service.sh`; healthy baseline
  (exit 0).
- Scope: only the `demo-http` unit. SSH, DNS, firewall, and other services
  are never touched.

## 4. Risks and safety steps

- Low risk: lab-only service, port 8080, no real data.
- The simulation script **refuses** any service other than `demo-http`
  (guard in code).
- The simulation uses `systemctl stop` (not `kill -9`): clean, no state
  damage; `Restart=on-failure` does not restart a manual stop, so the drill
  is deterministic.
- Run with `sudo`; the VM console is the fallback access path.

## 5. Normal condition

Evidence: `E02-baseline-sehat.txt` — baseline 5/5 healthy, exit 0:

```text
[OK] disk: / 17% used (warn 80% crit 90%)
[OK] service: demo-http active
[OK] dns: archive.ubuntu.com -> ...
[OK] tcp: 127.0.0.1:8080 connected
[OK] http: GET http://127.0.0.1:8080/health -> 200 ...
```

## 6. How to simulate the problem

```bash
sudo lab/scripts/simulate_service_down.sh --yes
```

Without `--yes` the script asks for interactive confirmation. The flag is
used in the evidence recording because it was non-interactive.

## 7. Observed symptoms

Evidence: `E04-gejala-baseline-gagal.txt` — exit 1, three failing checks at
once:

```text
[FAIL] service: demo-http status=inactive (expected active)
[FAIL] tcp: 127.0.0.1:8080 failed (refused/timeout/closed port)
[FAIL] http: connection refused to http://127.0.0.1:8080/health (curl rc=7)
```

From the host side: HTTP `:8080` and `/health` unreachable. Symptoms from
three layers (unit/TCP/HTTP) point to the same condition.

## 8. Hypotheses

H1: the demo-http process is not running (most likely — unit `inactive`).
H2: the process runs but is not listening on 8080 (port conflict/wrong bind)
— does not fit: TCP and HTTP both fail and the unit is `inactive`.
H3: a host-only network problem — does not fit: DNS still OK and only the lab
service fails.

## 9. Diagnostic commands and why

| Command | Reason |
|---|---|
| `systemctl status demo-http --no-pager -l` | Unit condition: active/inactive/failed, process exit code, PID |
| `sudo journalctl -u demo-http --no-pager -n 30` | systemd+application logs around the event (start/stop) |
| `ss -ltn \| grep 8080` | Confirm nothing is listening on that port |

Evidence: `E05-diagnostik-status.txt` (status `inactive`),
`E06-diagnostik-journalctl.txt` (journald recorded `Stopping...` →
`Deactivated successfully` → `Stopped` — consistent with a controlled stop).

Access lesson learned: `journalctl` **without sudo** cannot see system-unit
logs ("No entries"); system-unit logs require root or the `systemd-journal`
group. Recorded as a learning, not as a manufactured result.

## 10. Actual observations

Summarized from `E05` and `E06` (raw output in the evidence files):

- `systemctl is-active demo-http` → `inactive`.
- journald: `Stopping demo-http.service...`, `Deactivated successfully`,
  `Stopped demo-http.service ...`.
- Port 8080 not listening (supported by the tcp FAIL on the baseline).

## 11. Root cause

Drill cause: the service was deliberately stopped via `systemctl stop` as a
simulated failure. The same pattern appears in real incidents when a service
is stopped manually or its configuration disappears; a unit with
`Restart=on-failure` does not bring back a service that was **stopped**
(rather than crashed) — an important distinction practiced in this drill.

## 12. Fix

```bash
sudo lab/scripts/recover_service.sh
```

(`systemctl start demo-http` + a verification loop for the service being
active **and** `/health` 200, up to 15 seconds.)

## 13. Post-fix verification

Evidence: `E07-pemulihan-recover.txt` — `recovery VERIFIED: service active +
GET /health 200 (attempt 2)`; and `E08-baseline-sehat-ulang.txt` — baseline
back to 5/5, exit 0.

## 14. Rollback

- The fix is additive (starting the service); there is no configuration
  change to undo.
- If the unit is broken: `sudo lab/scripts/uninstall_demo_service.sh`, then
  reinstall; as the last resort, revert the `02-lab-ready` snapshot.

## 15. Prevention

- Scheduled monitoring: run the baseline/monitor periodically (Phase 2:
  `monitor/` + scheduler) so a stopped service is detected quickly.
- Snapshot before any change to units/configuration.
- Keep the runbook (RB-001) so recovery never depends on guesswork.

## 16. Evidence

| Evidence | Content | Result |
|---|---|---|
| `E02` | baseline before | exit 0 |
| `E03` | **real failure** of the first attempt | see section 17 |
| `E03b` | simulation with sudo | exit 0, service inactive |
| `E04` | baseline symptoms | exit 1, 3 failed checks |
| `E05`, `E06` | status & journald diagnostics | inactive; the stop was recorded |
| `E07` | recovery | exit 0, verified |
| `E08` | baseline after | exit 0 |
| `E09` | teardown | exit 0 |

## 17. Real failure during the first drill (portfolio note)

The first attempt ran `simulate_service_down.sh` **without sudo**. systemd
rejected `systemctl stop`: `Access denied` (exit 4) — the service stayed
active and the baseline stayed exit 0 (evidence:
`E03-percobaan-tanpa-sudo-gagal.txt`).

**Analysis:** systemd protects system units from modification by regular
users — correct behavior, not a bug. Fix: both scripts (simulate/recover) now
refuse to run without root (exit 2 + a proper usage message), and the
documentation mentions `sudo` explicitly. Positive side effect: the failure
documents a real permission boundary instead of an assumption.
