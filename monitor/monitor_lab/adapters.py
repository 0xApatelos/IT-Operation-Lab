"""Adapter: pemisahan komponen OS-specific agar dapat diuji terpisah.

Aturan:
- Tidak ada shell=True dan tidak ada interpolasi input ke shell; semua
  subprocess memakai list argv dengan argumen tetap.
- Adapter bisa diganti fake pada unit test (lihat monitor/tests/conftest.py).
- run_with_timeout dipakai untuk operasi yang tidak punya timeout bawaan
  (mis. DNS resolver sistem yang blocking).
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from . import __version__


class CheckTimeout(Exception):
    """Operasi melewati batas waktu yang ditetapkan."""


def run_with_timeout(fn, timeout_seconds: float, *args):
    """Jalankan fn(*args) di thread pendamping; hasil/exception di-propagate.

    Jika melebihi timeout, memunculkan CheckTimeout. Thread yang masih
    berjalan bersifat daemon (tidak menahan keluar proses).
    """
    box: dict = {}

    def target() -> None:
        try:
            box["value"] = fn(*args)
        except BaseException as exc:  # noqa: BLE001 - sengaja: diteruskan ke pemanggil
            box["error"] = exc

    th = threading.Thread(target=target, daemon=True, name="monitor-check-timeout")
    th.start()
    th.join(timeout_seconds)
    if th.is_alive():
        raise CheckTimeout(f"operasi melebihi {timeout_seconds:g}s")
    if "error" in box:
        raise box["error"]
    return box["value"]


class DiskAdapter:
    """Kapasitas filesystem (shutil.disk_usage — tanpa root)."""

    def usage(self, path: str) -> tuple[int, int, int]:
        u = shutil.disk_usage(path)
        return int(u.total), int(u.used), int(u.free)


class SystemdAdapter:
    """Status unit systemd via systemctl (tanpa shell, tanpa root)."""

    def is_supported(self) -> bool:
        if shutil.which("systemctl") is None:
            return False
        try:
            comm = Path("/proc/1/comm").read_text(encoding="utf-8").strip()
        except OSError:
            # /proc tidak terbaca (mis. platform non-Linux dengan systemctl
            # terpasang) — anggap didukung; get_state akan memutuskan.
            return True
        return comm == "systemd"

    def get_state(self, unit: str) -> str:
        """Kembalikan state unit: active/inactive/failed/activating/...

        'missing-unit' bila unit tidak ada di sistem.
        """
        try:
            proc = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise OSError(f"systemctl is-active timeout: {e}") from e
        state = (proc.stdout or "").strip()
        err = (proc.stderr or "").lower()
        if proc.returncode == 4 or "could not be found" in err or "not loaded" in err:
            return "missing-unit"
        return state or "unknown"


class DnsAdapter:
    """Resolusi nama via mekanisme sistem (socket.getaddrinfo). Blocking."""

    def resolve(self, host: str) -> list[str]:
        infos = socket.getaddrinfo(host, None)
        return sorted({info[4][0] for info in infos})


class TcpAdapter:
    """Koneksi TCP (bukan ICMP). socket.create_connection punya timeout."""

    def probe(self, host: str, port: int, timeout: float) -> None:
        with socket.create_connection((host, port), timeout=timeout):
            return


class HttpAdapter:
    """HTTP GET dengan timeout. 2xx -> kode; non-2xx -> HTTPError dari urllib."""

    def get_status(self, url: str, timeout: float) -> int:
        req = Request(url, method="GET", headers={"User-Agent": f"monitor-lab/{__version__}"})
        with urlopen(req, timeout=timeout) as resp:
            return int(resp.getcode())


@dataclass(frozen=True)
class Adapters:
    disk: DiskAdapter
    systemd: SystemdAdapter
    dns: DnsAdapter
    tcp: TcpAdapter
    http: HttpAdapter


def build_default_adapters() -> Adapters:
    return Adapters(
        disk=DiskAdapter(),
        systemd=SystemdAdapter(),
        dns=DnsAdapter(),
        tcp=TcpAdapter(),
        http=HttpAdapter(),
    )
