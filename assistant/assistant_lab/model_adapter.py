"""Adapter model (Tahap B) — interface siap, provider BELUM diimplementasikan.

Tahap A: OfflineAdapter (default) — jawaban ekstraktif, tanpa LLM, tanpa API
key, selalu dapat digunakan. Tahap B (planned): satu provider dengan config
biaya eksplisit (model, tarif per 1K token, tanggal tarif) — harga TIDAK
diisi di sini untuk menghindari angka karangan. API key hanya dari
environment, tidak pernah masuk source code/config.
"""

from __future__ import annotations

from typing import Protocol


class ModelAdapter(Protocol):
    name: str

    def generate(self, query: str, retrieved: list[dict], base_answer: dict) -> dict:
        """Kembalikan jawaban akhir (dict dengan skema sama seperti base_answer)."""
        ...


class OfflineAdapter:
    """Default Tahap A: kembalikan base_answer tanpa perubahan (ekstraktif)."""

    name = "offline-extractive"

    def generate(self, query: str, retrieved: list[dict], base_answer: dict) -> dict:
        return base_answer


class OpenAICompatibleAdapter:
    """Scaffold Tahap B — sengaja TIDAK diimplementasikan pada MVP.

    Rencana implementasi (dokumentasi, bukan kode aktif):
      - env: LAB_ASSIST_API_KEY (hanya di backend/environment lokal)
      - config biaya (wajib diisi pemilik repo dari halaman harga resmi):
          {"model": "...", "price_input_per_1k": <dari sumber>,
           "price_output_per_1k": <dari sumber>, "rate_date": "YYYY-MM-DD",
           "api_base": "..."}
      - token/usage dilaporkan dari response provider, bukan diperkirakan.
    Sampai diimplementasikan: metode ini menolak untuk berjalan.
    """

    name = "openai-compatible"

    def generate(self, query: str, retrieved: list[dict], base_answer: dict) -> dict:
        raise NotImplementedError(
            "Adapter provider belum diimplementasikan (Tahap B, planned). "
            "Gunakan OfflineAdapter (search-only) yang tidak butuh API key."
        )


def get_adapter(name: str) -> ModelAdapter:
    adapters: dict[str, ModelAdapter] = {OfflineAdapter.name: OfflineAdapter()}
    if name in adapters:
        return adapters[name]
    if name == OpenAICompatibleAdapter.name:
        return OpenAICompatibleAdapter()  # akan raise saat dipanggil (jujur, bukan diam-diam)
    raise ValueError(f"adapter tidak dikenal: {name!r}")
