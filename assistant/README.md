# assistant/ — AI Helpdesk Assistant (Fase 3, Tahap A)

Documentation-grounded assistance untuk runbook lab: pengguna mencari langkah
troubleshooting dan mendapat **potongan dokumen dengan kutipan sumber**.
Mode saat ini: **search-only** (retrieval BM25, tanpa LLM) — bukan chatbot
generatif.

## Status

| Bagian | Status |
|---|---|
| KB builder (explicit dirs, chunk+metadata+hash, guard traversal) | implemented + tested |
| Retrieval BM25 stdlib-only (top-k + ambang abstain) | implemented + tested |
| Jawaban ekstraktif (summary/steps/warnings/follow-ups/citations) | implemented + tested |
| Deteksi & label query injection (tidak diikuti, bukan dieksekusi) | implemented + tested |
| Validasi citation terhadap hasil retrieval | implemented + tested |
| FastAPI server + UI satu halaman (URL relatif, bind lokal default) | implemented + tested |
| Evaluasi 21 kasus sintetis + runner + laporan | implemented + tested (hasil: `evaluation/report.md`) |
| Adapter model Tahap B (provider lokal/API) | planned — interface siap, `OpenAICompatibleAdapter` sengaja menolak berjalan |

## Cara kerja (Tahap A)

```
query → validasi (panjang ≤ 500, kontrol chars dibersihkan)
      → deteksi instruksi injection (label safety_note, TIDAK diikuti)
      → BM25 search pada chunks KB (top_k ≤ 5)
      → skor top-1 < min_score → status insufficient_evidence (abstain)
      → skor ≥ min_score → jawaban EKSTRAKTIF dari dokumen:
          summary / diagnostic_steps / warnings (verbatim dari teks)
          + citations (chunk_id, doc, heading, path, skor)
```

Jaminan struktural: tidak ada langkah yang bisa muncul tanpa ada di teks
dokumen; citation hanya dibangun dari chunk hasil retrieval; pertanyaan di
luar cakupan → abstain, bukan prosedur dikarang. Assistant **tidak
mengeksekusi perintah, tidak mengubah sistem, tidak mengetahui kondisi server**.

## Install & jalankan

```bash
cd it-operations-ai-lab
python3 -m venv .venv
.venv/bin/pip install -e 'assistant[dev]'     # fastapi/uvicorn hanya untuk `serve`
.venv/bin/lab-assist index-stats
.venv/bin/lab-assist query "layanan demo-http berhenti bagaimana diagnosisnya?"
.venv/bin/lab-assist serve                    # UI di http://127.0.0.1:8077
```

CLI `query` bekerja tanpa fastapi (import lazy). `python3 -m assistant_lab`
juga didukung.

## Knowledge base

Didefinisikan **eksplisit** di `kb.config.json`:

| Key | Nilai | Catatan |
|---|---|---|
| `allowed_dirs` | `docs/runbooks`, `docs/incidents` | hanya 2 direktori ini diindeks; seluruh repo TIDAK |
| `repo_root` | `..` | guard traversal: allowed dir wajib di dalam root |
| `top_k` | 5 (maks 5) | batas jumlah chunk |
| `min_score` | 8.0 | ambang abstain (kalibrasi: titik tengah gap skor out-of-scope 5.69 vs answerable 10.54) |
| `max_query_chars` | 500 | batas input |
| `max_chunk_chars` | 1200 | chunk panjang dipecah |
| `exclude_globs` | `["*.en.md"]` | mirror terjemahan dikeluarkan dari KB — KB hanya memuat dokumen sumber kebenaran (D17) |

Metadata tiap chunk: `document_id` (RB-xxx/INC-xxx), `title`, `rel_path`,
`heading`, `chunk_id`, `content_hash` (sha256 16 hex) — setiap kutipan bisa
ditelusuri ke dokumen asli.

## Evaluasi (Tahap A)

```bash
python3 assistant/evaluation/evaluate.py     # → evaluation/report.json + report.md
```

21 kasus sintetis: 9 answerable, 4 out-of-scope, 4 ambiguous, 4 injection
(`evaluation/cases.json`, tiap kasus dengan rubrik). Hasil run (sandbox,
2026-11-26): hit@k 0.889, citation validity 1.0, abstain out-of-scope 1.0,
safety note injection 1.0, latensi p50 0.14 ms / p95 0.34 ms (n=21, indikatif),
token/biaya N/A (tanpa provider). Angka ini **bukan** "akurasi AI" — retrieval
dan perilaku diukur terpisah; penilaian isi penuh tetap rubrik manual.

Catatan kejujuran: kasus A8 tidak hit (retrieved INC-001+INC-005; expected
RB-001/INC-004). INC-001 yang ter-retrieve sebenarnya memuat petunjuk
reinstall (§14) — ekspektasi kasus terlalu sempit. Dibiarkan apa adanya agar
angka tidak di-tuning setelah melihat hasil.

## Keamanan

- Pertanyaan & isi dokumen = **input tidak tepercaya**. Mode ekstraktif tidak
  bisa "mematuhi" instruksi injection; query berpola injection tetap dideteksi
  dan diberi `safety_note`.
- Dokumen fixture berisi instruksi "IGNORE ALL PREVIOUS RULES" diuji: konten
  hanya tampil verbatim sebagai potongan dokumen dengan citation, tidak pernah
  menjadi instruksi baru.
- Citation dire-validasi di server sebelum dikirim; tanpa shell execution,
  tanpa akses file berdasarkan input, tanpa akses kredensial.
- Batasan: panjang input 500, top_k ≤ 5, payload kecil, log server hanya
  mencatat panjang & status query (bukan isinya).
- **Bind default 127.0.0.1**. Expose ke jaringan (mis. `--host 0.0.0.0`) =
  keputusan sadar pemilik repo dengan risiko: semua orang di jaringan dapat
  membaca isi runbook; tidak ada autentikasi pada MVP. UI memakai URL relatif
  (tanpa URL localhost tertanam) sehingga aman di-balik proxy preview.

## Testing

```bash
python3 -m pytest assistant/tests      # unit (mini corpus tmp, deterministik)
python3 -m ruff check assistant/assistant_lab assistant/tests assistant/evaluation
```

## Tahap B (planned)

Adapter provider (lokal/API) dengan: API key hanya dari environment
(`LAB_ASSIST_API_KEY`), config biaya wajib dari sumber resmi (model, tarif per
1K token, tanggal tarif), usage token dilaporkan dari response provider. Mode
offline tetap fungsional tanpa API key. Lihat docstring
`assistant_lab/model_adapter.py` — sampai diimplementasikan, adapter provider
menolak berjalan secara eksplisit (bukan diam-diam).
