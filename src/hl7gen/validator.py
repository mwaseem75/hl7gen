"""Validate HL7 v2 messages (ER7/pipe-delimited format)."""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Optional

from hl7apy import parser


@dataclass
class ValidationResult:
    valid: bool
    error: Optional[str] = None


def validate_message(raw: str) -> ValidationResult:
    """Parse and validate an HL7 v2 message. Never raises."""
    decoded = html.unescape(raw)
    try:
        parser.parse_message(decoded)
        return ValidationResult(valid=True)
    except Exception as exc:
        return ValidationResult(valid=False, error=str(exc))
