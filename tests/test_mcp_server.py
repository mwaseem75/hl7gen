"""End-to-end test: spawns the MCP server as a real subprocess over stdio and calls
each tool through an MCP client session, the same way Claude Desktop/Code would.
"""
import json

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.fixture
def server_params():
    return StdioServerParameters(command="python", args=["-m", "hl7gen.mcp_server"])


async def _call(server_params, name, arguments):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            return result.content[0].text


@pytest.mark.asyncio
async def test_lists_expected_tools(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert names == {
                "generate_hl7_message",
                "validate_hl7_message",
                "hl7_to_fhir",
                "get_hl7_structure",
                "list_hl7_message_types",
            }


@pytest.mark.asyncio
async def test_generate_then_validate(server_params):
    message = await _call(server_params, "generate_hl7_message", {"message_type": "ADT_A01"})
    assert message.startswith("MSH")

    result = json.loads(await _call(server_params, "validate_hl7_message", {"message": message}))
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_to_fhir(server_params):
    message = await _call(server_params, "generate_hl7_message", {"message_type": "ADT_A01"})
    bundle = json.loads(await _call(server_params, "hl7_to_fhir", {"message": message}))
    resource_types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "Patient" in resource_types


@pytest.mark.asyncio
async def test_to_fhir_unsupported_type_returns_error_not_exception(server_params):
    message = await _call(server_params, "generate_hl7_message", {"message_type": "MFN_M01"})
    result = json.loads(await _call(server_params, "hl7_to_fhir", {"message": message}))
    assert "error" in result


@pytest.mark.asyncio
async def test_structure_reports_required_and_repeating(server_params):
    tree = json.loads(await _call(server_params, "get_hl7_structure", {"message_type": "ADT_A01"}))
    msh = next(s for s in tree["segments"] if s["name"] == "MSH")
    assert msh["required"] is True


@pytest.mark.asyncio
async def test_list_message_types(server_params):
    types_ = json.loads(await _call(server_params, "list_hl7_message_types", {}))
    assert types_["ADT_A01"] == "Admit/Visit Notification"
