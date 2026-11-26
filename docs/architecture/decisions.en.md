# Technical decisions & trade-offs

English mirror of `docs/architecture/decisions.md` (Indonesian original is
the source of truth).

Compact ADR-style format: context → decision → trade-off. The order does not
imply priority.

## D1 — Hypervisor: VMware Workstation Pro

- **Context:** Windows 10/11 host, 8–15 GB RAM, 30–60 GB free disk; the
  owner's choice.
- **Decision:** VMware Workstation Pro. Since November 2024 it is free for
  personal/commercial/educational use without a license key (17.5.2+);
  downloads need a Broadcom account. Re-verify at installation time.
- **Trade-off:** downloads via the Broadcom portal (account needed); Hyper-V
  is more "built into Windows" but the owner's choice was VMware.

## D2 — VM OS: Ubuntu Server 24.04 LTS

- **Context:** needs systemd, journald, netplan, and long-term support.
- **Decision:** Ubuntu Server 24.04 LTS ("Noble Numbat"), standard support
  until May 2029.
- **Trade-off:** the ISO is ~2 GB (a one-time download). Debian would be
  lighter, but the lab guides are written for Ubuntu LTS for consistency.

## D3 — Network: host-only (VMnet1) + NAT (VMnet8), two adapters

- **Context:** incident simulation needs an isolated network; package updates
  need an outbound path.
- **Decision:** adapter 1 = VMnet1 host-only (static EXAMPLE IP
  192.168.200.10/24), adapter 2 = VMnet8 NAT (DHCP). No inbound from the
  internet.
- **Trade-off:** two adapters are more complex than a single NAT, but they
  mirror real lab-isolation practice and keep "service/port" scenarios safe.

## D4 — Practice service: Python stdlib-only (`http.server`)

- **Context:** one simple service is needed, easy to audit, no pip.
- **Decision:** `demo_http_server.py` stdlib-only, a JSON `/health` endpoint,
  fixed port 8080.
- **Trade-off:** `http.server` is not a production server — stated explicitly
  in the docstring. For the lab, auditability > performance.

## D5 — systemd native, not Docker

- **Context:** the portfolio goal is IT-operations skill (units, journald,
  hardening); the dev sandbox also has no Docker.
- **Decision:** the service is installed as a native systemd unit with a
  dedicated system user and light hardening.
- **Trade-off:** less "cloud-native"; containerization postponed until Phase
  2+ if relevant.

## D6 — `Restart=on-failure`, not `always`

- **Context:** the `systemctl stop` simulation must stay stopped (a
  deterministic drill), but real crashes should auto-recover.
- **Decision:** `Restart=on-failure` + `RestartSec=2`.
- **Trade-off:** `always` is more self-healing but overrides the manual-stop
  simulation; `on-failure` keeps both behaviors clear.

## D7 — Baseline bash (Phase 1) vs monitor Python (Phase 2)

- **Context:** Phase 1 needs fast checks with no dependencies; Phase 2 needs
  JSON output, OS adapters, and pytest tests.
- **Decision:** `baseline.sh` (bash, stdlib) for Phase 1; `monitor/` (Python,
  pytest) built in Phase 2 with equivalent exit codes (0/1/2).
- **Trade-off:** the check logic is written twice — deliberately, so the
  Python version is built to full engineering standards without blocking
  Phase 1.

## D8 — Dedicated system user + light unit hardening

- **Decision:** the `demo-http` user (no shell/home), `NoNewPrivileges`,
  `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`.
- **Trade-off:** slightly more complex than the default root; a much better
  security profile. The full profile is viewable via
  `systemd-analyze security`.

## D9 — Installer fallback when `useradd`/`adduser` is missing

- **Context:** minimal containers sometimes lack `useradd` in PATH.
- **Decision:** the installer tries `useradd` → `adduser` → falls back to the
  calling user with an explicit `[WARNING]`. The fallback is dev-only.
- **Trade-off:** a few extra branches in the installer, but no silent install
  failures and honesty about the running configuration.

## D10 — Fixed port 8080, no installer flag

- **Decision:** one fixed port for the whole lab so baseline, runbooks, and
  the monitor always agree.
- **Trade-off:** less flexible; on a conflict, change the unit + monitor
  config consciously (never silently).

## D11 — MIT license

- **Context:** a public portfolio others may reuse.
- **Decision:** MIT + a note that the license does not cover third-party
  assets (VMware, Ubuntu, AI services). See `LICENSE`.

## D12 — Disk simulation via a disposable tmpfs fixture, never filling root

- **Context:** a "full disk" simulation risks damaging the system on the root
  filesystem; the repo's safety rules forbid it.
- **Decision:** a **32 MB tmpfs** fixture (max 256 MB) at the fixed path
  `/mnt/lab-disk-fixture`, mounted on the fly without fstab; the path is
  hard-coded (no path argument) and scripts refuse non-lab mounts at that
  path.
- **Trade-off:** tmpfs lives in RAM and behaves slightly differently from a
  physical disk (no fragmentation/quota representation); a loop filesystem on
  a disposable VM would be closer to a real disk — still size-limited.
  Threshold consistency is tested with lowered thresholds (50/75) via env
  vars.

## D13 — INC-003 uses two DNS simulation levels

- **Context:** breaking the resolver on a real host is risky and violates the
  "never change the host's DNS" rule.
- **Decision:** Level A (safe, sandbox): symptoms simulated via an `.invalid`
  name (RFC 6761) in the baseline config — the resolver is untouched.
  Level B (disposable VM): actually break the resolver via netplan + snapshot
  rollback, status `requires manual verification`.
- **Trade-off:** Level A does not cover the "resolver down" pattern —
  explicitly limited in INC-003 §17 to avoid overclaiming.

## D14 — INC-004/005 touch real lab artifacts with deterministic guards

- **Context:** permission and port drills must change real state (file mode,
  port owner) so failure signatures are authentic — without touching system
  files/processes.
- **Decision:** (a) INC-004: one lab app file with a known installer mode
  (0755) — simulate `chmod 000`, recover `chmod 755`; scripts refuse unless
  the initial mode is 755 or the path resolves outside the lab install.
  (b) INC-005: the squatter is the same lab process run as the service user
  without systemd, PID recorded; kill only after verifying
  `/proc/<pid>/cmdline`, SIGKILL only after re-verification; the unit is
  stopped first to cancel the auto-restart loop (avoiding a self-heal race).
- **Documented real finding:** under `Restart=on-failure`, instant-exit
  failures (INC-004) reach the start limit in ~10 s (state `failed`), while
  bind failures (INC-005, ~2.5 s cycles) never trigger it and leave state
  `activating` forever. Implication: the monitor (Phase 2) must treat every
  state other than `active` as unhealthy.
- **Trade-off:** guards add code branches, but make drills safely repeatable
  without touching host processes.

## D15 — Monitor stdlib-only with exit codes equivalent to baseline.sh

- **Context:** Phase 2 must automate Phase-1 checks without adding dependency
  surface and stay easy to explain in interviews.
- **Decision:** zero-dependency runtime (stdlib), separated OS adapters
  (testable), strictly validated JSON config, exit codes 0/1/2 with priority
  2 > 1 > 0 (equivalent to baseline.sh), explicit
  `unsupported`/`unknown` statuses, webhook off-by-default with the URL from
  env + a dedup state file.
- **Design finding inherited from Phase 1 (D14):** the service check treats
  every state other than `active` as unhealthy (including an endless
  `activating`) — implemented from day one.
- **Trade-off:** the check logic exists in two versions (bash Phase 1, Python
  Phase 2) — intentional for learning; the Python version is the advanced
  path (JSON, scheduler, alerts) while baseline.sh stays the no-install quick
  tool.

## D16 — Assistant Stage A: extractive search-only, stdlib BM25, abstain threshold

- **Context:** Phase 3 must be grounded in the runbooks with verifiable
  citations, safe from prompt injection, and work offline at zero cost.
- **Decision:** (a) **extractive** answers (verbatim document excerpts) —
  structurally unable to "obey" injection instructions; injection-pattern
  queries are detected and get a `safety_note`. (b) BM25 implemented in-house
  (stdlib) — for a 133-chunk corpus, retrieval dependencies
  (sklearn/rank_bm25/vector DBs) add no meaningful value. (c) Abstention with
  `min_score` 8.0 — calibrated as the midpoint of the top-1 score gap
  between out-of-scope (max 5.69) and answerable (min 10.54) across 21
  cases; calibrated on a separate dev run, not an independent validation set
  (stated in the report). (d) Citations are only built from retrieved chunks
  + re-validated server-side. (e) fastapi/uvicorn only for serve mode (lazy
  import) — the CLI stays stdlib-only.
- **Trade-off:** extractive answers are stiffer than an LLM, but honest, safe,
  and 100% auditable to sources; Stage B (provider) is designed as an adapter
  with an explicit cost config — until implemented it refuses to run
  explicitly (no invented price/token numbers).

## D17 — Translation mirrors (`*.en.md`) are excluded from the assistant KB

- **Context:** documentation is now bilingual (mirrors live next to the
  originals in the same folders). The KB's allowed_dirs include
  docs/runbooks + docs/incidents — the EN mirrors almost entered the index;
  when they did (accidentally, during the docs polish), the evaluation
  changed 0.889 → 1.0 with no code change (E52/E53): the KB is
  composition-driven, plus near-duplicate chunks would risk duplicate
  citations.
- **Decision:** the KB config gained `exclude_globs` (default empty);
  kb.config.json sets `["*.en.md"]`. The KB keeps only the
  source-of-truth (Indonesian) documents; EN mirrors are presentation copies
  for English readers.
- **Trade-off:** the assistant cannot answer from EN mirrors — by design: a
  single canonical KB language. If bilingual answers are ever needed, that is
  an explicit decision (change exclude_globs + re-calibrate min_score), not a
  side effect of adding files.
