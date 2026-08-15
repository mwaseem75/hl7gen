from hl7gen.generator import generate_message
from hl7gen.validator import validate_message


def test_valid_message_passes():
    raw = generate_message("ADT_A01")
    result = validate_message(raw)
    assert result.valid
    assert result.error is None


def test_broken_message_fails():
    result = validate_message("THIS IS NOT HL7 AT ALL")
    assert not result.valid
    assert result.error
