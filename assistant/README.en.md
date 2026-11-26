# assistant/ — AI Helpdesk Assistant (Phase 3, Stage A)

English mirror of `assistant/README.md` (Indonesian original is the source of
truth).

Documentation-grounded assistance for the lab runbooks: the user searches for
troubleshooting steps and gets **document excerpts with citations** (document
id, heading, path, chunk id, hash). Current mode: **search-only** (BM25
retrieval, no LLM) — not a generative chatbot.

## Status

| Area | Status |
|---|---|
| KB builder (explicit dirs, chunk+metadata+hash, traversal guard) | implemented + tested |
| BM25 retrieval stdlib-only (top-k + abstain threshold) | implemented + tested |
| Extractive answers (summary/steps/warnings/follow-ups/citations) | implemented + tested |
| Query-injection detection & labeling (not followed, not executed) | implemented + tested |
| Citation validation against retrieval results | implemented + tested |
| FastAPI server + single-page UI (relative URLs, local bind default) | implemented + tested |
| 21-case synthetic evaluation + runner + report | implemented + tested (results: `evaluation/report.md`) |
| Stage-B model adapter (local/API provider) | planned — interface ready; `OpenAICompatibleAdapter` deliberately refuses to run |

## How it works (Stage A)

```
query → validation (length ≤ 500, control chars cleaned)
      → injection-instruction detection (safety_note label, NOT followed)
      → BM25 search over KB chunks (top_k ≤ 5)
      → top-1 score < min_score → status insufficient_evidence (abstain)
      → score ≥ min_score → EXTRACTIVE answer from documents:
          summary / diagnostic_steps / warnings (verbatim from the text)
          + citations (chunk_id, doc, heading, path, score)
```

Structural guarantees: no step can appear that is not in the document text;
citations can only be built from retrieved chunks; out-of-scope questions →
abstain, not invented procedures. The assistant **never executes commands,
never modifies systems, and never claims to know the server's current state**.

## Install & run

```bash
cd it-operations-ai-lab
python3 -m venv .venv
.venv/bin/pip install -e 'assistant[dev]'     # fastapi/uvicorn only for `serve`
.venv/bin/lab-assist index-stats
.venv/bin/lab-assist query "demo-http service stopped, how do I diagnose it?"
.venv/bin/lab-assist serve                    # UI at http://127.0.0.1:8077
```

The `query` CLI works without fastapi (lazy import). `python3 -m
assistant_lab` is also supported.

## Knowledge base

Defined **explicitly** in `kb.config.json`:

| Key | Value | Note |
|---|---|---|
| `allowed_dirs` | `docs/runbooks`, `docs/incidents` | only these two directories are indexed; never the whole repo |
| `repo_root` | `..` | traversal guard: allowed dirs must resolve inside the root |
| `top_k` | 5 (max 5) | chunk count limit |
| `min_score` | 8.0 | abstain threshold (calibration: midpoint between out-of-scope top-1 max 5.69 and answerable min 10.54) |
| `max_query_chars` | 500 | input limit |
| `max_chunk_chars` | 1200 | long sections are split |
| `exclude_globs` | `["*.en.md"]` | translation mirrors are excluded — the KB keeps only source-of-truth documents (D17) |

Per-chunk metadata: `document_id` (RB-xxx/INC-xxx), `title`, `rel_path`,
`heading`, `chunk_id`, `content_hash` (sha256 16 hex) — every citation is
traceable to the source document.

## Evaluation (Stage A)

```bash
python3 assistant/evaluation/evaluate.py     # → evaluation/report.json + report.md
```

21 synthetic cases: 9 answerable, 4 out-of-scope, 4 ambiguous, 4 injection
(`evaluation/cases.json`, each with a rubric). Run results (sandbox,
2026-11-26): hit@k 0.889, citation validity 1.0, out-of-scope abstain 1.0,
injection safety note 1.0, latency p50 0.14 ms / p95 0.34 ms (n=21,
indicative), tokens/cost N/A (no provider). These numbers are **not** an
"AI accuracy" figure — retrieval and behavior are measured separately; full
content scoring remains a manual rubric.

Honesty note: case A8 did not hit (retrieved INC-001+INC-005; expected
RB-001/INC-004). The retrieved INC-001 actually contains the reinstall
guidance (§14) — the case expectation was too narrow. Left as-is so numbers
are not tuned after seeing results. The manual rubric template is
`evaluation/rubrik-manual.en.md` (not yet filled → requires manual
verification).

## Security

- Questions AND document content are **untrusted input**. The extractive
  mode structurally cannot "obey" injection instructions; injection-pattern
  queries are additionally detected and get a `safety_note`.
- A fixture document containing "IGNORE ALL PREVIOUS RULES..." is tested: it
  is only shown verbatim as a document excerpt with a citation, never treated
  as new instructions.
- Citations are re-validated server-side before display; no shell execution,
  no file access driven by user input, no credential access.
- Limits: 500-char input, top_k ≤ 5, small payloads, server logs record only
  query length & status (not content).
- **Bind defaults to 127.0.0.1**. Exposing it to the network (e.g.
  `--host 0.0.0.0`) is an explicit owner decision with real risk: everyone on
  the network can read the runbooks; no authentication in the MVP. The UI
  uses relative URLs (no hard-coded localhost) so it is safe behind a
  proxied preview.

## Testing

```bash
python3 -m pytest assistant/tests      # unit (tmp mini corpus, deterministic)
python3 -m ruff check assistant/assistant_lab assistant/tests assistant/evaluation
```

## Stage B (planned)

A provider adapter (local/API) with: API key only from the environment
(`LAB_ASSIST_API_KEY`), a mandatory cost config filled from the official
pricing source (model, rate per 1K tokens, rate date), and token usage
reported from provider responses. The offline mode stays functional without
an API key. See the docstring of `assistant_lab/model_adapter.py` — until
implemented, the provider adapter refuses to run explicitly (never silently).
