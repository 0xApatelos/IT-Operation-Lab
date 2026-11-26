"""Retrieval BM25 (Okapi) — implementasi stdlib-only untuk KB kecil.

Kenapa BM25 sendiri: corpus ~60 chunks; dependensi eksternal (rank_bm25,
sklearn, vektor DB) tidak menambah kualitas yang berarti di skala ini dan
menambah permukaan audit. Skor dipakai untuk ranking + ambang abstain.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .kb import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Stopword minimal (id/en) + kata tanya — tidak membedakan dokumen.
STOPWORDS = frozenset({
    "dan", "di", "dari", "yang", "untuk", "dengan", "pada", "adalah", "ke", "itu", "ini",
    "the", "a", "an", "of", "to", "in", "for", "on", "is", "are",
    "apa", "kenapa", "mengapa", "bagaimana", "how", "what", "why", "cara", "when",
    "juga", "akan", "bisa", "dapat", "tidak", "ada",
    "jika", "atau", "sebagai", "oleh", "lebih", "saya", "kita", "mereka", "anda",
})


def tokenize(text: str) -> list[str]:
    return [
        t for t in _TOKEN_RE.findall(text.lower()) if len(t) >= 2 and t not in STOPWORDS
    ]


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.chunks = chunks
        self.doc_tokens: list[Counter[str]] = []
        self.doc_lens: list[int] = []
        self.df: Counter[str] = Counter()
        for c in chunks:
            counts = Counter(tokenize(f"{c.title} {c.heading} {c.text}"))
            self.doc_tokens.append(counts)
            self.doc_lens.append(sum(counts.values()))
            for term in counts:
                self.df[term] += 1
        self.n = len(chunks)
        self.avgdl = (sum(self.doc_lens) / self.n) if self.n else 0.0

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log((self.n - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        q_terms = [t for t in tokenize(query) if t in self.df]
        if not q_terms:
            return []
        scores: list[float] = []
        for counts, dl in zip(self.doc_tokens, self.doc_lens):
            s = 0.0
            for term in set(q_terms):
                tf = counts.get(term, 0)
                if tf == 0:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += self._idf(term) * (tf * (self.k1 + 1)) / denom
            scores.append(s)
        pairs = [(c, s) for c, s in zip(self.chunks, scores) if s > 0]
        pairs.sort(key=lambda p: p[1], reverse=True)
        return [RetrievedChunk(chunk=c, score=s) for c, s in pairs[:top_k]]
