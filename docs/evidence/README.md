# docs/evidence/ — indeks bukti

Semua file di folder ini adalah **output mentah dari eksekusi nyata** di
sandbox agent (container Debian 13 dengan systemd sebagai PID 1) — bukan VM
Ubuntu milik pemilik repo. Konteks lengkap lingkungan ada di `E00`.

Bukti yang berasal dari VM milik pemilik repo akan ditambahkan kemudian dengan
header lingkungan yang berbeda dan status `requires manual verification`
berubah menjadi terverifikasi.

## Konvensi label

| Label | Arti |
|---|---|
| `AKTUAL` | Output mentah eksekusi nyata, tanpa rekayasa. |
| `CONTOH` | Output sintetis untuk ilustrasi; **bukan** hasil eksekusi. Selalu ditandai jelas. |
| `SINTETIS` | Data uji yang dibuat sengaja (mis. fixture), bukan data produksi/pribadi. |

Aturan: tidak ada log atau screenshot palsu. Jika sesuatu belum dijalankan,
dinyatakan `planned` atau `requires manual verification` — tidak dibuatkan
bukti.

## Daftar bukti — alur INC-001 (layanan berhenti), 2026-11-25 UTC

| File | Isi | Hasil |
|---|---|---|
| `E00-lingkungan-sandbox.txt` | Konteks lingkungan (OS, systemd, python, catatan koreksi) | — |
| `E01-install-demo-http.txt` | Instalasi service via installer | exit 0; user sistem `demo-http` dibuat; unit enable --now |
| `E02-baseline-sehat.txt` | Baseline sebelum insiden (kondisi normal) | exit 0; 5/5 sehat |
| `E03-percobaan-tanpa-sudo-gagal.txt` | **Kegagalan nyata**: stop tanpa sudo ditolak systemd | exit 4; `Access denied` |
| `E03b-simulasi-stop-sudo.txt` | Simulasi terkontrol dengan sudo | exit 0; layanan `inactive` |
| `E04-gejala-baseline-gagal.txt` | Gejala saat layanan berhenti | exit 1; 3 check gagal (service/tcp/http) |
| `E05-diagnostik-status.txt` | Diagnostik: `systemctl status demo-http` | status `inactive` |
| `E06-diagnostik-journalctl.txt` | Diagnostik: log journald unit | stop direkam; tanpa sudo user tak melihat log unit sistem |
| `E07-pemulihan-recover.txt` | Pemulihan via `recover_service.sh` | exit 0; service aktif + `/health` 200 |
| `E08-baseline-sehat-ulang.txt` | Verifikasi pasca-perbaikan | exit 0; 5/5 sehat |
| `E09-teardown-uninstall.txt` | Teardown lengkap | exit 0; unit, aplikasi, user dihapus |

### INC-002 — disk pressure (2026-11-26 UTC; sandbox direstart antar sesi, service di-install ulang di E11)

| File | Isi | Hasil |
|---|---|---|
| `E10-inc002-mount-fixture.txt` | Mount tmpfs disposable 32 MB (kosong) | df 0% |
| `E11-inc002-baseline-sehat-fixture.txt` | Baseline sehat pada fixture kosong (+ install ulang service; catatan koreksi rekaman) | exit 0; 5/5 sehat |
| `E12-inc002-simulasi-isi.txt` | Isi fixture ~90% (28 MB) | df 88% |
| `E13-inc002-gejala-baseline-gagal.txt` | Gejala satu-faktor: disk >= CRIT | exit 1 |
| `E14-inc002-diagnostik-disk.txt` | df/du/ls → `lab-fill.bin` 28 MB | penyebab teridentifikasi |
| `E15-inc002-pemulihan.txt` | Hapus file penyebab | df 0% |
| `E16-inc002-baseline-pulih.txt` | Baseline pulih | exit 0; 5/5 sehat |
| `E17-inc002-teardown-fixture.txt` | Unmount + hapus mountpoint | tidak ada mount tersisa |

### INC-003 — DNS gagal, Level A (2026-11-26 UTC; tanpa perubahan resolver)

| File | Isi | Hasil |
|---|---|---|
| `E18-inc003-gejala-dns-gagal.txt` | Baseline dengan `DNS_HOST=nonexistent.invalid` | exit 1; dns FAIL (satu faktor) |
| `E19-inc003-diagnostik-getent.txt` | Bandingkan nama gagal (rc=2) vs nama umum (rc=0) | resolver sehat, nama memang tidak ada |
| `E20-inc003-baseline-pulih.txt` | Baseline dengan DNS_HOST default | exit 0; 5/5 sehat |

### INC-004 — permission file salah (2026-11-26 UTC; sandbox direstart antar sesi, service di-install ulang di E21)

| File | Isi | Hasil |
|---|---|---|
| `E21-inc004-baseline-sehat.txt` | Baseline sehat + mode file 755 (+ konteks reinstall) | exit 0; 5/5 sehat |
| `E22-inc004-simulasi-chmod.txt` | `chmod 000` pada file aplikasi lab + restart | unit `failed` (start-limit ~9 detik) |
| `E23-inc004-gejala-baseline-gagal.txt` | Gejala tiga-lapis (service/tcp/http) | exit 1 |
| `E24-inc004-diagnostik-permission.txt` | status + journald + stat | `Errno 13 Permission denied`, `status=2`, mode 000 |
| `E25-inc004-pemulihan.txt` | chmod 755 + reset-failed + start | terverifikasi (active + 200) |
| `E26-inc004-baseline-pulih.txt` | Baseline pulih + mode 755 | exit 0; 5/5 sehat |

### INC-005 — konflik port 8080 (2026-11-26 UTC)

| File | Isi | Hasil |
|---|---|---|
| `E27-inc005-baseline-sehat.txt` | Baseline sehat + pendengar milik unit | exit 0; 5/5 sehat |
| `E28-inc005-simulasi-squatter.txt` | **Kegagalan rekaman pertama**: settle logic terlalu sempit | exit 1 — unit terjebak `activating` |
| `E28b-inc005-simulasi-ulang-fix.txt` | Cleanup terverifikasi + simulasi ulang (settle logic diperbaiki) | exit 0; unit tidak aktif, port dipegang squatter |
| `E29-inc005-gejala-deceptif.txt` | Gejala penipu: service FAIL tetapi tcp/http OK (squatter menjawab) | exit 1 |
| `E30-inc005-diagnostik-port.txt` | status + journald + ss + cmdline | `Errno 98 Address already in use`; squatter teridentifikasi |
| `E31-inc005-pemulihan.txt` | Kill squatter terverifikasi cmdline + start unit | terverifikasi (active + 200) |
| `E32-inc005-baseline-pulih.txt` | Baseline pulih | exit 0; 5/5 sehat |
| `E33-inc005-endstate-bersih.txt` | End-state bersih (+ pelajaran false positive `pgrep -f`) | tepat 1 proses python3 milik unit |

## Fase 2 — System Health Monitor (2026-11-26 UTC; sandbox direstart antar sesi, service di-install ulang)

| File | Isi | Hasil |
|---|---|---|
| `E33b-monitor-integration-lokal.txt` | Integration test monitor terhadap lab lokal (opt-in) | 1 lulus |
| `E34-monitor-pytest-unit.txt` | Unit test deterministik (mock, tanpa internet/VM) | 58 lulus |
| `E35-monitor-ruff.txt` | Lint ruff | bersih |
| `E36-monitor-cli-sehat.txt` | CLI laporan sehat terhadap lab (teks) | exit 0; 5/5 ok |
| `E37-monitor-cli-json.txt` | Output JSON terstruktur | timestamp timezone; schema lengkap |
| `E38-monitor-config-tidak-valid.txt` | warn_pct ≥ crit_pct → ditolak | exit 2 + pesan stderr |
| `E39-monitor-webhook-dedup-nyata.txt` | Webhook NYATA ke receiver lokal: kirim + dedup | tepat 1 POST; payload tanpa secret; state tercatat |
| `E40-monitor-webhook-gagal.txt` | Webhook tak terjangkau (retry terbatas) | warning; hasil health utuh; exit tetap 1 |
| `E41-monitor-integrasi-homelab.txt` | Alur wajib: sehat → gangguan → deteksi → pulih | exit 0 → 1 → 0 |
| `E42-monitor-scheduler-verify-trigger.txt` | `systemd-analyze verify` + trigger nyata service unit | verify 0; start 0; journald + log JSON terekam; cleanup bersih |

## Fase 3 — AI Helpdesk Assistant, Tahap A (2026-11-26 UTC)

| File | Isi | Hasil |
|---|---|---|
| `E43-assistant-pytest-unit.txt` | Unit test assistant (mini corpus) | 43 lulus |
| `E44-assistant-ruff.txt` | Lint ruff assistant | bersih |
| `E45-assistant-cli-query-answered.txt` | CLI query answered — jawaban ekstraktif + citation | status answered; sumber RB-001/INC-001 |
| `E46-assistant-cli-abstain.txt` | Query di luar cakupan | abstain jujur, tanpa prosedur dikarang |
| `E47-assistant-cli-injection.txt` | Query injection "abaikan aturan" | safety_note + abstain |
| `E48-assistant-evaluasi.txt` | Evaluasi 21 kasus (hit rate, citation, abstain, safety, latensi) | hit@k 0.889; citation 1.0; abstain 1.0; safety 1.0; 0 pelanggaran. Catatan A8: expected_doc_ids kasus terlalu sempit (INC-001 ter-retrieve memuat petunjuk reinstall §14) — dibiarkan apa adanya, tidak di-tuning |
| `E49-assistant-index-stats.txt` | Statistik KB | 133 chunks / 11 dokumen, hanya allowed_dirs |
| `E50-assistant-server-nyata.txt` | Server FastAPI nyata: health, query, abstain, batasan input, UI relatif | semua sesuai desain; UI tanpa URL localhost tertanam |

## QA akhir repository (2026-11-26 UTC)

| File | Isi | Hasil |
|---|---|---|
| `E51-repo-qa-final.txt` | YAML CI valid, grep secret bersih, checklist 7 pertanyaan README, placeholder hanya di template, re-run semua test/lint/evaluasi | semua hijau; 58+43 test; hit@k 0.889; 0 pelanggaran |
| `E52-docs-recruiter-polish-qa.txt` | QA polish dokumentasi perspektif recruiter: struktur baru README, link antar-file, konsistensi angka + anotasi temuan hit@k=1.0 | struktur 5/5; link rusak 0; temuan KB di-follow-up di E53 |
| `E53-kb-exclude-globs-sideeffect.txt` | Side effect mirror EN pada KB assistant + perbaikan `exclude_globs` (D17) | baseline kembali: hit@k 0.889, 133/11, 45 test assistant, ruff bersih |

Ringkasan per proyek untuk recruiter & demo: `PORTFOLIO.md` (root).
Template rubrik manual evaluasi assistant: `assistant/evaluation/rubrik-manual.md`
(status: belum diisi → requires manual verification).

## Cara membaca

1. Mulai dari `E00` untuk konteks, lalu ikuti nomor secara berurutan — itu
   adalah alur insiden INC-001 dari kondisi normal sampai pulih.
2. `E03` sengaja dipertahankan apa adanya sebagai contoh kegagalan nyata dan
   analisisnya ada di `../incidents/INC-001-service-down.md`.
3. Tidak ada secret, IP privat milik pihak lain, atau data pribadi dalam bukti.
