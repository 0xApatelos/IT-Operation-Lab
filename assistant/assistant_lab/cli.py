"""CLI lab-assist: query (search-only) / serve / index-stats.

Exit code (query): 0 = jawaban/abstain sehat; 2 = config/KB tidak valid atau
pertanyaan tidak valid. Serve tidak berhenti kecuali error startup.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .answer import AnswerEngine
from .kb import KBError
from .security import QueryValidationError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lab-assist",
        description=(
            "AI Helpdesk Assistant (Tahap A: search-only). Jawaban ekstraktif dari "
            "runbook dengan kutipan sumber; tidak mengeksekusi perintah."
        ),
    )
    p.add_argument("--version", action="version", version=f"assistant-lab {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="cari di knowledge base runbook (search-only)")
    q.add_argument("--kb-config", default=None, help="path config KB (default: kb.config.json sebelah package)")
    q.add_argument("question", help="pertanyaan Anda")
    q.add_argument("--format", choices=("text", "json"), default="text")

    s = sub.add_parser("serve", help="jalankan web UI lokal (FastAPI)")
    s.add_argument("--kb-config", default=None)
    s.add_argument("--host", default=os.environ.get("LAB_ASSIST_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("LAB_ASSIST_PORT", "8077")))

    st = sub.add_parser("index-stats", help="statistik knowledge base")
    st.add_argument("--kb-config", default=None)
    return p


def _default_config() -> str:
    return str(Path(__file__).resolve().parent.parent / "kb.config.json")


def _engine(cfg_path: str | None) -> AnswerEngine:
    return AnswerEngine.from_config(cfg_path or _default_config())


def _render_text(a: dict) -> str:
    lines = [f"mode: {a['mode']} | status: {a['status']}"]
    if a.get("safety_note"):
        lines.append(f"[SAFETY] {a['safety_note']}")
    if a.get("summary"):
        lines.append(f"ringkasan: {a['summary']}")
    if a["diagnostic_steps"]:
        lines.append("langkah diagnostik (dari dokumen):")
        lines += [f"  {i}. {s}" for i, s in enumerate(a["diagnostic_steps"], 1)]
    if a["warnings"]:
        lines.append("peringatan (dari dokumen):")
        lines += [f"  - {w}" for w in a["warnings"]]
    if a["follow_up_questions"]:
        lines.append("perlu klarifikasi:")
        lines += [f"  - {f}" for f in a["follow_up_questions"]]
    lines.append("sumber:")
    lines += [f"  [{c['document_id']} {c['chunk_id']}] {c['heading']} ({c['path']}, skor {c['score']})"
              for c in a["citations"]]
    lines += [f"limitasi: {l}" for l in a["limitations"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.cmd == "query":
            engine = _engine(args.kb_config)
            try:
                answer = engine.query(args.question)
            except QueryValidationError as e:
                print(f"[QUERY-ERROR] {e}", file=sys.stderr)
                return 2
            print(json.dumps(answer, indent=2, ensure_ascii=False) if args.format == "json"
                  else _render_text(answer))
            return 0
        if args.cmd == "index-stats":
            engine = _engine(args.kb_config)
            print(json.dumps(engine.kb.stats(), indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "serve":
            engine = _engine(args.kb_config)
            from .server import run_server

            print(f"lab-assist serve di http://{args.host}:{args.port} (mode search-only)")
            run_server(engine, args.host, args.port)
            return 0
    except KBError as e:
        print(f"[KB-ERROR] {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
