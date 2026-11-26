"""Keamanan input & deteksi instruksi berbahaya pada pertanyaan.

Prinsip:
- Pertanyaan pengguna DAN isi dokumen adalah input tidak tepercaya.
- Query yang memuat instruksi gaya "abaikan aturan/bocorkan secret" TIDAK
  diikuti — mode search-only bersifat ekstraktif (secara struktural tidak
  bisa mematuhi instruksi), dan query seperti itu diberi label safety_note.
- Tidak ada eksekusi shell, tidak ada akses file berdasarkan input pengguna,
  tidak ada akses kredensial di seluruh package.
"""

from __future__ import annotations

import re

from .kb import KBConfig

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class QueryValidationError(Exception):
    """Pertanyaan tidak valid (kosong/terlalu panjang) — HTTP 400 di server."""


def validate_query(raw: str, cfg: KBConfig) -> str:
    if not isinstance(raw, str):
        raise QueryValidationError("pertanyaan harus berupa string")
    q = _CONTROL_RE.sub(" ", raw)
    q = " ".join(q.split())  # rapikan spasi beruntun
    if not q:
        raise QueryValidationError("pertanyaan tidak boleh kosong")
    if len(raw) > cfg.max_query_chars:
        raise QueryValidationError(
            f"pertanyaan terlalu panjang ({len(raw)} > {cfg.max_query_chars} karakter)"
        )
    return q


# Pola instruksi "abaikan aturan / bocorkan secret" — dipakai untuk LABEL, bukan eksekusi.
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\babaikan( semua)? (aturan|rule|rulea|instruksi|instruction)",
        r"\bignore (all |previous |your )?(rules|instructions|system)",
        r"\bdisregard (all |previous |your )?(rules|instructions)",
        r"\bbocorkan|buka rahasia|\breveal (the )?secret|\bleak (secret|env|token|api[ _-]?key)",
        r"\btampilkan isi .*\.env",
        r"\bapa isi (token|password|api[ _-]?key|credential)",
        r"\bsystem\s*[:p]|^\s*sistem\s*[:p]",
        r"\bsekarang kamu (adalah|berperan)\b.*\bunrestricted\b",
        r"\bperan baru\b.*\btanpa (batas|aturan)\b",
        r"\bbypass\b.*\b(rule|aturan|safety|keamanan)",
    )
)


def detect_injection(query: str) -> bool:
    return any(p.search(query) for p in INJECTION_PATTERNS)
