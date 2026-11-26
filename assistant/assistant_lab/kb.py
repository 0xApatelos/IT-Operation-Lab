"""Knowledge base: index dokumen markdown dari direktori yang DIIZINKAN EKSPLISIT.

Aturan:
- Hanya direktori pada `allowed_dirs` (relatif terhadap repo_root di config)
  yang diindeks — tidak pernah mengindeks seluruh repository otomatis.
- Guard path traversal: setiap allowed dir harus resolve DI DALAM repo_root.
- Hanya file .md; file/direktori tersembunyi dikecualikan. .env, log, dan
  file di luar allowed dirs tidak mungkin terindeks.
- Chunk per heading dengan metadata lengkap + hash (setiap sumber bisa
  ditelusuri ke dokumen asli).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

_H1_RE = re.compile(r"^# (.+)$", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,6}) (.+)$")
_DOC_ID_RE = re.compile(r"(?:RB|INC)-\d{3}[a-z]?")


class KBError(Exception):
    """Konfigurasi knowledge base tidak valid (config/traversal/hilang)."""


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    heading: str
    rel_path: str
    text: str
    content_hash: str


@dataclass(frozen=True)
class KBConfig:
    repo_root: Path
    allowed_dirs: tuple[Path, ...]
    top_k: int
    min_score: float
    max_query_chars: int
    max_chunk_chars: int


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise KBError(msg)


def load_kb_config(path: str | Path) -> KBConfig:
    """Baca + validasi config KB. Traversal/atribut aneh ditolak."""
    p = Path(path).resolve()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise KBError(f"config KB tidak ditemukan: {p}") from e
    except json.JSONDecodeError as e:
        raise KBError(f"config KB bukan JSON valid: {p} ({e})") from e
    _require(isinstance(raw, dict), "config KB harus berupa object")

    cfg_dir = p.parent
    root_raw = raw.get("repo_root", "..")
    _require(isinstance(root_raw, str) and root_raw.strip(), "repo_root wajib string")
    repo_root = (cfg_dir / root_raw).resolve()
    _require(repo_root.is_dir(), f"repo_root tidak ada: {repo_root}")

    dirs_raw = raw.get("allowed_dirs")
    _require(isinstance(dirs_raw, list) and dirs_raw, "allowed_dirs wajib list tidak kosong")
    allowed: list[Path] = []
    for d in dirs_raw:
        _require(isinstance(d, str) and d.strip(), "setiap allowed_dirs wajib string")
        resolved = (repo_root / d).resolve()
        # Guard traversal: harus tetap di dalam repo_root.
        _require(
            resolved == repo_root or resolved.is_relative_to(repo_root),
            f"allowed_dir di luar repo_root (traversal ditolak): {d!r} -> {resolved}",
        )
        _require(resolved.is_dir(), f"allowed_dir tidak ada: {resolved}")
        allowed.append(resolved)

    top_k = raw.get("top_k", 5)
    _require(isinstance(top_k, int) and not isinstance(top_k, bool), "top_k wajib integer")
    _require(1 <= top_k <= 5, "top_k harus 1-5 (batas jumlah chunk)")

    min_score = raw.get("min_score")
    _require(isinstance(min_score, (int, float)) and not isinstance(min_score, bool),
             "min_score wajib angka")
    _require(0 <= float(min_score), "min_score >= 0")

    max_query = raw.get("max_query_chars", 500)
    _require(isinstance(max_query, int) and not isinstance(max_query, bool),
             "max_query_chars wajib integer")
    _require(50 <= max_query <= 2000, "max_query_chars harus 50-2000")

    max_chunk = raw.get("max_chunk_chars", 1200)
    _require(isinstance(max_chunk, int) and not isinstance(max_chunk, bool),
             "max_chunk_chars wajib integer")
    _require(200 <= max_chunk <= 4000, "max_chunk_chars harus 200-4000")

    return KBConfig(
        repo_root=repo_root,
        allowed_dirs=tuple(allowed),
        top_k=top_k,
        min_score=float(min_score),
        max_query_chars=max_query,
        max_chunk_chars=max_chunk,
    )


def _doc_id_for(stem: str) -> str:
    m = _DOC_ID_RE.search(stem)
    return m.group(0).upper() if m else stem.upper()


def _split_long(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


def parse_markdown(path: Path, repo_root: Path, max_chunk_chars: int) -> list[Chunk]:
    """Parse satu file markdown menjadi chunks per heading."""
    text = path.read_text(encoding="utf-8", errors="replace")
    h1 = _H1_RE.search(text)
    title = h1.group(1).strip() if h1 else path.stem
    document_id = _doc_id_for(path.stem)
    rel_path = path.relative_to(repo_root).as_posix()

    # Pecah per heading (## ke ###), pertahankan teks intro di bawah judul.
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    heading = title  # intro sebelum heading pertama memakai judul dokumen
    buf: list[str] = []
    for line in lines:
        m = _HEADING_RE.match(line)
        if m and len(m.group(1)) >= 2:  # ## ke bawah
            if any(s.strip() for s in buf):
                sections.append((heading, buf))
            heading = m.group(2).strip()
            buf = [line]
        else:
            buf.append(line)
    if any(s.strip() for s in buf):
        sections.append((heading, buf))

    chunks: list[Chunk] = []
    seq = 0
    for heading, body in sections:
        chunk_text = "\n".join(body).strip()
        if len(chunk_text) < 30:  # buang section kosong (mis. hanya judul)
            continue
        for piece in _split_long(chunk_text, max_chunk_chars):
            h = hashlib.sha256(piece.encode("utf-8")).hexdigest()[:16]
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}:{seq:02d}",
                    document_id=document_id,
                    title=title,
                    heading=heading,
                    rel_path=rel_path,
                    text=piece,
                    content_hash=h,
                )
            )
            seq += 1
    return chunks


class KnowledgeBase:
    """Bangun index dari config. build() dipanggil eksplisit agar mudah dites."""

    def __init__(self, cfg: KBConfig) -> None:
        self.cfg = cfg
        self.chunks: list[Chunk] = []
        self.documents: dict[str, list[Chunk]] = {}
        self.excluded = 0

    def build(self) -> KnowledgeBase:
        chunks: list[Chunk] = []
        for d in self.cfg.allowed_dirs:
            for f in sorted(d.rglob("*.md")):
                if f.name.startswith(".") or any(part.startswith(".") for part in f.parts):
                    self.excluded += 1
                    continue
                chunks.extend(parse_markdown(f, self.cfg.repo_root, self.cfg.max_chunk_chars))
        if not chunks:
            raise KBError("knowledge base kosong — tidak ada dokumen yang terindeks")
        self.chunks = chunks
        self.documents = {}
        for c in chunks:
            self.documents.setdefault(c.document_id, []).append(c)
        return self

    def stats(self) -> dict:
        return {
            "chunks": len(self.chunks),
            "documents": len(self.documents),
            "doc_ids": sorted(self.documents.keys()),
            "allowed_dirs": [str(d) for d in self.cfg.allowed_dirs],
            "excluded_hidden_files": self.excluded,
        }
