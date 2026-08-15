"""Optional AI-generated realistic patient personas (see decisions/0002).

If ANTHROPIC_API_KEY is unset, or the API call fails for any reason, generate_persona()
returns None and callers fall back to plain Faker-based randomization. This module never
raises — a broken/missing key must never break message generation.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Persona:
    first_name: str
    last_name: str
    dob: str  # YYYYMMDD
    street: str
    city: str
    state: str
    phone: str


_PERSONA_PROMPT = """Generate one realistic but entirely fictional patient persona for
synthetic HL7 test data. Respond with ONLY a JSON object, no prose, with exactly these
string fields: first_name, last_name, dob (format YYYYMMDD), street, city, state,
phone (format NNNNNNNNNN). Make it internally consistent (e.g. a plausible age)."""


def generate_persona() -> Optional[Persona]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic  # lazy import: optional dependency, only needed here
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            messages=[{"role": "user", "content": _PERSONA_PROMPT}],
        )
        text = response.content[0].text.strip()
        # Guard against accidental markdown code fences in the response.
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[-1]
        data = json.loads(text)
        return Persona(
            first_name=data["first_name"],
            last_name=data["last_name"],
            dob=data["dob"],
            street=data["street"],
            city=data["city"],
            state=data["state"],
            phone=data["phone"],
        )
    except Exception:
        # Any failure (network, bad JSON, missing field, API error) — fall back silently.
        return None
