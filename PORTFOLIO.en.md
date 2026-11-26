# Portfolio summary — for recruiters & interview prep

> Every claim in this document points to real execution evidence in
> `docs/evidence/` (environment label: Debian 13 sandbox with systemd — not a
> VM). No business-impact numbers, user counts, or time savings — not
> measured, not invented. Detailed per-feature status: `README.en.md`.
> Indonesian original: `PORTFOLIO.md`.

## 30-second elevator pitch

This repo proves two competencies through artifacts, not claims: five Linux
incident scenarios built, broken, diagnosed, and recovered end to end (57
real-execution evidence files), and an AI assistant whose every answer is
traceable to the runbooks and which refuses to invent risky procedures.
**103 automated tests green, 0 safety violations in a 21-case evaluation** —
and development failures are kept as-is as evidence of how the work is done.

## 5-minute quick verification (for recruiters)

| Minute | Open | What you will see |
|---|---|---|
| 1 | `docs/evidence/E41-monitor-integrasi-homelab.txt` | the full flow: healthy → outage → detection → recovery (exit 0→1→0) |
| 2 | `assistant/evaluation/report.md` | an honest evaluation: metrics split per aspect, the weakness (case A8) stated |
| 3 | `docs/evidence/E45…E47` (assistant CLI) | citing answers → honest abstain → refusing injection |
| 4 | `docs/incidents/INC-001-service-down.en.md` §17 | a real failure (Access denied) + its analysis, not hidden |
| 5 | `docs/architecture/decisions.en.md` D14 & D16 | technical depth: two systemd failure signatures; extractive vs generative |

(Evidence file names keep their Indonesian names — they are the originals.)

## A. IT Support Homelab — `lab/` + `docs/`

**Recruiter summary.** An isolated Linux lab environment (target: Ubuntu VM;
actually executed in a systemd sandbox) with one practice service and **five
incident scenarios** that can be reproduced and recovered end to end: service
stopped, disk over threshold, DNS failure, wrong permissions, port conflict.
Each incident has a 16-section document (symptoms → hypotheses → diagnostics →
root cause → fix → verification → prevention) plus a quick runbook, with 57
evidence files of real executions.

**Three technical contributions (backed by real implementation):**
1. A stdlib-only practice service + a systemd installer with light hardening
   (dedicated system user, `NoNewPrivileges`, `ProtectSystem=strict`) and
   safety guards in every operational script — evidence `E01`, `lab/scripts/`.
2. A five-dimension baseline health check (disk/service/DNS/TCP/HTTP) with
   documented exit codes 0/1/2 and env-based configuration — evidence `E02`
   (exit 0) and `E04` (exit 1 during the incident).
3. Safe-by-design incident simulation: a disposable tmpfs fixture (root fs is
   never filled), a service-name guard, and kills only after verifying
   `/proc/<pid>/cmdline` — evidence `E10–E17` (disk), `E27–E33` (port).

**One real failure & analysis.** The first recording of the port-conflict
simulation failed (`E28`, exit 1): the settle logic waited for state
`failed`, but under `Restart=on-failure` a bind failure (~2.5 s/cycle)
**never triggers the start limit**, so the unit stayed stuck in `activating`
forever — a different signature from instant-exit failures (`E22`, ~9 s →
`failed`). Fix: success = unit not active for ≥3 consecutive polls + the
squatter still holding the port (`E28b`, exit 0). This finding directly
shaped the Phase-2 monitor (a service check treats every state ≠ `active` as
unhealthy, D14).

**One trade-off to discuss.** `Restart=on-failure` vs `always` (D6): `always`
is more "self-healing" but overrides the `systemctl stop` drill — drills stop
being deterministic. `on-failure` keeps manufactured failures visible, with
the consequence that bind failures can loop forever (see the failure above),
which is exactly why the monitor must check the service layer, not just the
port.

## B. System Health Monitor — `monitor/`

**Recruiter summary.** A Python CLI (runtime **stdlib-only**, zero production
dependencies) automating the homelab checks: 5 checks with timeouts, strictly
validated JSON config, text + JSON output with timezone timestamps, rotating
JSON logging, webhook alerts (URL from the environment, cross-run dedup,
bounded retries) that **never change health-check results**, a systemd-timer
scheduler, and 58 deterministic unit tests without internet/VM.

**Three technical contributions:**
1. A separated adapter architecture (disk/systemd/DNS/TCP/HTTP) so every
   check is testable with fakes independent of the machine — 58 tests pass
   (`E34`), plus an opt-in local integration test against the real lab
   (`E33b`).
2. Safe notifications: webhook failure (retry + warning) never changes the
   exit code and never records dedup state — alerts retry next run; live
   send + dedup exactly 1 POST (`E39`) and the failure mode (`E40`).
3. Systemd scheduler: unit template verified with `systemd-analyze verify`,
   then **triggered for real** — monitor results captured in journald and
   the JSON log (`E42`).

**One real failure & analysis.** The first test run: **10 of 58 failing** —
`_parse_alerts` required every field although the `alerts` section must have
defaults; plus one test failed due to logger-level leakage between tests
(`setup_logging` sets the parent logger). Fixes: default-but-validated
helpers and `caplog.set_level` — final result 58/58 (`E34`). Lesson: strict
validation still needs explicit defaults, and tests must isolate global state.

**One trade-off to discuss.** Stdlib-only runtime (D15): easy to audit, runs
on a minimal VM without pip, zero supply-chain surface — at the cost of
ecosystem features (Prometheus metrics, dashboards, a central alert manager)
that are deliberately absent from the MVP, and two versions of the check
logic (bash Phase 1, Python Phase 2) because they serve different roles.

## C. AI Helpdesk Assistant — `assistant/` (Stage A: search-only)

**Recruiter summary.** A documentation-grounded helpdesk assistant: answers
are verbatim excerpts from the runbooks with citations (document_id, heading,
path, chunk_id, hash) — not a generative chatbot. BM25 implemented on the
stdlib, honest abstention when the docs don't cover the question, query
injection labeled as a safety note and **structurally impossible to obey**
(extractive), a FastAPI server that re-validates citations before display,
and a 21-case synthetic evaluation with zero safety violations.

**Three technical contributions:**
1. A knowledge base with **explicit** directory allow-list + path-traversal
   guard + per-heading chunk metadata (133 chunks / 11 docs, `E49`) — the
   whole repo is never indexed.
2. Extractive answers whose citations can only be built from retrieved
   chunks (re-validated server-side), abstention with a calibrated threshold
   — evidence: answered (`E45`), abstain (`E46`), separate metrics in
   `evaluation/report.md`.
3. Security testing: a fixture document containing "IGNORE ALL PREVIOUS
   RULES" is confirmed to be treated as content (shown verbatim with a
   citation, never as new instructions), and 6 injection patterns are
   detected & labeled (`E47`, `tests/test_security.py`).

**One real failure & analysis.** Evaluation hit@k 0.889 — case A8 missed
(retrieved INC-001+INC-005; expected RB-001/INC-004). Analysis: the retrieved
INC-001 actually contains the reinstall guidance (§14), so the case
expectation was too narrow. Decision: **left as-is** (no tuning after seeing
results) and documented in `E48` + the report limitations; the threshold
calibration is also explicitly declared as not an independent validation set.
Additional lesson (`E53`): when EN mirrors accidentally entered the KB,
hit@k shifted 0.889 → 1.0 with no code change — proof that retrieval metrics
are sensitive to corpus composition; the KB was locked to source-of-truth
documents via `exclude_globs` (D17) and the 0.889 baseline was restored.

**One trade-off to discuss.** Extractive vs generative (D16): answers are
stiffer than an LLM, but 100% auditable to the source, cannot invent risky
procedures, and work offline at zero API cost. Stage B (a provider adapter)
is designed with an explicit cost config from the official source; until it
is implemented, the adapter refuses to run explicitly — no invented price or
token numbers.

## Evidence quick map (for a live demo)

| Claim | Evidence | Repro command |
|---|---|---|
| End-to-end service installation | `E01` | `sudo lab/scripts/install_demo_service.sh` |
| Healthy vs failing baseline | `E02` vs `E04` | `bash lab/scripts/baseline.sh` (before/after `simulate_service_down.sh`) |
| Failure without sudo (systemd protects units) | `E03` | run the simulate script without `sudo` |
| Safe disk pressure (tmpfs fixture) | `E10`–`E17` | `simulate_disk_pressure.sh --yes --mount-only` → fill → recover |
| DNS: healthy resolver vs wrong name | `E18`–`E19` | `getent hosts nonexistent.invalid` vs `archive.ubuntu.com` |
| Port squatter + deceptive symptoms | `E28`–`E33` | `simulate_port_conflict.sh --yes` → `baseline.sh` → recover |
| Monitor: healthy → detect → recover | `E41` | the 5 commands in the `E41` header |
| Monitor: live webhook + dedup | `E39`–`E40` | the `E39` header (local receiver) |
| Monitor: verified scheduler | `E42` | the `E42` header |
| Assistant: answered / abstain / injection | `E45`–`E47` | `lab-assist query "..."` |
| Assistant: 21-case evaluation | `E48` | `python3 assistant/evaluation/evaluate.py` |
| Assistant: live server | `E50` | `lab-assist serve` + curl (the `E50` header) |
