"""Build a JSON-serializable structure tree for an HL7 message type.

Rebuilt from GetHL7Structure/GetSegmentDetails in the original iris-HL7v2Gen, which built
an HTML <ul>/<li> tree string for a CSP page. This produces a plain nested-dict tree instead,
reused by both the CLI (`hl7gen structure`) and the web API — no markup baked into the data.
"""
from __future__ import annotations

from hl7apy.core import Message

from hl7gen.data import hl7_segment_names


def _describe_field(name: str, field_def: tuple) -> dict:
    struct_type, sub_elements, datatype, description = field_def[0], field_def[1], field_def[2], field_def[3]
    table_id = field_def[4] if len(field_def) > 4 else None

    node = {
        "name": name,
        "description": description.replace("_", " ").title() if description else None,
        "datatype": datatype,
        "table": table_id,
    }
    if struct_type == "sequence" and sub_elements:
        node["components"] = [
            _describe_field(sub_name, sub_def)
            for sub_name, sub_def, _card, _type in sub_elements
        ]
    return node


def _describe_segment(seg_name: str, definition: tuple, cardinality: tuple) -> dict:
    _seq_type, fields = definition
    return {
        "type": "segment",
        "name": seg_name,
        "description": hl7_segment_names.get(seg_name, ""),
        "required": cardinality[0] >= 1,
        "fields": [_describe_field(name, fdef) for name, fdef, _card, _ftype in fields],
    }


def _describe_group(group_name: str, definition: tuple, cardinality: tuple, msg_type: str) -> dict:
    _seq_type, children = definition
    return {
        "type": "group",
        "name": group_name.replace(msg_type, "").lstrip("_") or group_name,
        "required": cardinality[0] >= 1,
        "children": [_describe_element(el, msg_type) for el in children],
    }


def _describe_element(element: tuple, msg_type: str) -> dict:
    name, definition, cardinality, element_type = element
    if element_type == "SEG":
        return _describe_segment(name, definition, cardinality)
    return _describe_group(name, definition, cardinality, msg_type)


def get_structure(msg_type: str, version: str = "2.5") -> dict:
    """Return a nested-dict structure tree for the given HL7 message type."""
    message = Message(msg_type, version=version)
    _seq_type, top_elements = message.reference
    return {
        "message_type": msg_type,
        "version": version,
        "segments": [_describe_element(el, msg_type) for el in top_elements],
    }
