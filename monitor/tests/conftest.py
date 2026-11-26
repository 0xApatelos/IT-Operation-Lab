"""Fixture: pasang fake adapters ke cli.build_adapters."""

from __future__ import annotations

import pytest

from monitor_lab.adapters import Adapters
from tests.fakes import FakeDisk, FakeDns, FakeHttp, FakeSystemd, FakeTcp


@pytest.fixture
def install_adapters(monkeypatch):
    """Pasang fake adapters ke cli.build_adapters; kembalikan objeknya."""

    def _install(disk=None, systemd=None, dns=None, tcp=None, http=None) -> Adapters:
        adapters = Adapters(
            disk=disk or FakeDisk(),
            systemd=systemd or FakeSystemd(states={"demo-http": "active"}),
            dns=dns or FakeDns(mapping={"archive.ubuntu.com": ["1.2.3.4"]}),
            tcp=tcp or FakeTcp(),
            http=http or FakeHttp(),
        )
        from monitor_lab import cli as cli_mod

        monkeypatch.setattr(cli_mod, "build_adapters", lambda: adapters)
        return adapters

    return _install
