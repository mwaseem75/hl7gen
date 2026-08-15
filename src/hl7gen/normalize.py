"""Normalize incoming HL7 v2 text to use a literal \\r as the segment separator.

HL7 ER7 messages use \\r between segments. Two different sources routinely rewrite that
to \\n before it reaches hl7apy's parser:
  - An HTML <textarea>'s `.value` getter normalizes all line breaks (\\r, \\r\\n, \\n) to \\n
    per the HTML spec — so a message the browser itself generated and displayed comes back
    mangled the moment a user clicks a button that reads the textarea.
  - Default text-mode file I/O (Python's universal newlines) does the same on read.

hl7apy's parser doesn't raise on \\n-separated input — it just silently mis-parses,
producing an empty or wrong structure (see decisions/0009). Always normalize at the
boundary before parsing, sending, or validating.
"""
from __future__ import annotations


def normalize_er7(raw: str) -> str:
    return raw.replace("\r\n", "\r").replace("\n", "\r")
