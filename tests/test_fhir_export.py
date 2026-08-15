import pytest

from hl7gen.fhir_export import UnsupportedMessageTypeError, message_to_fhir
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
