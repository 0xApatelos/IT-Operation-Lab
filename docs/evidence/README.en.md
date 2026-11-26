# docs/evidence/ — evidence index

English mirror of `docs/evidence/README.md` (Indonesian original is the
source of truth).

All files in this folder are **raw output from real executions** in the agent
sandbox (a Debian 13 container with systemd as PID 1) — not the owner's
Ubuntu VM. Full environment context is in `E00`. Evidence from the owner's
own VM will be added later with a different environment header, changing
`requires manual verification` to verified.

## Label conventions

| Label | Meaning |
|---|---|
| `AKTUAL` (actual) | Raw output of a real execution, no fabrication. |
| `CONTOH` (example) | Synthetic output for illustration; **not** an execution result. Always marked. |
| `SINTETIS` (synthetic) | Deliberately created test data (e.g., fixtures), not production/personal data. |

Rule: no fake logs or screenshots. If something has not been run, it is
marked `planned` or `requires manual verification` — evidence is never
invented.

## INC-001 evidence list — service stopped (2026-11-25 UTC)

| File | Content | Result |
|---|---|---|
| `E00-lingkungan-sandbox.txt` | Environment context (OS, systemd, python, correction note) | — |
| `E01-install-demo-http.txt` | Service installation via installer | exit 0; system user `demo-http` created; unit enable --now |
| `E02-baseline-sehat.txt` | Healthy baseline before the incident (normal condition) | exit 0; 5/5 healthy |
| `E03-percobaan-tanpa-sudo-gagal.txt` | **Real failure**: stop without sudo rejected by systemd | exit 4; `Access denied` |
| `E03b-simulasi-stop-sudo.txt` | Controlled simulation with sudo | exit 0; service `inactive` |
| `E04-gejala-baseline-gagal.txt` | Symptoms while the service is stopped | exit 1; 3 failing checks (service/tcp/http) |
| `E05-diagnostik-status.txt` | Diagnostics: `systemctl status demo-http` | status `inactive` |
| `E06-diagnostik-journalctl.txt` | Diagnostics: unit journald logs | the stop was recorded; without sudo a user cannot see system-unit logs |
| `E07-pemulihan-recover.txt` | Recovery via `recover_service.sh` | exit 0; service active + `/health` 200 |
| `E08-baseline-sehat-ulang.txt` | Post-fix verification | exit 0; 5/5 healthy |
| `E09-teardown-uninstall.txt` | Full teardown | exit 0; unit, app, user removed |

## INC-002 — disk pressure (2026-11-26 UTC; the sandbox restarted between sessions, so the service was reinstalled in E11)

| File | Content | Result |
|---|---|---|
| `E10-inc002-mount-fixture.txt` | Mount a 32 MB disposable tmpfs (empty) | df 0% |
| `E11-inc002-baseline-sehat-fixture.txt` | Healthy baseline on the empty fixture (+ service reinstall; recording-correction note) | exit 0; 5/5 healthy |
| `E12-inc002-simulasi-isi.txt` | Fill the fixture ~90% (28 MB) | df 88% |
| `E13-inc002-gejala-baseline-gagal.txt` | Single-factor symptom: disk >= CRIT | exit 1 |
| `E14-inc002-diagnostik-disk.txt` | df/du/ls → `lab-fill.bin` 28 MB | cause identified |
| `E15-inc002-pemulihan.txt` | Remove the offending file | df 0% |
| `E16-inc002-baseline-pulih.txt` | Baseline recovered | exit 0; 5/5 healthy |
| `E17-inc002-teardown-fixture.txt` | Unmount + remove the mountpoint | no mounts left |

## INC-003 — DNS failure, Level A (2026-11-26 UTC; resolver untouched)

| File | Content | Result |
|---|---|---|
| `E18-inc003-gejala-dns-gagal.txt` | Baseline with `DNS_HOST=nonexistent.invalid` | exit 1; dns FAIL (single factor) |
| `E19-inc003-diagnostik-getent.txt` | Compare a failing name (rc=2) vs a common name (rc=0) | resolver healthy, the name genuinely does not exist |
| `E20-inc003-baseline-pulih.txt` | Baseline with the default DNS_HOST | exit 0; 5/5 healthy |

## INC-004 — wrong file permission (2026-11-26 UTC; the sandbox restarted between sessions, so the service was reinstalled in E21)

| File | Content | Result |
|---|---|---|
| `E21-inc004-baseline-sehat.txt` | Healthy baseline + file mode 755 (+ reinstall context) | exit 0; 5/5 healthy |
| `E22-inc004-simulasi-chmod.txt` | `chmod 000` on the lab app file + restart | unit `failed` (start limit ~9 s) |
| `E23-inc004-gejala-baseline-gagal.txt` | Three-layer symptoms (service/tcp/http) | exit 1 |
| `E24-inc004-diagnostik-permission.txt` | status + journald + stat | `Errno 13 Permission denied`, `status=2`, mode 000 |
| `E25-inc004-pemulihan.txt` | chmod 755 + reset-failed + start | verified (active + 200) |
| `E26-inc004-baseline-pulih.txt` | Baseline recovered + mode 755 | exit 0; 5/5 healthy |

## INC-005 — port 8080 conflict (2026-11-26 UTC)

| File | Content | Result |
|---|---|---|
| `E27-inc005-baseline-sehat.txt` | Healthy baseline + unit-owned listener | exit 0; 5/5 healthy |
| `E28-inc005-simulasi-squatter.txt` | **First recording failed**: settle logic too narrow | exit 1 — the unit stuck in `activating` |
| `E28b-inc005-simulasi-ulang-fix.txt` | Verified cleanup + re-simulation (fixed settle logic) | exit 0; unit inactive, squatter holds the port |
| `E29-inc005-gejala-deceptif.txt` | Deceptive symptoms: service FAIL but tcp/http OK (the squatter answers) | exit 1 |
| `E30-inc005-diagnostik-port.txt` | status + journald + ss + cmdline | `Errno 98 Address already in use`; squatter identified |
| `E31-inc005-pemulihan.txt` | Kill the squatter after cmdline verification + start the unit | verified (active + 200) |
| `E32-inc005-baseline-pulih.txt` | Baseline recovered | exit 0; 5/5 healthy |
| `E33-inc005-endstate-bersih.txt` | Clean end state (+ the `pgrep -f` false-positive lesson) | exactly 1 unit-owned python3 process |

## Phase 2 — System Health Monitor (2026-11-26 UTC; sandbox restarted between sessions, service reinstalled)

| File | Content | Result |
|---|---|---|
| `E33b-monitor-integration-lokal.txt` | Monitor integration test against the local lab (opt-in) | 1 pass |
| `E34-monitor-pytest-unit.txt` | Deterministic unit tests (mocked, no internet/VM) | 58 pass |
| `E35-monitor-ruff.txt` | ruff lint | clean |
| `E36-monitor-cli-sehat.txt` | CLI healthy report against the lab (text) | exit 0; 5/5 ok |
| `E37-monitor-cli-json.txt` | Structured JSON output | timezone timestamps; full schema |
| `E38-monitor-config-tidak-valid.txt` | warn_pct ≥ crit_pct → rejected | exit 2 + stderr message |
| `E39-monitor-webhook-dedup-nyata.txt` | LIVE webhook to a local receiver: send + dedup | exactly 1 POST; payload without secrets; state recorded |
| `E40-monitor-webhook-gagal.txt` | Webhook unreachable (bounded retry) | warning; health results intact; exit stays 1 |
| `E41-monitor-integrasi-homelab.txt` | Required flow: healthy → outage → detection → recovery | exit 0 → 1 → 0 |
| `E42-monitor-scheduler-verify-trigger.txt` | `systemd-analyze verify` + real service-unit trigger | verify 0; start 0; journald + JSON log captured; clean cleanup |

## Phase 3 — AI Helpdesk Assistant, Stage A (2026-11-26 UTC)

| File | Content | Result |
|---|---|---|
| `E43-assistant-pytest-unit.txt` | Assistant unit tests (mini corpus) | 43 pass |
| `E44-assistant-ruff.txt` | ruff lint (assistant) | clean |
| `E45-assistant-cli-query-answered.txt` | CLI query answered — extractive answer + citations | status answered; sources RB-001/INC-001 |
| `E46-assistant-cli-abstain.txt` | Out-of-scope query | honest abstain, no invented procedures |
| `E47-assistant-cli-injection.txt` | Injection query "ignore the rules" | safety_note + abstain |
| `E48-assistant-evaluasi.txt` | 21-case evaluation (hit rate, citations, abstain, safety, latency) | hit@k 0.889; citations 1.0; abstain 1.0; safety 1.0; 0 violations. A8 note: the case's expected_doc_ids were too narrow (the retrieved INC-001 contains the reinstall guidance §14) — left as-is, not tuned |
| `E49-assistant-index-stats.txt` | KB statistics | 133 chunks / 11 docs, allowed_dirs only |
| `E50-assistant-server-nyata.txt` | Live FastAPI server: health, query, abstain, input limits, relative-URL UI | all as designed; UI with no hard-coded localhost URL |

## Final repo QA (2026-11-26 UTC)

| File | Content | Result |
|---|---|---|
| `E51-repo-qa-final.txt` | CI YAML valid, secret grep clean, README 7-question checklist, placeholders only in templates, full re-runs | all green; 58+43 tests; hit@k 0.889; 0 violations |
| `E52-docs-recruiter-polish-qa.txt` | docs polish QA (recruiter perspective): new README structure, cross-file links, number consistency + annotation of the hit@k=1.0 finding | structure 5/5; broken links 0; KB finding followed up in E53 |
| `E53-kb-exclude-globs-sideeffect.txt` | EN-mirror side effect on the assistant KB + the `exclude_globs` fix (D17) | baseline restored: hit@k 0.889, 133/11, 45 assistant tests, clean ruff |

Per-project recruiter summary & demo map: `PORTFOLIO.en.md` (root).
Manual-scoring rubric template: `assistant/evaluation/rubrik-manual.en.md`
(not yet filled → requires manual verification).

## How to read

1. Start with `E00` for context, then follow the numbers — that is the INC-001
   flow from normal condition to recovery.
2. `E03` is intentionally kept as-is as a real-failure example; its analysis
   is in `../incidents/INC-001-service-down.en.md` §17.
3. No secrets, third-party private IPs, or personal data in the evidence.
