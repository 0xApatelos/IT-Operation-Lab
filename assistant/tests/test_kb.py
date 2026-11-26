"""Unit test knowledge base: chunking, metadata, traversal guard."""

from __future__ import annotations

import pytest

from assistant_lab.kb import KBError, KnowledgeBase, load_kb_config, parse_markdown
from tests.conftest import RB_DOC, make_kb


def test_parse_chunks_have_metadata(tmp_path):
    p = tmp_path / "RB-990-service-down.md"
    p.write_text(RB_DOC, encoding="utf-8")
    chunks = parse_markdown(p, tmp_path, max_chunk_chars=1200)
    assert chunks, "harus menghasilkan chunks"
    c0 = chunks[0]
    assert c0.document_id == "RB-990"
    assert c0.title.startswith("RB-990 — Runbook")
    assert c0.chunk_id == "RB-990:00"
    assert c0.content_hash and len(c0.content_hash) == 16
    headings = [c.heading for c in chunks]
    assert any("Pemicu" in h for h in headings)


def test_long_section_is_split(tmp_path):
    doc = "# INC-992 — Panjang\n\n## Bagian\n\n" + ("\n".join(f"- baris {i}" for i in range(200)))
    p = tmp_path / "INC-992-long.md"
    p.write_text(doc, encoding="utf-8")
    chunks = parse_markdown(p, tmp_path, max_chunk_chars=400)
    assert len(chunks) > 1
    assert all(len(c.text) <= 400 for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)  # chunk_id unik


def test_traversal_dir_rejected(tmp_path):
    cfg_path = make_kb(tmp_path, with_ignore_doc=False)
    raw = cfg_path.read_text(encoding="utf-8")
    import json

    cfg = json.loads(raw)
    cfg["allowed_dirs"] = ["../../etc"]
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(KBError, match="traversal"):
        load_kb_config(cfg_path)


def test_missing_dir_rejected(tmp_path):
    cfg_path = make_kb(tmp_path, with_ignore_doc=False)
    import json

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["allowed_dirs"] = ["docs/tidak-ada"]
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(KBError, match="tidak ada"):
        load_kb_config(cfg_path)


def test_only_md_and_non_hidden_indexed(tmp_path):
    cfg_path = make_kb(tmp_path, with_ignore_doc=False)
    repo = (cfg_path.parent / "..").resolve()
    (repo / "docs" / "runbooks" / ".hidden.md").write_text("# Rahasia", encoding="utf-8")
    (repo / "docs" / "runbooks" / "notes.txt").write_text("# bukan md", encoding="utf-8")
    kb = KnowledgeBase(load_kb_config(cfg_path)).build()
    assert all(c.rel_path.endswith(".md") for c in kb.chunks)
    assert not any(".hidden" in c.rel_path for c in kb.chunks)
    assert kb.excluded >= 1


def test_empty_corpus_rejected(tmp_path):
    cfg_path = make_kb(tmp_path, with_ignore_doc=False)
    repo = (cfg_path.parent / "..").resolve()
    for f in (repo / "docs" / "runbooks").glob("*.md"):
        f.unlink()
    for f in (repo / "docs" / "incidents").glob("*.md"):
        f.unlink()
    with pytest.raises(KBError, match="kosong"):
        KnowledgeBase(load_kb_config(cfg_path)).build()
