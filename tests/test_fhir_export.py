import pytest

from hl7gen.fhir_export import (
    UnsupportedFhirVersionError,
    UnsupportedMessageTypeError,
    message_to_fhir,
)
from hl7gen.generator import generate_message


def test_supported_type_produces_patient_resource():
    raw = generate_message("ADT_A01")
    bundle = message_to_fhir(raw)
    resource_types = [entry["resource"]["resourceType"] for entry in bundle["entry"]]
    assert "Patient" in resource_types


def test_unsupported_type_raises():
    raw = generate_message("MFN_M01")
    with pytest.raises(UnsupportedMessageTypeError):
        message_to_fhir(raw)


def test_oru_produces_observations():
    raw = generate_message("ORU_R01")
    bundle = message_to_fhir(raw)
    resource_types = [entry["resource"]["resourceType"] for entry in bundle["entry"]]
    assert "Observation" in resource_types


def test_default_version_is_r5():
    raw = generate_message("ADT_A01")
    bundle = message_to_fhir(raw)
    encounter = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Encounter")
    assert isinstance(encounter["class"], list)  # R5 shape


def test_r4b_produces_valid_bundle_with_different_encounter_shape():
    raw = generate_message("ADT_A01")
    bundle = message_to_fhir(raw, fhir_version="R4B")
    encounter = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Encounter")
    assert isinstance(encounter["class"], dict)  # R4B shape: single Coding, not a list


def test_unsupported_fhir_version_raises():
    raw = generate_message("ADT_A01")
    with pytest.raises(UnsupportedFhirVersionError):
        message_to_fhir(raw, fhir_version="STU3")


def test_mangled_newlines_still_convert_correctly():
    # Simulates what an HTML <textarea>.value getter (or naive text-mode file read) does
    # to HL7's literal \r segment separators — see decisions/0009.
    raw = generate_message("ADT_A01")
    mangled = raw.replace("\r", "\n")
    bundle = message_to_fhir(mangled)
    resource_types = [entry["resource"]["resourceType"] for entry in bundle["entry"]]
    assert "Patient" in resource_types
