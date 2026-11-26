"""Unit test adapter: offline default, provider jujur menolak."""

from __future__ import annotations

import pytest

from assistant_lab.model_adapter import OfflineAdapter, OpenAICompatibleAdapter, get_adapter


def test_offline_adapter_passthrough():
    a = OfflineAdapter()
    base = {"status": "answered"}
    assert a.generate("q", [], base) is base


def test_provider_adapter_not_implemented():
    with pytest.raises(NotImplementedError, match="Tahap B"):
        OpenAICompatibleAdapter().generate("q", [], {})


def test_get_adapter_unknown_rejected():
    with pytest.raises(ValueError, match="tidak dikenal"):
        get_adapter("bukan-ada")


def test_get_adapter_names():
    assert get_adapter("offline-extractive").name == "offline-extractive"
    assert get_adapter("openai-compatible").name == "openai-compatible"
