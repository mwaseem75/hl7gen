"""Convert HL7 v2 messages to FHIR resources for a documented set of message types.

See decisions/0003-fhir-coverage-scope.md: this intentionally covers common ADT/ORU/ORM
message types (Patient/Encounter/Observation), not all ~185 HL7 v2.5 message types.
Unsupported types raise UnsupportedMessageTypeError rather than attempting a partial or
silently-wrong conversion.

See decisions/0010-fhir-version-selection.md: output can target FHIR R5 (the current
release, and the default) or R4B (still the most widely deployed version in production
EHR/interoperability systems). STU3 is not supported — its resource shapes diverge enough
from R4B/R5 that supporting it properly would need separate mapping code, not just a
different import path.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

from hl7apy.parser import parse_message

from hl7gen.normalize import normalize_er7

# FHIR release -> human label. "R5" is the current FHIR release and the default.
FHIR_VERSIONS = {"R5": "R5 (current)", "R4B": "R4B"}

# Message types this module knows how to convert. Extend deliberately, with tests,
# not by relaxing this check.
SUPPORTED_TYPES = {
    "ADT_A01", "ADT_A02", "ADT_A03", "ADT_A04", "ADT_A05", "ADT_A06", "ADT_A08",
    "ORU_R01", "ORM_O01", "SIU_S12",
}

_SEX_MAP = {"M": "male", "F": "female", "O": "other", "U": "unknown"}
_ENCOUNTER_CLASS_MAP = {"I": "IMP", "O": "AMB", "E": "EMER"}


class UnsupportedMessageTypeError(ValueError):
    pass


class UnsupportedFhirVersionError(ValueError):
    pass


def _load_resources(fhir_version: str) -> SimpleNamespace:
    if fhir_version not in FHIR_VERSIONS:
        raise UnsupportedFhirVersionError(
            f"{fhir_version!r} is not a supported FHIR version. Supported: {sorted(FHIR_VERSIONS)}"
        )

    # The top-level `fhir.resources.*` modules are the current release (R5); R4B lives
    # under its own subpackage. Import lazily and per-call so each conversion is
    # self-contained about which release's classes it used.
    prefix = "" if fhir_version == "R5" else f"{fhir_version}."
    import importlib

    def load(module: str, name: str):
        return getattr(importlib.import_module(f"fhir.resources.{prefix}{module}"), name)

    return SimpleNamespace(
        Address=load("address", "Address"),
        Bundle=load("bundle", "Bundle"),
        BundleEntry=load("bundle", "BundleEntry"),
        ContactPoint=load("contactpoint", "ContactPoint"),
        Encounter=load("encounter", "Encounter"),
        HumanName=load("humanname", "HumanName"),
        Observation=load("observation", "Observation"),
        Patient=load("patient", "Patient"),
    )


def _field(segment, field_name: str) -> str:
    return getattr(segment, field_name).to_er7() if hasattr(segment, field_name) else ""


def _hl7_date_to_fhir(value: str) -> Optional[str]:
    if not value or len(value) < 8:
        return None
    return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"


def _patient_from_pid(pid, R) -> "R.Patient":
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
        address = R.Address(
            line=[parts[0]] if parts and parts[0] else None,
            city=parts[1] if len(parts) > 1 and parts[1] else None,
            state=parts[2] if len(parts) > 2 and parts[2] else None,
        )

    phone_raw = _field(pid, "pid_13")
    telecom = [R.ContactPoint(system="phone", value=phone_raw)] if phone_raw else None

    return R.Patient(
        identifier=None,
        name=[R.HumanName(family=family or None, given=given or None)] if (family or given) else None,
        birthDate=_hl7_date_to_fhir(_field(pid, "pid_7")),
        gender=_SEX_MAP.get(_field(pid, "pid_8"), None),
        address=[address] if address else None,
        telecom=telecom,
    )


def _encounter_from_pv1(pv1, R, fhir_version: str):
    if not hasattr(pv1, "pv1_2"):
        return None
    code = _ENCOUNTER_CLASS_MAP.get(_field(pv1, "pv1_2"), "AMB")

    if fhir_version == "R4B":
        # R4B's Encounter.class is a single required Coding, not a list.
        return R.Encounter(status="unknown", class_fhir={"code": code})

    # R5 changed Encounter.class to a list of CodeableConcept.
    return R.Encounter(status="unknown", class_fhir=[{"coding": [{"code": code}]}])


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


def _observations_from_obx(message, R) -> list:
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
        observations.append(R.Observation(**obs_kwargs))
    return observations


def message_to_fhir(raw: str, fhir_version: str = "R5") -> dict:
    """Convert an HL7 v2 ER7 message to a FHIR Bundle (as a plain dict, JSON-ready).

    fhir_version selects the target FHIR release — "R5" (current, default) or "R4B".
    Raises UnsupportedMessageTypeError for HL7 message types outside SUPPORTED_TYPES, and
    UnsupportedFhirVersionError for an unsupported fhir_version.
    """
    R = _load_resources(fhir_version)

    message = parse_message(normalize_er7(raw))
    msg_type = message.msh.msh_9.msg_3.to_er7() if hasattr(message.msh.msh_9, "msg_3") else ""
    if msg_type not in SUPPORTED_TYPES:
        raise UnsupportedMessageTypeError(
            f"{msg_type or '(unknown)'} is not a supported message type for FHIR export. "
            f"Supported: {sorted(SUPPORTED_TYPES)}"
        )

    resources = []
    pid_segments = _find_segments(message, "PID")
    if pid_segments:
        resources.append(_patient_from_pid(pid_segments[0], R))
    pv1_segments = _find_segments(message, "PV1")
    if pv1_segments:
        encounter = _encounter_from_pv1(pv1_segments[0], R, fhir_version)
        if encounter:
            resources.append(encounter)
    resources.extend(_observations_from_obx(message, R))

    bundle = R.Bundle(
        type="collection",
        entry=[R.BundleEntry(resource=r) for r in resources],
    )
    return bundle.model_dump(exclude_none=True, by_alias=True)
