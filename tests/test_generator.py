import pytest
from hl7apy.parser import parse_message

from hl7gen.generator import generate_message

SAMPLE_TYPES = ["ADT_A01", "ORU_R01", "ORM_O01", "SIU_S12", "ACK"]


@pytest.mark.parametrize("msg_type", SAMPLE_TYPES)
def test_generate_produces_valid_message(msg_type):
    raw = generate_message(msg_type, version="2.5")
    parsed = parse_message(raw)
    assert parsed.msh.msh_9.msg_1.to_er7() == msg_type.split("_")[0]


def test_generate_unknown_type_raises():
    with pytest.raises(ValueError):
        generate_message("NOT_A_REAL_TYPE")


def test_generate_unsupported_version_raises():
    with pytest.raises(ValueError):
        generate_message("ADT_A01", version="9.9")


def test_generate_is_randomized_across_calls():
    a = generate_message("ADT_A01")
    b = generate_message("ADT_A01")
    assert a != b
