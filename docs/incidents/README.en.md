# Incident scenario index

English mirror of `docs/incidents/README.md` (Indonesian original is the
source of truth).

Incident documents follow the 16-section template (see INC-001 for the full
English exemplar). Every incident has explicit safety guards and never touches
the DNS, firewall, permissions, or main services of the host machine.

| ID | Title | Status | Simulation approach |
|---|---|---|---|
| INC-001 | Service stopped (`demo-http`) | implemented + tested (sandbox) · requires manual verification (VM) | `simulate_service_down.sh` → `systemctl stop demo-http` |
| INC-002 | Disk usage over threshold | implemented + tested (sandbox) · requires manual verification (VM) | **32 MB disposable tmpfs** fixture at `/mnt/lab-disk-fixture` — root fs is never filled |
| INC-003 | DNS resolution failure | implemented + tested (sandbox, Level A: `.invalid` name, resolver untouched) · Level B (resolver on a disposable VM) requires manual verification | `DNS_HOST=nonexistent.invalid bash baseline.sh` |
| INC-004 | Wrong file permission | implemented + tested (sandbox) · requires manual verification (VM) | `chmod 000` on the **lab app file** (`/opt/demo-http/…`) → restart fails → restore chmod explicitly |
| INC-005 | Connectivity/service port failure | implemented + tested (sandbox) · requires manual verification (VM) | port 8080 conflict by a lab squatter process, diagnosed via `ss`/journald |

Status definitions: `implemented` / `tested` / `simulated` /
`requires manual verification` / `planned` — see
`docs/security/safety-rules.md` §3.

**Language note:** the full 16-section documents for INC-002–005 and the
runbooks RB-002–005 are currently Indonesian-only (`INC-002-disk-pressure.md`,
`INC-003-dns-failure.md`, `INC-004-permission-mismatch.md`,
`INC-005-port-conflict.md`, `RB-002-disk-pressure.md`,
`RB-003-dns-failure.md`, `RB-004-permission-mismatch.md`,
`RB-005-port-conflict.md`). INC-001/RB-001 are available in English as the
format exemplar; the others can be translated on request. Their evidence and
results are summarized in English in `docs/evidence/README.en.md` and
`PORTFOLIO.en.md`.
