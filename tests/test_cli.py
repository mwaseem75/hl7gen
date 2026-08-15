from click.testing import CliRunner

from hl7gen.cli import cli


def test_generate_command_prints_message():
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "ADT_A01"])
    assert result.exit_code == 0
    assert "MSH" in result.output


def test_types_command_lists_message_types():
    runner = CliRunner()
    result = runner.invoke(cli, ["types"])
    assert result.exit_code == 0
    assert "ADT_A01" in result.output


def test_generate_to_file_then_validate(tmp_path):
    runner = CliRunner()
    out_dir = tmp_path / "out"
    result = runner.invoke(cli, ["generate", "ADT_A01", "--out", str(out_dir)])
    assert result.exit_code == 0

    generated_file = out_dir / "ADT_A01_1.hl7"
    assert generated_file.exists()

    result = runner.invoke(cli, ["validate", str(generated_file)])
    assert result.exit_code == 0
    assert "Valid" in result.output


def test_generate_to_fhir_roundtrip(tmp_path):
    runner = CliRunner()
    out_dir = tmp_path / "out"
    runner.invoke(cli, ["generate", "ADT_A01", "--out", str(out_dir)])
    generated_file = out_dir / "ADT_A01_1.hl7"

    result = runner.invoke(cli, ["to-fhir", str(generated_file)])
    assert result.exit_code == 0
    assert "Patient" in result.output


def test_unknown_message_type_errors_cleanly():
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "NOT_REAL"])
    assert result.exit_code != 0
