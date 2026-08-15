"""Generate synthetic HL7 v2 test messages.

Rebuilt from the message-population logic in the author's original iris-HL7v2Gen
(an ObjectScript wrapper whose method bodies were IRIS embedded Python calling
hl7apy). This version walks hl7apy's message reference tree *recursively* to any
depth, instead of the original's hand-unrolled 3-level nesting, so every group
and every composite field gets populated rather than being left empty past a
hardcoded depth.
"""
from __future__ import annotations

import importlib
import random
import string
from typing import Optional

import hl7apy as hl7apy_root
from faker import Faker
from hl7apy.core import Message
from hl7apy.parser import parse_message

from hl7gen.ai_realistic import Persona

_fake = Faker()

# Field/component descriptions (hl7apy's `long_name`) that get special handling
# regardless of datatype.
_LITERAL_FIELDS = {"VERSION_ID"}


def _get_version_tables(version: str) -> dict:
    module_name = hl7apy_root.SUPPORTED_LIBRARIES[version]
    lib = importlib.import_module(module_name)
    return getattr(lib, "tables", None) and lib.tables.TABLES or {}


def _random_leaf_value(datatype: str, table_id: Optional[str], tables: dict) -> str:
    if table_id and table_id in tables and tables[table_id][1]:
        return str(random.choice(tables[table_id][1]))

    if datatype in ("ST", "IS", "ID", "TX", "FT"):
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    if datatype == "SI":
        return str(random.randint(1, 100))
    if datatype == "NM":
        return str(round(random.uniform(1, 1000), 2))
    if datatype == "DT":
        return _fake.date(pattern="%Y%m%d")
    if datatype == "TM":
        return _fake.time(pattern="%H%M%S")
    if datatype in ("TS", "DTM"):
        return _fake.date_time().strftime("%Y%m%d%H%M%S")
    # Unknown/unsupported leaf datatype: still produce a harmless placeholder
    # rather than leaving the field empty or emitting a literal "UNKNOWN".
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


def _persona_override(description: str, persona: Optional[Persona]) -> Optional[str]:
    if persona is None:
        return None
    if description == "PATIENT_NAME":
        return f"{persona.last_name}^{persona.first_name}"
    if description == "PATIENT_ADDRESS":
        return f"{persona.street}^{persona.city}^{persona.state}"
    if description == "DATE_TIME_OF_BIRTH":
        return persona.dob
    if description in ("HOME_PHONE_NUMBER", "PHONE_NUMBER_HOME"):
        return persona.phone
    return None


def _populate_field(field_def: Optional[tuple], mtype: str, version: str, tables: dict,
                     persona: Optional[Persona]) -> str:
    if field_def is None:
        # hl7apy leaves the definition unresolved for a handful of "varies"-datatype
        # fields (e.g. OBX-5's type depends on OBX-2 at runtime) — no fixed structure
        # to walk, so there's nothing meaningful to generate.
        return ""
    struct_type, sub_elements, datatype, description = field_def[0], field_def[1], field_def[2], field_def[3]
    table_id = field_def[4] if len(field_def) > 4 else None

    override = _persona_override(description, persona)
    if override is not None:
        return override

    if description in _LITERAL_FIELDS:
        return version
    if description == "MESSAGE_TYPE" or datatype == "MSG":
        parts = mtype.split("_")
        return f"{parts[0]}^{parts[1]}^{mtype}" if len(parts) > 1 else mtype

    if struct_type == "leaf":
        return _random_leaf_value(datatype, table_id, tables)

    # Composite: recurse into subcomponents and join with the component separator.
    return "^".join(
        _populate_field(sub_el[1], mtype, version, tables, persona) for sub_el in sub_elements
    )


def _build_segment(seg_name: str, fields: tuple, mtype: str, version: str, tables: dict,
                    persona: Optional[Persona]) -> str:
    if seg_name == "MSH":
        # MSH-1 (field separator) and MSH-2 (encoding characters) are positional,
        # not delimited fields — handle them literally, then join the rest normally.
        rest = fields[2:]
        rest_values = [_populate_field(f[1], mtype, version, tables, persona) for f in rest]
        tail = "|" + "|".join(rest_values) if rest_values else ""
        return "MSH|" + r"^~\&" + tail

    values = [_populate_field(f[1], mtype, version, tables, persona) for f in fields]
    return "|".join([seg_name, *values])


def _walk(elements: tuple, mtype: str, version: str, tables: dict,
          persona: Optional[Persona], out: list) -> None:
    # Populate every segment/group the message structure allows (one occurrence each),
    # not just the ones marked required — a "required-fields-only" skeleton (e.g. an
    # ORU_R01 with no PID) isn't useful synthetic test data even though it's technically
    # grammar-valid. Repeating groups are only populated once; see decisions/ for scope.
    for _name, definition, _cardinality, element_type in elements:
        if element_type == "SEG":
            _, fields = definition
            out.append(_build_segment(_name, fields, mtype, version, tables, persona))
        elif element_type == "GRP":
            _, children = definition
            _walk(children, mtype, version, tables, persona, out)


def generate_message(msg_type: str, version: str = "2.5", realistic: bool = False) -> str:
    """Generate a single synthetic HL7 v2 message in ER7 (pipe-delimited) format.

    Raises ValueError if msg_type/version is not a valid hl7apy message structure.
    """
    if version not in hl7apy_root.SUPPORTED_LIBRARIES:
        raise ValueError(f"Unsupported HL7 version: {version!r}")

    try:
        message = Message(msg_type, version=version)
    except Exception as exc:  # hl7apy raises its own exception types for bad structures
        raise ValueError(f"Unknown message type {msg_type!r} for version {version}: {exc}") from exc

    tables = _get_version_tables(version)

    persona = None
    if realistic:
        from hl7gen.ai_realistic import generate_persona
        persona = generate_persona()

    _seq_type, top_elements = message.reference
    segments: list[str] = []
    _walk(top_elements, msg_type, version, tables, persona, segments)

    er7 = "\r".join(segments)
    # Round-trip through hl7apy's parser so the output is guaranteed well-formed.
    parsed = parse_message(er7)
    return parsed.to_er7()


def generate_messages(msg_type: str, version: str = "2.5", count: int = 1,
                       realistic: bool = False) -> list[str]:
    return [generate_message(msg_type, version=version, realistic=realistic) for _ in range(count)]
