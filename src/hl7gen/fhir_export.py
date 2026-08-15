"""Convert HL7 v2 messages to FHIR resources for a documented set of message types.

See decisions/0003-fhir-coverage-scope.md: this intentionally covers common ADT/ORU/ORM
message types (Patient/Encounter/Observation), not all ~185 HL7 v2.5 message types.
Unsupported types raise UnsupportedMessageTypeError rather than attempting a partial or
silently-wrong conversion.
"""
from __future__ import annotations

from typing import Optional

from fhir.resources.address import Address
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.encounter import Encounter
from fhir.resources.humanname import HumanName
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from hl7apy.parser import parse_message

# Message types this module knows how to convert. Extend deliberately, with tests,
# not by relaxing this check.
SUPPORTED_TYPES = {
    "ADT_A01", "ADT_A02", "ADT_A03", "ADT_A04", "ADT_A05", "ADT_A06", "ADT_A08",
    "ORU_R01", "ORM_O01", "SIU_S12",
}

_SEX_MAP = {"M": "male", "F": "female", "O": "other", "U": "unknown"}


class UnsupportedMessageTypeError(ValueError):
    pass


def _field(segment, field_name: str) -> str:
    return getattr(segment, field_name).to_er7() if hasattr(segment, field_name) else ""


def _hl7_date_to_fhir(value: str) -> Optional[str]:
    if not value or len(value) < 8:
        return None
    return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"


def _patient_from_pid(pid) -> Patient:
    name_raw = _field(pid, "pid_5")
    family, given = "", []
    if name_raw:
        parts = name_raw.split("^")
        family = parts[0] if parts else ""
        given = [p for p in parts[1:3] if p]

    address_raw = _field(pid, "pid_11")
    address = None
    if address_raw:
        parts = address_raw.split("^")
        address = Address(
            line=[parts[0]] if parts and parts[0] else None,
            city=parts[1] if len(parts) > 1 and parts[1] else None,
            state=parts[2] if len(parts) > 2 and parts[2] else None,
        )

    phone_raw = _field(pid, "pid_13")
    telecom = [ContactPoint(system="phone", value=phone_raw)] if phone_raw else None

    return Patient(
        identifier=None,
        name=[HumanName(family=family or None, given=given or None)] if (family or given) else None,
        birthDate=_hl7_date_to_fhir(_field(pid, "pid_7")),
        gender=_SEX_MAP.get(_field(pid, "pid_8"), None),
        address=[address] if address else None,
        telecom=telecom,
    )


def _encounter_from_pv1(pv1) -> Optional[Encounter]:
    if not hasattr(pv1, "pv1_2"):
        return None
    patient_class = _field(pv1, "pv1_2")
    class_map = {"I": "IMP", "O": "AMB", "E": "EMER"}
    return Encounter(
        status="unknown",
        class_fhir=[{"coding": [{"code": class_map.get(patient_class, "AMB")}]}],
    )


def _find_segments(node, name: str) -> list:
    """Recursively collect all segments named `name` anywhere under `node`.

    Needed because grouped message types (e.g. ORU_R01) nest segments like OBX
    several group levels deep — a top-level `.children` scan misses them, and
    hl7apy's `hasattr(node, name)` attribute shortcut only ever returns one match.
    """
    found = []
    for child in getattr(node, "children", []):
        if getattr(child, "name", "") == name:
            found.append(child)
        else:
            found.extend(_find_segments(child, name))
    return found


def _observations_from_obx(message) -> list[Observation]:
    observations = []
    for child in _find_segments(message, "OBX"):
        value_type = _field(child, "obx_2")
        identifier_raw = _field(child, "obx_3")
        value = _field(child, "obx_5")
        units = _field(child, "obx_6")

        id_parts = identifier_raw.split("^") if identifier_raw else []
        code_value = id_parts[0] if id_parts else None
        code_display = id_parts[1] if len(id_parts) > 1 else None
        code = {
            "coding": [{"code": code_value, "display": code_display}] if code_value else [],
            "text": code_display or code_value or "Observation",
        }

        obs_kwargs = {"status": "final", "code": code}
        if value_type == "NM":
            try:
                obs_kwargs["valueQuantity"] = {"value": float(value), "unit": units or None}
            except ValueError:
                obs_kwargs["valueString"] = value
        else:
            obs_kwargs["valueString"] = value
        observations.append(Observation(**obs_kwargs))
    return observations


def message_to_fhir(raw: str) -> dict:
    """Convert an HL7 v2 ER7 message to a FHIR Bundle (as a plain dict, JSON-ready).

    Raises UnsupportedMessageTypeError for message types outside SUPPORTED_TYPES.
    """
    message = parse_message(raw)
    msg_type = message.msh.msh_9.msg_3.to_er7() if hasattr(message.msh.msh_9, "msg_3") else ""
    if msg_type not in SUPPORTED_TYPES:
        raise UnsupportedMessageTypeError(
            f"{msg_type or '(unknown)'} is not a supported message type for FHIR export. "
            f"Supported: {sorted(SUPPORTED_TYPES)}"
        )

    resources = []
    pid_segments = _find_segments(message, "PID")
    if pid_segments:
        resources.append(_patient_from_pid(pid_segments[0]))
    pv1_segments = _find_segments(message, "PV1")
    if pv1_segments:
        encounter = _encounter_from_pv1(pv1_segments[0])
        if encounter:
            resources.append(encounter)
    resources.extend(_observations_from_obx(message))

    bundle = Bundle(
        type="collection",
        entry=[BundleEntry(resource=r) for r in resources],
    )
    return bundle.model_dump(exclude_none=True, by_alias=True)
