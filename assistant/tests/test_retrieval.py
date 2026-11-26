"""Unit test retrieval BM25: ranking, top_k, deterministik."""

from __future__ import annotations

from assistant_lab.retrieval import tokenize


def test_tokenize_filters_stopwords_and_short():
    toks = tokenize("Cara periksa DNS yang gagal di port 8080")
    assert "cara" not in toks and "yang" not in toks and "di" not in toks
    assert "dns" in toks and "gagal" in toks and "8080" in toks and "port" in toks


def test_ranking_relevant_doc_first(mini_engine):
    result = mini_engine.query("kapasitas disk melewati ambang")
    docs = result["retrieval"]["documents_hit"]
    assert docs, "harus ada hasil"
    assert "INC-990" in docs[:2]


def test_top_k_limit(mini_engine):
    retrieved = mini_engine.index.search("layanan demo-x berhenti systemd journalctl", top_k=2)
    assert len(retrieved) <= 2


def test_no_match_returns_empty(mini_engine):
    assert mini_engine.index.search("zzzz qqqq xxxx", top_k=3) == []
