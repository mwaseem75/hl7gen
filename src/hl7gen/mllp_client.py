"""Send HL7 v2 messages over MLLP (Minimal Lower Layer Protocol) over TCP/IP.

MLLP is the de-facto transport for HL7 v2: every message is wrapped in a
start-of-block byte (0x0b, VT) and terminated by end-of-block (0x1c, FS)
followed by carriage return. Receivers such as Mirth Connect, InterSystems
IRIS, and HAPI's Hl7Listeners frame on those bytes; an unframed payload makes
them wait forever for the end block or reject the connection outright.
"""
from __future__ import annotations

import socket

from hl7gen.normalize import normalize_er7

MLLP_START = b"\x0b"  # vertical tab, start of block
MLLP_END = b"\x1c\r"  # file separator + CR, end of block


def frame_mllp(raw: str) -> bytes:
    """Wrap a normalized ER7 message in MLLP start/end block bytes."""
    return MLLP_START + normalize_er7(raw).encode("utf-8") + MLLP_END


def _unframe_mllp(payload: bytes) -> str:
    """Strip MLLP framing from a received ACK, tolerating unframed replies."""
    text = payload.decode("utf-8", errors="replace")
    start = text.find("\x0b")
    if start != -1:
        text = text[start + 1 :]
    end = text.find("\x1c")
    if end != -1:
        text = text[:end]
    return text.strip("\r\n")


def send_message(
    raw: str,
    host: str,
    port: int,
    timeout: float = 10.0,
    mllp_framing: bool = True,
) -> str:
    """Send an HL7 message and return the receiver's response (e.g. an ACK), if any.

    With ``mllp_framing=True`` (default) the payload is wrapped in MLLP
    start/end block bytes and any framing is stripped from the response, which
    is what standard HL7 receivers expect. Pass ``False`` to reproduce the old
    raw-socket behavior against custom listeners that do not speak MLLP.
    """
    wire = frame_mllp(raw) if mllp_framing else normalize_er7(raw).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(wire)
        try:
            reply = sock.recv(4096)
        except socket.timeout:
            return ""
    if not mllp_framing:
        return reply.decode("utf-8", errors="replace")
    return _unframe_mllp(reply)


def test_connection(host: str, port: int, timeout: float = 10.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False
