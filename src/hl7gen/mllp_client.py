"""Send HL7 v2 messages over plain TCP/IP to any receiver.

Ported from SendMessage/TestConnection in the original iris-HL7v2Gen — these were already
vendor-agnostic plain sockets; only the surrounding ObjectScript wrapper was IRIS-specific,
and that's dropped entirely here (see decisions/0004).
"""
from __future__ import annotations

import socket


def send_message(raw: str, host: str, port: int, timeout: float = 10.0) -> str:
    """Send an HL7 message and return the receiver's response (e.g. an ACK), if any."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(raw.encode("utf-8"))
        try:
            return sock.recv(4096).decode("utf-8", errors="replace")
        except socket.timeout:
            return ""


def test_connection(host: str, port: int, timeout: float = 10.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False
