# Indeks skenario insiden

Format dokumen insiden mengikuti template 16 bagian (lihat INC-001).
Setiap insiden punya guard keselamatan eksplisit dan tidak menyentuh
DNS/firewall/permission/layanan host utama.

| ID | Judul | Status | Pendekatan simulasi |
|---|---|---|---|
| INC-001 | Layanan berhenti (`demo-http`) | implemented + tested (sandbox) · requires manual verification (VM) | `simulate_service_down.sh` → `systemctl stop demo-http` |
| INC-002 | Kapasitas disk melewati ambang | implemented + tested (sandbox) · requires manual verification (VM) | fixture **tmpfs disposable 32 MB** di `/mnt/lab-disk-fixture` — **tidak** mengisi root fs |
| INC-003 | Resolusi DNS gagal | implemented + tested (sandbox, Level A: nama `.invalid`, tanpa ubah resolver) · Level B (resolver di VM disposable) requires manual verification | `DNS_HOST=nonexistent.invalid bash baseline.sh` |
| INC-004 | Permission file salah | implemented + tested (sandbox) · requires manual verification (VM) | `chmod 000` pada file aplikasi lab (`/opt/demo-http/…`, path tetap) → restart gagal → kembalikan `chmod 755` |
| INC-005 | Konektivitas/port layanan gagal | implemented + tested (sandbox) · requires manual verification (VM) | instance lab liar menempati port 8080 (squatter terverifikasi cmdline) → unit gagal bind → bersihkan |

Status definisi: `implemented`/`tested`/`simulated`/`requires manual
verification`/`planned` — lihat `docs/security/safety-rules.md` §3.

Urutan pengerjaan mengikuti prinsip: satu insiden end-to-end dulu (INC-001),
barulah menambah skenario. INC-002–005 dibuat dengan alur dan bukti yang sama
ketatnya sebelum statusnya dinaikkan.
