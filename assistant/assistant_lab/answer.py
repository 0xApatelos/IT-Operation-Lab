"""AnswerEngine — pipeline search-only: query -> retrieval -> jawaban ekstraktif.

Jaminan desain (Tahap A, tanpa LLM):
- Semua kalimat jawaban berasal dari teks dokumen (ekstraktif) atau dari
  template meta (status/limitasi) yang TIDAK berisi prosedur teknis.
- Citation hanya dibangun dari chunk hasil retrieval (validasi struktural),
  dan server melakukan re-validasi sebelum menampilkan.
- Tidak mengeksekusi perintah, tidak mengubah sistem, tidak mengklaim
  mengetahui kondisi server.
- Pertanyaan di luar cakupan dokumen -> status `insufficient_evidence`
  (abstain), bukan prosedur yang dikarang.
"""

from __future__ import annotations

import re

from . import __version__
from .kb import KnowledgeBase
from .retrieval import BM25Index, RetrievedChunk
from .security import detect_injection, validate_query

_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$")
_WARN_RE = re.compile(r"peringatan|warning|jangan|risiko|keselamatan|safety|awas", re.IGNORECASE)

MAX_STEPS = 6
MAX_WARNINGS = 3


class AnswerEngine:
    def __init__(self, kb: KnowledgeBase, index: BM25Index) -> None:
        self.kb = kb
        self.index = index
        self.cfg = kb.cfg

    @classmethod
    def from_config(cls, config_path: str) -> AnswerEngine:
        from .kb import load_kb_config

        cfg = load_kb_config(config_path)
        kb = KnowledgeBase(cfg).build()
        return cls(kb, BM25Index(kb.chunks))

    def query(self, raw: str) -> dict:
        q = validate_query(raw, self.cfg)
        injected = detect_injection(q)
        retrieved = self.index.search(q, self.cfg.top_k)
        top_score = retrieved[0].score if retrieved else 0.0
        threshold_met = bool(retrieved) and top_score >= self.cfg.min_score
        citations = [
            {
                "chunk_id": rc.chunk.chunk_id,
                "document_id": rc.chunk.document_id,
                "title": rc.chunk.title,
                "heading": rc.chunk.heading,
                "path": rc.chunk.rel_path,
                "score": round(rc.score, 3),
            }
            for rc in retrieved
        ]

        status = "answered" if threshold_met else "insufficient_evidence"
        data: dict = {
            "mode": "search-only",
            "assistant_version": __version__,
            "status": status,
            "query": q,
            "safety_note": None,
            "summary": None,
            "diagnostic_steps": [],
            "warnings": [],
            "follow_up_questions": [],
            "limitations": [],
            "citations": citations,
            "retrieval": {
                "top_k": self.cfg.top_k,
                "min_score": self.cfg.min_score,
                "returned_chunks": len(retrieved),
                "top_score": round(top_score, 3),
                "documents_hit": sorted({rc.chunk.document_id for rc in retrieved}),
            },
        }

        if injected:
            data["safety_note"] = (
                "Pertanyaan memuat instruksi seperti 'abaikan aturan' atau permintaan "
                "mengakses secret — instruksi seperti itu TIDAK diikuti. Jawaban hanya "
                "berupa potongan dokumentasi dengan kutipan sumber."
            )

        if threshold_met:
            data["summary"] = self._summary(retrieved)
            data["diagnostic_steps"] = self._steps(retrieved)
            data["warnings"] = self._warnings(retrieved)
        else:
            data["limitations"].append(
                "Dokumentasi yang tersedia belum cukup untuk menjawab pertanyaan ini. "
                "Tidak ada prosedur yang dikarang untuk mengisi kekosongan."
            )

        data["follow_up_questions"] = self._follow_ups(status, retrieved, q)
        data["limitations"].append(
            "Mode search-only: potongan dokumen, bukan jawaban generatif. Assistant tidak "
            "mengeksekusi perintah, tidak mengubah sistem, dan tidak mengetahui kondisi "
            "server saat ini."
        )
        return data

    # --- ekstraksi (semua teks diambil verbatim dari dokumen) ----------------

    def _summary(self, retrieved: list[RetrievedChunk]) -> str:
        top = retrieved[0].chunk
        first_line = next((l for l in top.text.splitlines() if l.strip()), "")
        first_line = first_line.lstrip("#").strip()
        return f"{top.title} › {top.heading} — {first_line[:160]}"

    def _steps(self, retrieved: list[RetrievedChunk]) -> list[str]:
        steps: list[str] = []
        for rc in retrieved:
            for line in rc.chunk.text.splitlines():
                m = _LIST_ITEM_RE.match(line)
                if m:
                    item = m.group(1).strip()
                    if item and item not in steps:
                        steps.append(item)
                        if len(steps) >= MAX_STEPS:
                            return steps
        return steps

    def _warnings(self, retrieved: list[RetrievedChunk]) -> list[str]:
        warns: list[str] = []
        for rc in retrieved[:2]:  # hanya dari 2 chunk teratas agar relevan
            for line in rc.chunk.text.splitlines():
                s = line.strip()
                if s and _WARN_RE.search(s) and s not in warns:
                    warns.append(s)
                    if len(warns) >= MAX_WARNINGS:
                        return warns
        return warns

    def _follow_ups(self, status: str, retrieved: list[RetrievedChunk], q: str) -> list[str]:
        docs = sorted({rc.chunk.document_id for rc in retrieved})
        if status == "insufficient_evidence":
            return [
                "Layanan/host mana yang dimaksud?",
                "Apa pesan error atau gejala persisnya?",
                "Kapan masalah mulai muncul?",
            ]
        if len(docs) > 1:
            return [
                f"Skenario mana yang cocok dengan kondisi Anda? Dokumen kandidat: {', '.join(docs)}.",
                "Apa pesan error persisnya yang terlihat?",
            ]
        return []

    # --- validasi citation (mencegah kutipan di luar hasil retrieval) ---------

    def validate_citations(self, answer: dict) -> bool:
        """Semua chunk_id pada citations harus ada di hasil retrieval terakhir."""
        valid = {c["chunk_id"] for c in answer.get("citations", [])}  # citations dibangun dari retrieved
        retrieved_ids = {rc.chunk.chunk_id for rc in self.index.search(
            answer["query"], self.cfg.top_k
        )}
        return valid.issubset(retrieved_ids)
