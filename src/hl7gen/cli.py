from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from hl7gen.data import hl7_message_types
from hl7gen.fhir_export import FHIR_VERSIONS, UnsupportedMessageTypeError, message_to_fhir
from hl7gen.generator import generate_messages
from hl7gen.mllp_client import send_message, test_connection
from hl7gen.structure import get_structure
from hl7gen.validator import validate_message


def _read_hl7(path: str) -> str:
    # HL7 ER7 uses a literal \r as the segment separator. Default text-mode I/O
    # (universal newlines) silently rewrites lone \r to \n on read, which corrupts
    # segment boundaries without raising an error — always open with newline=''.
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _write_hl7(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


@click.group()
@click.version_option()
def cli():
    """hl7gen — generate, validate, and convert synthetic HL7 v2 test data."""


@cli.command()
@click.argument("message_type")
@click.option("--version", default="2.5", show_default=True, help="HL7 version.")
@click.option("--count", default=1, show_default=True, help="Number of messages to generate.")
@click.option("--realistic", is_flag=True, help="Use AI-generated realistic patient data if ANTHROPIC_API_KEY is set.")
@click.option("--out", "out_dir", type=click.Path(file_okay=False), default=None,
              help="Directory to write one .hl7 file per message. Prints to stdout if omitted.")
def generate(message_type, version, count, realistic, out_dir):
    """Generate one or more synthetic HL7 v2 MESSAGE_TYPE messages (e.g. ADT_A01)."""
    try:
        messages = generate_messages(message_type, version=version, count=count, realistic=realistic)
    except ValueError as exc:
        raise click.ClickException(str(exc))

    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        for i, msg in enumerate(messages, start=1):
            path = Path(out_dir) / f"{message_type}_{i}.hl7"
            _write_hl7(str(path), msg)
            click.echo(f"Wrote {path}")
    else:
        click.echo("\n---\n".join(messages))


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
def validate(file):
    """Validate an HL7 v2 message from FILE."""
    result = validate_message(_read_hl7(file))
    if result.valid:
        click.echo("Valid HL7 message.")
    else:
        click.echo(f"Invalid HL7 message: {result.error}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--host", required=True)
@click.option("--port", required=True, type=int)
@click.option("--no-frame", "mllp_framing", flag_value=False, default=True,
              help="Send the raw message without MLLP framing (custom listeners only).")
def send(file, host, port, mllp_framing):
    """Send an HL7 message from FILE to HOST:PORT over MLLP."""
    response = send_message(_read_hl7(file), host, port, mllp_framing=mllp_framing)
    click.echo(response or "(no response received)")


@cli.command()
@click.option("--host", required=True)
@click.option("--port", required=True, type=int)
def check_connection(host, port):
    """Test TCP/IP connectivity to HOST:PORT."""
    ok = test_connection(host, port)
    click.echo("Connected." if ok else "Could not connect.")
    sys.exit(0 if ok else 1)


@cli.command("to-fhir")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--fhir-version", type=click.Choice(sorted(FHIR_VERSIONS)), default="R5",
              show_default=True, help="Target FHIR release.")
@click.option("--out", "out_file", type=click.Path(), default=None,
              help="File to write the FHIR Bundle JSON to. Prints to stdout if omitted.")
def to_fhir(file, fhir_version, out_file):
    """Convert an HL7 v2 message from FILE to a FHIR Bundle."""
    try:
        bundle = message_to_fhir(_read_hl7(file), fhir_version=fhir_version)
    except UnsupportedMessageTypeError as exc:
        raise click.ClickException(str(exc))

    output = json.dumps(bundle, indent=2, default=str)
    if out_file:
        Path(out_file).write_text(output, encoding="utf-8")
        click.echo(f"Wrote {out_file}")
    else:
        click.echo(output)


@cli.command()
@click.option("--version", default="2.5", show_default=True)
def types(version):
    """List available HL7 message types."""
    for code, description in sorted(hl7_message_types.items()):
        click.echo(f"{code:<12} {description}")


@cli.command()
@click.argument("message_type")
@click.option("--version", default="2.5", show_default=True)
def structure(message_type, version):
    """Print the segment/field structure tree for MESSAGE_TYPE as JSON."""
    try:
        tree = get_structure(message_type, version=version)
    except Exception as exc:
        raise click.ClickException(str(exc))
    click.echo(json.dumps(tree, indent=2))


if __name__ == "__main__":
    cli()
