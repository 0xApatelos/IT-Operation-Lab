# monitor/ — System Health Monitor (Phase 2)

English mirror of `monitor/README.md` (Indonesian original is the source of truth).

A Python CLI automating the checks used in the Homelab (Phase 1). CLI-first
(no dashboard), **stdlib-only** runtime (zero production dependencies), two
dev-only dependencies: `pytest` and `ruff`.

## Status

| Area | Status |
|---|---|
| 5 checks: disk, service (systemd), DNS, TCP, HTTP | implemented + tested (unit) + integration (sandbox) |
| Strictly validated JSON config | implemented + tested |
| Text + JSON output, timezone timestamps | implemented + tested |
| Exit codes 0/1/2 as documented | implemented + tested |
| JSON logging with rotation (512 KiB × 3) | implemented + tested |
| Webhook adapter (off by default, env-based, dedup, retry) | implemented + tested (+ live sandbox evidence) |
| systemd-timer scheduler (Ubuntu VM) | implemented; unit verified via `systemd-analyze verify`; periodic execution on VM = requires manual verification |
| Auto-remediation | **none (intentional, per MVP design)** |

## Architecture

```
config.py    → load + strict validation (ConfigError → exit 2)
checks.py    → 5 pure checks (take adapters; exceptions → defined statuses)
adapters.py  → OS-specific: systemctl (list-argv subprocess, no shell),
               disk (shutil), DNS (getaddrinfo + thread timeout guard),
               TCP (socket.create_connection), HTTP (urllib + timeout)
output.py    → human-readable text + structured JSON
notify.py    → optional webhook (env-based URL, dedup state file, bounded retry)
cli.py       → argparse, orchestration, exit codes
```

Check statuses: `ok`, `warn` (disk only; does not cause exit 1), `fail`,
`unsupported` (platform lacks the capability — not a failure), `unknown`
(unexpected exception — counted as unhealthy).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | all checks healthy (ok/warn/unsupported) |
| 1 | at least one check is `fail` or `unknown` |
| 2 | CLI configuration/execution error (missing/invalid config, etc.) |

**Priority: 2 > 1 > 0.** A failed alert delivery or a failed `--json-out`
write does NOT change the exit code (warning in the log only).

## Install & run

```bash
cd it-operations-ai-lab
python3 -m venv .venv
.venv/bin/pip install -e 'monitor[dev]'
.venv/bin/lab-monitor --config monitor/config.example.json          # example without copying
# your own configuration:
cp monitor/config.example.json monitor/config.json   # (config.json is gitignored)
.venv/bin/lab-monitor --config monitor/config.json --format text    # default
.venv/bin/lab-monitor --config monitor/config.json --format json    # JSON to stdout
.venv/bin/lab-monitor --config monitor/config.json --json-out runtime-report.json
```

Alternative without installing: `python3 -m monitor_lab --config ...` from
the `monitor/` folder.

### Configuration reference (monitor/config.example.json)

- `checks`: list; `type` is one of `disk|service|dns|tcp|http`; unique `name`.
  - `disk`: `path`, `warn_pct` < `crit_pct` (1–99).
  - `service`: `unit` (letters/digits and `@ . _ -` only — validated to be
    argv-safe).
  - `dns`: `host`, `timeout_seconds` (0–60].
  - `tcp`: `host`, `port` (1–65535), `timeout_seconds`.
  - `http`: `url` (http/https), `timeout_seconds`. 2xx = ok, non-2xx = fail.
- `output`: `log_file` (relative paths resolve against the config folder),
  `log_level` (DEBUG/INFO/WARNING/ERROR).
- `alerts`: `webhook_enabled` (**false by default**), `webhook_url_env` (name
  of the env var holding the URL — the token/URL never lives in the config),
  `retry_max` (0–5), `dedup_seconds` (0–86400), `state_file` (dedup across
  runs).

Relative paths resolve against the configuration file's directory so behavior
is identical regardless of the working directory (including under systemd).

## Webhook alerts

- URL from the environment: `LAB_WEBHOOK_URL=http://…` (env name in config).
- Payload contains only check results (host, time, failing checks + details)
  — no secrets and no environment content.
- Dedup: one send per (host, check, status) combination within
  `dedup_seconds`; state persists in `state_file` across scheduler runs.
  State is recorded only on success → failed alerts retry on the next run.
- Retry: `retry_max` attempts with short backoff; failure = warning only.

## Testing

```bash
.venv/bin/pytest monitor/tests                 # unit tests (deterministic, mocked, no internet)
.venv/bin/pytest monitor/tests -m integration  # local integration (requires demo-http running)
.venv/bin/ruff check monitor/monitor_lab monitor/tests
```

Unit tests use fake adapters (no VM/internet/secrets) and cover: healthy
condition, disk over threshold, service inactive/failed/missing, DNS failure
& timeout, TCP refused & timeout, HTTP non-2xx & refused & timeout & unknown
host, invalid config (including bool-as-number, port 0, warn≥crit, unit with
spaces), unsupported platform, notification failure (health results intact),
dedup & retry, exit codes, and the JSON schema.

## Scheduler (Ubuntu VM — systemd timer)

After `lab-monitor` is installed in `.venv` and `monitor/config.json` exists:

```bash
sudo cp monitor/scheduler/lab-monitor.service monitor/scheduler/lab-monitor.timer /etc/systemd/system/
sudo sed -i "s|@@REPO_DIR@@|$HOME/it-operations-ai-lab|; s|@@SERVICE_USER@@|labadmin|" \
  /etc/systemd/system/lab-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable --now lab-monitor.timer
systemctl list-timers lab-monitor.timer          # verify the schedule
sudo systemctl start lab-monitor.service         # manual one-shot trigger
journalctl -u lab-monitor.service -n 20          # inspect results
```

Timer: `OnBootSec=2min`, `OnUnitActiveSec=5min`, `Persistent=true`.
The unit template was verified with `systemd-analyze verify` (evidence E42);
periodic execution on the VM = requires manual verification.

## Homelab integration (required flow)

The flow is documented with real evidence in `docs/evidence/E41`:
healthy baseline (monitor exit 0) → controlled outage
(`simulate_service_down.sh`) → monitor detects it (exit 1, detail
`status=inactive`) → manual fix (`recover_service.sh`) → monitor exit 0.

## Technical decisions & trade-offs

- **Stdlib-only runtime**: easy to audit & install on a minimal VM; features
  like a Prometheus exporter are deliberately out of scope (MVP).
- **DNS via getaddrinfo + thread timeout guard**: the system resolver can
  block without a timeout — the thread guard bounds each check's duration
  (a still-running thread is a daemon and does not hold the process open).
- **TCP/HTTP as the primary connectivity check**; no ICMP (by design).
- **`unknown` ≠ `fail` as a label, both exit 1**: unexpected exceptions must
  never look healthy.
- **Webhook URL via env, not config**: prevents secrets entering git.
- **Disk percent via `shutil.disk_usage`**: may differ slightly from `df -P`
  (df counts reserved blocks) — stated explicitly.

## Limitations

- MVP without a dashboard, without auto-remediation, without email/IM alerts.
- Dedup is local per host (state file), not a central alert manager.
- The service check is systemd-only (other platforms → `unsupported`).
