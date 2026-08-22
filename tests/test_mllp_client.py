"""Tests for MLLP framing in the send path.

Runs a real local TCP listener so the wire bytes are asserted, not mocked.
"""
import socket
import threading

from hl7gen.mllp_client import frame_mllp, send_message

SAMPLE = "MSH|^~\\&|APP|FAC|APP2|FAC2|20260822120000||ADT^A01|MSG00001|P|2.5\rEVN|A01|20260822120000\r"


def _serve_once(port_box: list, received: list, reply_framed: bool, ready: threading.Event):
    """Bind an ephemeral port, publish it, accept one connection, capture wire bytes."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    port_box.append(server.getsockname()[1])
    server.listen(1)
    ready.set()
    try:
        conn, _ = server.accept()
        with conn:
            conn.settimeout(0.5)
            data = b""
            # Read until the MLLP end block or a quiet period, so both
            # framed and legacy raw payloads terminate deterministically.
            while len(data) < 65536:
                try:
                    chunk = conn.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                data += chunk
                if b"\x1c" in data:
                    break
            received.append(data)
            ack_body = "MSA|AA|MSG00001\r"
            payload = (b"\x0b" + ack_body.encode() + b"\x1c\r") if reply_framed else ack_body.encode()
            conn.sendall(payload)
    finally:
        server.close()


def _start_listener(reply_framed: bool):
    port_box: list = []
    received: list = []
    ready = threading.Event()
    t = threading.Thread(target=_serve_once, args=(port_box, received, reply_framed, ready))
    t.start()
    assert ready.wait(2), "listener did not start"
    return t, port_box[0], received


def test_frame_mllp_wraps_start_and_end_blocks():
    framed = frame_mllp(SAMPLE)
    assert framed.startswith(b"\x0bMSH|")
    assert framed.endswith(b"\x1c\r")


def test_frame_mllp_normalizes_newlines():
    framed = frame_mllp(SAMPLE.replace("\r", "\n"))
    assert b"\n" not in framed
    assert framed.count(b"\r") == 3  # two segment separators + end block CR


def test_send_message_frames_by_default_and_unframes_ack():
    t, port, received = _start_listener(reply_framed=True)
    try:
        ack = send_message(SAMPLE, "127.0.0.1", port, timeout=5.0)
    finally:
        t.join(5)

    wire = received[0]
    assert wire.startswith(b"\x0b"), f"message was not MLLP-framed on the wire: {wire[:20]!r}"
    assert wire.endswith(b"\x1c\r")
    assert ack == "MSA|AA|MSG00001", f"ACK should be unframed, got {ack!r}"


def test_send_message_no_frame_preserves_raw_behavior():
    t, port, received = _start_listener(reply_framed=False)
    try:
        ack = send_message(SAMPLE, "127.0.0.1", port, timeout=5.0, mllp_framing=False)
    finally:
        t.join(5)

    wire = received[0]
    assert wire.startswith(b"MSH|"), "raw mode must not add framing"
    # Legacy raw mode returns the reply exactly as received, no unframing.
    assert ack.strip("\r\n") == "MSA|AA|MSG00001"
