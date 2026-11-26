"""Fake adapters — dipakai bersama oleh unit test (deterministik, tanpa jaringan)."""

from __future__ import annotations

import socket
import time


class FakeDisk:
    def __init__(self, total=1000, used=100, free=900, error=None):
        self.total, self.used, self.free, self.error = total, used, free, error

    def usage(self, path: str) -> tuple[int, int, int]:
        if self.error is not None:
            raise self.error
        return self.total, self.used, self.free


class FakeSystemd:
    def __init__(self, supported=True, states=None):
        self.supported = supported
        self.states = states or {}

    def is_supported(self) -> bool:
        return self.supported

    def get_state(self, unit: str) -> str:
        return self.states.get(unit, "missing-unit")


class FakeDns:
    def __init__(self, mapping=None, error=None, delay=0.0):
        self.mapping = mapping or {}
        self.error = error
        self.delay = delay

    def resolve(self, host: str) -> list[str]:
        if self.delay:
            time.sleep(self.delay)
        if self.error is not None:
            raise self.error
        if host not in self.mapping:
            raise socket.gaierror(-2, "Name or service not known")
        return self.mapping[host]


class FakeTcp:
    def __init__(self, error=None):
        self.error = error

    def probe(self, host: str, port: int, timeout: float) -> None:
        if self.error is not None:
            raise self.error


class FakeHttp:
    def __init__(self, code=200, error=None):
        self.code = code
        self.error = error

    def get_status(self, url: str, timeout: float) -> int:
        if self.error is not None:
            raise self.error
        return self.code
