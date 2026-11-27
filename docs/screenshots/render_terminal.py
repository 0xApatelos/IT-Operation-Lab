#!/usr/bin/env python3
"""Render tangkapan teks eksekusi nyata menjadi PNG bergaya terminal.

Transparansi (penting):
- Teks input adalah stdout/stderr APA ADANYA dari perintah yang benar-benar
  dijalankan di sandbox (file di captures/; bukti eksekusi terkait ada di
  docs/evidence/).
- Renderer ini HANYA menata tampilan (font monospace, warna berdasarkan
  penanda [OK]/[FAIL]/[WARN]/[SAFETY], judul jendela) dan TIDAK PERNAH
  mengubah isi teks. Tidak ada baris yang ditambah/dikarang di area output.

Pemakaian:
    python3 render_terminal.py <capture.txt> <output.png> "judul jendela"
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_MONO = FONT_DIR / "DejaVuSansMono.ttf"
FONT_MONO_BOLD = FONT_DIR / "DejaVuSansMono-Bold.ttf"
FONT_UI = FONT_DIR / "DejaVuSans.ttf"

BG = (15, 23, 32)          # latar terminal
TITLE_BG = (27, 40, 54)    # bar judul
FG = (213, 222, 233)       # teks default
GREEN = (111, 207, 142)
RED = (242, 112, 138)
YELLOW = (232, 196, 104)
DIM = (124, 139, 158)
PROMPT = (120, 170, 255)
DOTS = (234, 106, 92), (244, 191, 79), (98, 197, 84)

SIZE = 15
COLS = 100  # lebar maksimum kolom; baris lebih panjang dilipat (wrap)
PAD_X = 18
PAD_Y = 16
TITLE_H = 38
FOOTER = "output eksekusi nyata (sandbox agent) - bukan VM - bukti: docs/evidence/"


def _wrap(line: str, cols: int) -> list[str]:
    if len(line) <= cols:
        return [line]
    out: list[str] = []
    while len(line) > cols:
        out.append(line[:cols])
        line = "    " + line[cols:]  # indentasi lanjutan agar jelas hasil lipatan
    out.append(line)
    return out


def _color_for(line: str) -> tuple[int, int, int]:
    if "[OK]" in line or "SEHAT" in line or "TERVERIFIKASI" in line or '"status":"ok"' in line:
        return GREEN
    if "[FAIL]" in line or "TIDAK SEHAT" in line or '"error"' in line:
        return RED
    if "[WARN]" in line or "[SAFETY]" in line or '"status":"insufficient_evidence"' in line:
        return YELLOW
    if line.startswith("$ ") or line.startswith("exit code:"):
        return PROMPT if line.startswith("$ ") else DIM
    return FG


def render(src: Path, dst: Path, title: str) -> None:
    text = src.read_text(encoding="utf-8").rstrip("\n")
    lines: list[str] = []
    for raw in text.splitlines():
        lines.extend(_wrap(raw.rstrip(), COLS))

    f_mono = ImageFont.truetype(str(FONT_MONO), SIZE)
    f_mono_bold = ImageFont.truetype(str(FONT_MONO_BOLD), SIZE)
    f_ui = ImageFont.truetype(str(FONT_UI), 12)

    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    ch_w = probe.textlength("M", font=f_mono)
    line_h = int(SIZE * 1.42)
    body_w = int(ch_w * COLS) + PAD_X * 2
    body_h = PAD_Y * 2 + line_h * len(lines)
    w = max(body_w, 720)
    h = TITLE_H + body_h + 30  # +footer

    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)

    # bar judul + titik gaya jendela
    d.rectangle([0, 0, w, TITLE_H], fill=TITLE_BG)
    for i, c in enumerate(DOTS):
        d.ellipse([14 + i * 22, TITLE_H // 2 - 6, 26 + i * 22, TITLE_H // 2 + 6], fill=c)
    d.text((90, (TITLE_H - SIZE) // 2 - 1), title, font=f_mono_bold, fill=FG)

    # isi output (verbatim, hanya diberi warna)
    y = TITLE_H + PAD_Y
    for ln in lines:
        d.text((PAD_X, y), ln, font=f_mono, fill=_color_for(ln))
        y += line_h

    # footer label kejujuran
    d.text((PAD_X, h - 22), FOOTER, font=f_ui, fill=DIM)

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "PNG", optimize=True)
    print(f"{dst.name}: {w}x{h}px, {len(lines)} baris dari {src.name}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("pakai: render_terminal.py <capture.txt> <out.png> <judul>")
    render(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
