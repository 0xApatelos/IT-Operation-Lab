# Tangkapan layar eksekusi nyata

Galeri visual alur kerja portofolio. **Semua gambar di sini dirender dari
output eksekusi NYATA** di sandbox agent — perintah benar-benar dijalankan,
output-nya disimpan apa adanya di `captures/`, lalu ditata menjadi PNG oleh
`render_terminal.py` (skrip ikut di-commit — cara pembuatan bisa diaudit
siapa pun).

## Aturan kejujuran (penting)

- Renderer **hanya menata tampilan** (font monospace, warna berdasarkan
  penanda `[OK]`/`[FAIL]`/`[WARN]`/`[SAFETY]`, judul jendela) dan **tidak
  pernah mengubah isi teks** — tidak ada baris output yang ditambah,
  dihapus, atau dikarang.
- Semua eksekusi ini **sandbox agent** (lihat `E00`), **bukan VM** — label
  jujur tercantum di footer tiap gambar. Bukti teks mentah terkait ada di
  `docs/evidence/`.
- **Tidak ada** tangkapan layar UI browser yang dimanipulasi atau mockup
  yang diklaim nyata. UI lokal assistant bisa Anda jalankan sendiri via
  `lab-assist serve` (lihat `assistant/README.md`).

## Indeks

| File | Menunjukkan | Sumber tangkapan | Bukti terkait |
|---|---|---|---|
| `png/sc-01-baseline-sehat.png` | Baseline 5/5 sehat, exit 0 (kondisi normal) | `captures/01-baseline-sehat.txt` | E02 |
| `png/sc-02-gejala-insiden.png` | INC-001: 3 check gagal saat layanan dihentikan, exit 1 | `captures/03-gejala-insiden.txt` | E04 |
| `png/sc-03-pemulihan-terverifikasi.png` | Pemulihan terverifikasi: service aktif + HTTP 200 | `captures/04-recover.txt` | E07 |
| `png/sc-04-monitor-cli.png` | Monitor CLI (Fase 2): laporan teks 5 check, exit 0 | `captures/05-monitor-text.txt` | E36 |
| `png/sc-05-monitor-json.png` | Monitor: output JSON terstruktur (dipotong) | `captures/06-monitor-json.txt` | E37 |
| `png/sc-06-assistant-answered.png` | Assistant: jawaban ekstraktif + kutipan sumber | `captures/07-assistant-answered.txt` | E45 |
| `png/sc-07-assistant-abstain-injection.png` | Assistant: abstain jujur + label `[SAFETY]` untuk injection | `captures/08-assistant-abstain-injection.txt` | E46–E47 |
| `png/sc-08-server-api.png` | Server FastAPI nyata: health, query answered/abstain, validasi field | `captures/09-server-api.txt` | E50 |

## Cara mereproduksi / meregenerasi

```bash
cd docs/screenshots
# prasyarat di sandbox/host: demo-http terinstal (sudo lab/scripts/install_demo_service.sh),
# monitor & assistant terinstal (pip install -e 'monitor[dev]' -e 'assistant[dev]')
python3 render_terminal.py captures/01-baseline-sehat.txt png/sc-01-baseline-sehat.png "judul jendela"
# (ulangi per baris indeks di atas — perintah lengkap per capture ada di
#  header file captures/*.txt dan di docs/evidence/)
```

Untuk mengambil ulang output (bukan sekadar me-render ulang), perintah
per langkah ada pada komentar di awal tiap file `captures/*.txt` dan pada
bukti terkait di `docs/evidence/` — jalankan di lingkungan lab Anda sendiri
(VM) lalu simpan hasilnya dengan header lingkungan Anda.

English version: `README.en.md` (in this folder).
