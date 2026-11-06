"""Outbound-socket guard for the offline harness (S-04 fallback mode).

Auto-imported by every Python process when PYTHONPATH includes scripts/py_guard.
Blocks any outbound socket connection to a non-loopback host by raising, so any
accidental network access during tests fails loudly instead of silently succeeding.
"""

import socket

_ALLOWED_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}


class OfflineSocketBlocked(RuntimeError):
    """Raised when an outbound socket to a non-loopback host is attempted."""


def _check_address(address) -> None:
    host = address
    if isinstance(address, tuple):
        host = address[0] if address else ""
    if isinstance(host, str) and host not in _ALLOWED_HOSTS:
        raise OfflineSocketBlocked(f"offline_check: outbound socket to {host!r} blocked")


_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _guarded_connect(self, address):
    _check_address(address)
    return _orig_connect(self, address)


def _guarded_connect_ex(self, address):
    _check_address(address)
    return _orig_connect_ex(self, address)


socket.socket.connect = _guarded_connect
socket.socket.connect_ex = _guarded_connect_ex
