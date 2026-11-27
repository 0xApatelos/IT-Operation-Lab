# Real-execution screenshots

A visual gallery of the portfolio workflow. **Every image here is rendered
from REAL execution output** in the agent sandbox — the commands actually
ran, their output was saved verbatim in `captures/`, then laid out as PNG by
`render_terminal.py` (the script is committed — anyone can audit how the
images were made).

## Honesty rules (important)

- The renderer **only styles the presentation** (monospace font, colors based
  on `[OK]`/`[FAIL]`/`[WARN]`/`[SAFETY]` markers, window title) and **never
  changes the text** — no output line is added, removed, or invented.
- All executions are from the **agent sandbox** (see `E00`), **not a VM** —
  the honest label appears in each image's footer. The raw text evidence
  lives in `docs/evidence/`.
- **No** manipulated browser-UI screenshots and no mockups presented as real.
  The assistant's local UI can be run yourself via `lab-assist serve` (see
  `assistant/README.en.md`).

## Index

| File | Shows | Capture source | Related evidence |
|---|---|---|---|
| `png/sc-01-baseline-sehat.png` | Baseline 5/5 healthy, exit 0 (normal condition) | `captures/01-baseline-sehat.txt` | E02 |
| `png/sc-02-gejala-insiden.png` | INC-001: 3 failing checks while the service is stopped, exit 1 | `captures/03-gejala-insiden.txt` | E04 |
| `png/sc-03-pemulihan-terverifikasi.png` | Verified recovery: service active + HTTP 200 | `captures/04-recover.txt` | E07 |
| `png/sc-04-monitor-cli.png` | Monitor CLI (Phase 2): 5-check text report, exit 0 | `captures/05-monitor-text.txt` | E36 |
| `png/sc-05-monitor-json.png` | Monitor: structured JSON output (truncated) | `captures/06-monitor-json.txt` | E37 |
| `png/sc-06-assistant-answered.png` | Assistant: extractive answer + source citations | `captures/07-assistant-answered.txt` | E45 |
| `png/sc-07-assistant-abstain-injection.png` | Assistant: honest abstain + `[SAFETY]` label for injection | `captures/08-assistant-abstain-injection.txt` | E46–E47 |
| `png/sc-08-server-api.png` | Real FastAPI server: health, answered/abstain query, field validation | `captures/09-server-api.txt` | E50 |

(File names keep their Indonesian names — they are the originals.)

## How to reproduce / regenerate

```bash
cd docs/screenshots
# prerequisites on a sandbox/host: demo-http installed (sudo lab/scripts/install_demo_service.sh),
# monitor & assistant installed (pip install -e 'monitor[dev]' -e 'assistant[dev]')
python3 render_terminal.py captures/01-baseline-sehat.txt png/sc-01-baseline-sehat.png "window title"
# (repeat per index row — the full per-capture commands are in the headers of
#  captures/*.txt and in docs/evidence/)
```

To re-capture the output itself (not just re-render), the per-step commands
are in the comment at the top of each `captures/*.txt` and in the related
evidence files — run them in your own lab environment (VM) and save the
result with your own environment header.

Indonesian original: `README.md` (in this folder).
