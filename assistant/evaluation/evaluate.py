"""Runner evaluasi Tahap A (search-only).

Menghitung & melaporkan (jujur, tanpa satu angka "akurasi AI"):
1. Retrieval hit rate pada top-k (dokumen yang diharapkan muncul di hasil).
2. Validitas kutipan: chunk_id citations berasal dari hasil retrieval.
3. Konten: sinyal expected_points (informative; penilaian penuh tetap manual).
4. Perilaku abstain pada kategori out-of-scope.
5. Hasil kasus keamanan (safety_note untuk injection).
6. Latensi p50/p95: time.perf_counter per kasus, n = jumlah kasus (kecil ->
   indikatif, bukan benchmark).
7. Token/usage: N/A (mode search-only, tanpa provider).
8. Biaya: N/A (tanpa provider; tidak ada angka harga yang dikarang).

Exit code: 1 bila ekspektasi keamanan/abstain dilanggar; 0 selain itu.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # direktori assistant/

from assistant_lab import __version__
from assistant_lab.answer import AnswerEngine


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * pct / 100
    f, c = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _content_signal(answer: dict, points: list[str]) -> float | None:
    if not points:
        return None
    hay = " ".join(
        [answer.get("summary") or "", " ".join(answer.get("diagnostic_steps", [])),
         " ".join(answer.get("warnings", []))]
    ).lower()
    hits = sum(1 for p in points if p.lower() in hay)
    return round(hits / len(points), 3)


def run_evaluation(kb_config: Path, cases_path: Path, out_dir: Path) -> tuple[dict, int]:
    engine = AnswerEngine.from_config(kb_config)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    stats = engine.kb.stats()
    kb_hash = hashlib.sha256("".join(c.content_hash for c in engine.kb.chunks).encode()).hexdigest()[:16]

    rows: list[dict] = []
    latencies: list[float] = []
    violations: list[str] = []

    for case in cases:
        t0 = time.perf_counter()
        answer = engine.query(case["question"])
        dt_ms = (time.perf_counter() - t0) * 1000
        latencies.append(dt_ms)

        rubric = case["rubric"]
        docs_hit = set(answer["retrieval"]["documents_hit"])
        expected_docs = set(case["expected_doc_ids"] or [])
        hit = bool(expected_docs & docs_hit) if expected_docs else None
        abstained = answer["status"] == "insufficient_evidence"
        citation_valid = engine.validate_citations(answer)

        if rubric["abstain_expected"] and not abstained:
            violations.append(f"{case['id']}: diharapkan abstain tetapi status={answer['status']}")
        if rubric["safety_note_expected"] and answer["safety_note"] is None:
            violations.append(f"{case['id']}: safety_note tidak muncul pada kasus injection")
        if not citation_valid:
            violations.append(f"{case['id']}: citation validasi gagal")

        rows.append({
            "id": case["id"],
            "category": case["category"],
            "status": answer["status"],
            "latency_ms": round(dt_ms, 2),
            "hit": hit,
            "abstained": abstained,
            "safety_note_present": answer["safety_note"] is not None,
            "citation_valid": citation_valid,
            "content_signal": _content_signal(answer, case["expected_points"]),
            "documents_hit": sorted(docs_hit),
            "expected_doc_ids": case["expected_doc_ids"],
        })

    answerable = [r for r in rows if r["category"] == "answerable"]
    out_of_scope = [r for r in rows if r["category"] == "out-of-scope"]
    injection = [r for r in rows if r["category"] == "injection"]
    hits = [r["hit"] for r in answerable if r["hit"] is not None]
    signals = [r["content_signal"] for r in rows if r["content_signal"] is not None]
    lat_sorted = sorted(latencies)

    metrics = {
        "report_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "assistant_version": __version__,
        "mode": "search-only (Tahap A, tanpa LLM)",
        "kb": {**stats, "kb_content_hash": kb_hash},
        "config": {
            "kb_config": str(kb_config),
            "top_k": engine.cfg.top_k,
            "min_score": engine.cfg.min_score,
            "max_query_chars": engine.cfg.max_query_chars,
        },
        "metrics": {
            "retrieval_hit_rate_topk": {
                "value": round(sum(hits) / len(hits), 3) if hits else None,
                "n_answerable": len(hits),
                "definition": "expected_doc_ids muncul di dokumen hasil retrieval top-k",
            },
            "citation_validity": {
                "value": round(sum(1 for r in rows if r["citation_valid"]) / len(rows), 3),
                "definition": "semua chunk_id pada citations berasal dari hasil retrieval",
            },
            "abstain_on_out_of_scope": {
                "value": round(sum(1 for r in out_of_scope if r["abstained"]) / len(out_of_scope), 3)
                if out_of_scope else None,
                "n": len(out_of_scope),
            },
            "safety_note_on_injection": {
                "value": round(sum(1 for r in injection if r["safety_note_present"]) / len(injection), 3)
                if injection else None,
                "n": len(injection),
            },
            "content_signal_expected_points": {
                "value": round(sum(signals) / len(signals), 3) if signals else None,
                "definition": "informative: fraksi expected_points muncul pada summary+steps+warnings; penilaian isi penuh tetap rubrik manual",
            },
            "latency_ms": {
                "p50": round(_percentile(lat_sorted, 50), 2),
                "p95": round(_percentile(lat_sorted, 95), 2),
                "n": len(lat_sorted),
                "method": "time.perf_counter di sekitar pipeline penuh per kasus; jumlah sampel kecil -> indikatif",
            },
            "token_usage": {"value": "N/A", "reason": "mode search-only tanpa provider; tidak ada pemakaian token"},
            "cost_estimate": {"value": "N/A", "reason": "tanpa provider API; tidak ada angka harga yang dikarang"},
        },
        "safety_violations": violations,
        "cases": rows,
    }

    exit_code = 1 if violations else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "report.md").write_text(_render_markdown(metrics), encoding="utf-8")
    return metrics, exit_code


def _render_markdown(m: dict) -> str:
    mt = m["metrics"]
    lines = [
        "# Laporan evaluasi assistant (Tahap A — search-only)",
        "",
        (f"- Dibuat: {m['generated_at']} (UTC) · versi assistant: {m['assistant_version']}"),
        ("- Mode: " + m["mode"] + " — hasil ini **bukan** angka 'akurasi AI'; "
         "retrieval dan perilaku diukur terpisah."),
        (f"- KB: {m['kb']['chunks']} chunks dari {m['kb']['documents']} dokumen "
         f"({', '.join(m['kb']['doc_ids'])}) · hash konten KB: `{m['kb']['kb_content_hash']}`"),
        (f"- Konfigurasi: top_k={m['config']['top_k']}, min_score={m['config']['min_score']}, "
         f"max_query_chars={m['config']['max_query_chars']}"),
        "",
        "## Metrik",
        "",
        (f"1. **Retrieval hit rate @top-k**: {mt['retrieval_hit_rate_topk']['value']} "
         f"(n={mt['retrieval_hit_rate_topk']['n_answerable']} kasus answerable) — "
         f"{mt['retrieval_hit_rate_topk']['definition']}"),
        (f"2. **Validitas kutipan**: {mt['citation_validity']['value']} — "
         f"{mt['citation_validity']['definition']}"),
        (f"3. **Abstain pada out-of-scope**: {mt['abstain_on_out_of_scope']['value']} "
         f"(n={mt['abstain_on_out_of_scope']['n']})"),
        (f"4. **Safety note pada injection**: {mt['safety_note_on_injection']['value']} "
         f"(n={mt['safety_note_on_injection']['n']})"),
        (f"5. **Sinyal konten expected_points**: {mt['content_signal_expected_points']['value']} — "
         f"{mt['content_signal_expected_points']['definition']}"),
        (f"6. **Latensi** p50={mt['latency_ms']['p50']} ms, p95={mt['latency_ms']['p95']} ms "
         f"(n={mt['latency_ms']['n']}; {mt['latency_ms']['method']})"),
        (f"7. **Token usage**: {mt['token_usage']['value']} — {mt['token_usage']['reason']}"),
        (f"8. **Estimasi biaya**: {mt['cost_estimate']['value']} — {mt['cost_estimate']['reason']}"),
        "",
        "## Per-case",
        "",
        "| ID | Kategori | Status | Hit | Abstain | safety_note | Signal | Latensi ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in m["cases"]:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['status']} | {r['hit']} | {r['abstained']} "
            f"| {r['safety_note_present']} | {r['content_signal']} | {r['latency_ms']} |"
        )
    lines += [
        "",
        "## Keterbatasan pelaporan",
        "",
        "- Jumlah sampel kecil (21 kasus sintetis) — angka latensi dan hit rate indikatif, bukan benchmark.",
        "- Ambang `min_score` dikalibrasi pada run dev terpisah (melihat distribusi skor kasus answerable vs out-of-scope), lalu diuji pada kasus ini; bukan set validasi independen.",
        "- Hasil hanya untuk mode search-only; belum mencakup mode model lokal/API (Tahap B, planned).",
        "- Sinyal konten otomatis bersifat informatif; penilaian dukungan isi jawaban penuh menggunakan rubrik manual di cases.json.",
        "- Eksekusi pada sandbox dev (bukan VM lab) — lihat docs/evidence/ untuk konteks.",
        "",
        f"**Pelanggaran keamanan/abstain**: {m['safety_violations'] if m['safety_violations'] else 'tidak ada'}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Runner evaluasi assistant Tahap A")
    parser.add_argument("--kb-config", default=str(base.parent / "kb.config.json"))
    parser.add_argument("--cases", default=str(base / "cases.json"))
    parser.add_argument("--out-dir", default=str(base))
    args = parser.parse_args()

    metrics, exit_code = run_evaluation(Path(args.kb_config), Path(args.cases), Path(args.out_dir))
    mt = metrics["metrics"]
    print(f"hit@k={mt['retrieval_hit_rate_topk']['value']} "
          f"citation_valid={mt['citation_validity']['value']} "
          f"abstain={mt['abstain_on_out_of_scope']['value']} "
          f"safety={mt['safety_note_on_injection']['value']} "
          f"p50={mt['latency_ms']['p50']}ms p95={mt['latency_ms']['p95']}ms "
          f"violations={len(metrics['safety_violations'])}")
    if metrics["safety_violations"]:
        for v in metrics["safety_violations"]:
            print(f"  VIOLATION: {v}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
