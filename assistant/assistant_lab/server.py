"""FastAPI server untuk assistant (mode `serve`).

- Default bind 127.0.0.1 (akses lokal). Mengexpose ke jaringan = keputusan
  sadar pemilik repo (risiko didokumentasikan di assistant/README.md §Security).
- Batasan: panjang query, jumlah chunk (top_k di config), payload kecil.
- Citation dire-validasi terhadap hasil retrieval sebelum dikirim.
- UI: satu halaman HTML inline; SEMUA request memakai URL RELATIF (fetch
  '/api/query') — tidak ada URL localhost/absolute yang ditanam di browser.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from . import __version__
from .answer import AnswerEngine
from .security import QueryValidationError

log = logging.getLogger("assistant_lab.server")


def create_app(engine: AnswerEngine) -> FastAPI:
    app = FastAPI(title="lab-assist", version=__version__, docs_url=None, redoc_url=None)
    kb_stats = engine.kb.stats()

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "mode": "search-only",
            "assistant_version": __version__,
            "kb": kb_stats,
        }

    @app.post("/api/query")
    async def api_query(request: Request) -> dict:
        try:
            body = await request.json()
        except ValueError:  # json.JSONDecodeError adalah subclass ValueError
            return {"error": "invalid_json", "detail": "body harus JSON valid"}
        if not isinstance(body, dict) or "question" not in body:
            return {"error": "invalid_request", "detail": "field 'question' wajib"}
        try:
            answer = engine.query(body["question"])
        except QueryValidationError as e:
            return {"error": "invalid_query", "detail": str(e)}
        # Re-validasi citation: hanya chunk dari retrieval yang boleh tampil.
        if not engine.validate_citations(answer):
            log.error("citation validation gagal — jawaban tidak dikirim")
            return {"error": "internal", "detail": "citation validation failed"}
        # Privasi log: catat panjang + status, bukan isi pertanyaan.
        log.info(
            "query ok: len=%d status=%s citations=%d",
            len(answer["query"]),
            answer["status"],
            len(answer["citations"]),
        )
        return answer

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _UI_HTML

    return app


_UI_HTML = """<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lab-assist — search-only helpdesk</title>
<style>
  :root { --ink:#1f2a3a; --line:#d9e2ec; --accent:#35659c; --warn:#b03a3a; --ok:#2f7d4f; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,Segoe UI,sans-serif; color:var(--ink); background:#f5f8fc; }
  .wrap { max-width:760px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:20px; margin:0 0 4px; }
  .sub { color:#5a6b80; font-size:13px; margin-bottom:16px; }
  .banner { background:#eaf2fb; border:1px solid var(--line); border-radius:8px;
            padding:10px 12px; font-size:12.5px; margin-bottom:16px; }
  .row { display:flex; gap:8px; }
  input { flex:1; padding:10px 12px; border:1px solid var(--line); border-radius:8px; font-size:14px; }
  button { padding:10px 16px; border:0; border-radius:8px; background:var(--accent);
           color:#fff; font-size:14px; cursor:pointer; }
  button:disabled { opacity:.5; cursor:default; }
  .card { background:#fff; border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; margin-top:14px; }
  .card h3 { margin:0 0 8px; font-size:14px; }
  .status-answered { color:var(--ok); font-weight:600; }
  .status-insufficient_evidence { color:var(--warn); font-weight:600; }
  ul { margin:6px 0 0 18px; padding:0; }
  li { margin:4px 0; font-size:13.5px; line-height:1.45; }
  .cite { font-size:12.5px; color:#5a6b80; margin-top:4px; }
  .note { background:#fdecec; border:1px solid #f0c4c4; border-radius:8px;
          padding:8px 10px; font-size:12.5px; margin-top:10px; }
  .limit { color:#5a6b80; font-size:12.5px; margin-top:8px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>lab-assist</h1>
  <div class="sub">Search-only helpdesk untuk runbook lab (Tahap A — tanpa LLM).</div>
  <div class="banner">
    Mode <b>search-only</b>: jawaban adalah potongan dokumen dengan kutipan sumber.
    Assistant <b>tidak mengeksekusi perintah</b>, tidak mengubah sistem, dan tidak
    mengetahui kondisi server saat ini.
  </div>
  <div class="row">
    <input id="q" placeholder="mis. layanan demo-http berhenti, disk melewati ambang, resolusi DNS gagal..."
           maxlength="500">
    <button id="go">Cari</button>
  </div>
  <div id="out"></div>
</div>
<script>
const btn = document.getElementById('go');
const inp = document.getElementById('q');
const out = document.getElementById('out');
function esc(s){ const d=document.createElement('div'); d.textContent=String(s??''); return d.innerHTML; }
function list(items){ return items && items.length ? '<ul>'+items.map(i=>'<li>'+esc(i)+'</li>').join('')+'</ul>' : ''; }
async function ask(){
  const q = inp.value.trim();
  if(!q){ return; }
  btn.disabled = true; btn.textContent='Mencari...';
  try {
    const r = await fetch('/api/query', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({question: q})
    });
    const a = await r.json();
    if(a.error){ out.innerHTML = '<div class="card"><h3 class="status-insufficient_evidence">Permintaan ditolak</h3><div>'+esc(a.detail)+'</div></div>'; return; }
    let html = '<div class="card">';
    html += '<h3>Status: <span class="status-'+esc(a.status)+'">'+esc(a.status)+'</span></h3>';
    if(a.summary) html += '<div><b>'+esc(a.summary)+'</b></div>';
    if(a.safety_note) html += '<div class="note">'+esc(a.safety_note)+'</div>';
    html += '<h3 style="margin-top:12px">Langkah diagnostik (dari dokumen)</h3>'+list(a.diagnostic_steps);
    if(a.warnings && a.warnings.length){
      html += '<h3 style="margin-top:12px">Peringatan dari dokumen</h3>'+list(a.warnings);
    }
    if(a.follow_up_questions && a.follow_up_questions.length){
      html += '<h3 style="margin-top:12px">Info yang perlu diklarifikasi</h3>'+list(a.follow_up_questions);
    }
    if(a.citations && a.citations.length){
      html += '<h3 style="margin-top:12px">Sumber</h3><ul>'+a.citations.map(c=>
        '<li class="cite">'+esc(c.document_id)+' · '+esc(c.heading)+' · '+esc(c.path)+
        ' · chunk '+esc(c.chunk_id)+' · skor '+esc(c.score)+'</li>').join('')+'</ul>';
    }
    if(a.limitations && a.limitations.length){
      html += '<div class="limit">'+a.limitations.map(l=>esc(l)).join(' ')+'</div>';
    }
    html += '</div>';
    out.innerHTML = html;
  } catch(e) {
    out.innerHTML = '<div class="card"><h3 class="status-insufficient_evidence">Gagal menghubungi backend</h3></div>';
  } finally { btn.disabled=false; btn.textContent='Cari'; }
}
btn.addEventListener('click', ask);
inp.addEventListener('keydown', e=>{ if(e.key==='Enter') ask(); });
</script>
</body>
</html>
"""


def run_server(engine: AnswerEngine, host: str, port: int) -> None:
    import uvicorn

    app = create_app(engine)
    uvicorn.run(app, host=host, port=port, log_level="warning")
