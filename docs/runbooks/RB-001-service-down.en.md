# RB-001 — Runbook: demo-http service stopped

English mirror of `docs/runbooks/RB-001-service-down.md` (Indonesian original
is the source of truth).

Quick operational version (cheat sheet). The full case study with root-cause
analysis: `docs/incidents/INC-001-service-down.en.md`.

## Trigger

- `baseline.sh` exits 1 with `[FAIL] service: demo-http status=inactive`
  and/or `[FAIL] tcp/http` on 127.0.0.1:8080.
- `/health` unreachable from the host (`Test-NetConnection ... -Port 8080`
  fails, EXAMPLE IP).

## Impact

Lab-only: the practice service is inaccessible. Nothing else is affected. No
production urgency.

## First five minutes (triage)

| # | Command | Purpose |
|---|---|---|
| 1 | `systemctl status demo-http --no-pager -l` | Unit condition: active/inactive/failed, process exit code |
| 2 | `sudo journalctl -u demo-http --no-pager -n 50` | Logs before/during the death (needs root or the `systemd-journal` group) |
| 3 | `ss -ltn \| grep 8080` | Whether the port is really not listening / used by another process |
| 4 | `curl -i -m 5 http://127.0.0.1:8080/health` | Direct verification from inside the VM |

## Common causes & actions

| Status symptom | Likely cause | Action |
|---|---|---|
| `inactive` | stopped manually (e.g., after a drill) | `sudo lab/scripts/recover_service.sh` |
| `failed` | process crash (see the exit code in status) | read the journal → fix the cause → recover; the unit has `Restart=on-failure`, so repeated crashes mean the cause is not gone |
| unit not found | not installed / removed | `sudo lab/scripts/install_demo_service.sh` |
| port conflict | another process holds 8080 | identify via `ss -ltnp` (root); stop other lab processes, never host processes |
| python path changed | system python3 upgrade | reinstall the unit (the installer templates the python path at install time) |

## After recovery

1. `bash lab/scripts/baseline.sh` → **must exit 0** ("service is running" is
   not enough — end-to-end verification uses HTTP).
2. Record the time, cause, and action (for evidence/practice).

## Escalation & rollback

- If recovery fails within 15 s: read `journalctl -u demo-http -n 50`, then
  reinstall via the installer.
- Last resort: revert the `02-lab-ready` snapshot (see
  `docs/setup/teardown.md`).

## Prevention

- Scheduled baseline (Phase 2: `monitor/` with a scheduler) so a stopped
  service is detected immediately, not when someone needs it.
- Snapshot before every change to units/services.
