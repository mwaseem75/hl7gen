"""MCP server exposing hl7gen's core library as tools an MCP client can call.

This imports the same functions the CLI (cli.py) and the web playground (webapp/main.py)
call — no HTTP, no Docker, no subprocess. It runs locally over stdio: an MCP client
(Claude Desktop, Claude Code, etc.) launches this script as a child process and talks to
it over stdin/stdout using the MCP protocol.

Deliberately NOT exposed as a tool: mllp_client.send_message. Generating/validating/
converting data is read-only and side-effect-free; letting an LLM push arbitrary bytes to
an arbitrary host:port over the network is a different risk category and deserves its own
design pass (confirmation step, allowlisting, etc.) rather than being bundled in here.
"""
from __future__ import annotations

from mcp.server import MCPServer

from hl7gen.data import hl7_message_types
from hl7gen.fhir_export import UnsupportedFhirVersionError, UnsupportedMessageTypeError, message_to_fhir
from hl7gen.generator import generate_message
from hl7gen.structure import get_structure
from hl7gen.validator import validate_message

mcp = MCPServer(name="hl7gen", version="0.1.0")


@mcp.tool()
def generate_hl7_message(message_type: str, version: str = "2.5", realistic: bool = False) -> str:
    """Generate a synthetic HL7 v2 message.

    Args:
        message_type: HL7 message type, e.g. "ADT_A01", "ORU_R01".
        version: HL7 version, e.g. "2.5" (default), "2.3", "2.8.2".
        realistic: If true, use AI-generated realistic patient data when available
            (requires ANTHROPIC_API_KEY on the server); otherwise falls back to
            randomized test data automatically.
    """
    return generate_message(message_type, version=version, realistic=realistic)


@mcp.tool()
def validate_hl7_message(message: str) -> dict:
    """Validate an HL7 v2 message (ER7/pipe-delimited format).

    Args:
        message: The raw HL7 message text to validate.

    Returns:
        {"valid": bool, "error": str | None}
    """
    result = validate_message(message)
    return {"valid": result.valid, "error": result.error}


@mcp.tool()
def hl7_to_fhir(message: str, fhir_version: str = "R5") -> dict:
    """Convert an HL7 v2 message to a FHIR Bundle.

    Only a documented subset of message types is supported (common ADT/ORU/ORM types) —
    unsupported types raise a clear error rather than a partial or wrong conversion.

    Args:
        message: The raw HL7 message text to convert.
        fhir_version: "R5" (current FHIR release, default) or "R4B".
    """
    try:
        return message_to_fhir(message, fhir_version=fhir_version)
    except (UnsupportedMessageTypeError, UnsupportedFhirVersionError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_hl7_structure(message_type: str, version: str = "2.5") -> dict:
    """Get the segment/field structure tree for an HL7 message type.

    Each node reports whether it's required or optional, and whether it can repeat —
    useful for understanding a message type before generating or hand-writing one.

    Args:
        message_type: HL7 message type, e.g. "ADT_A01".
        version: HL7 version, default "2.5".
    """
    return get_structure(message_type, version=version)


@mcp.tool()
def list_hl7_message_types() -> dict:
    """List all known HL7 v2 message types and their descriptions."""
    return dict(sorted(hl7_message_types.items()))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
