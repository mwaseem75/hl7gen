# hl7gen

[![PyPI](https://img.shields.io/pypi/v/hl7gen)](https://pypi.org/project/hl7gen/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Smithery](https://img.shields.io/badge/Smithery-mwaseem75%2Fhl7gen-blue)](https://smithery.ai/servers/mwaseem75/hl7gen)

Generate, validate, and convert synthetic HL7 v2 test data — for any HL7 v2 system, with
no vendor lock-in.

```bash
pip install hl7gen
hl7gen generate ADT_A01
```

That's it — no database, no server, no license required. Point the output at whatever
you're testing (Mirth, Rhapsody, an IRIS production, your own listener) with `hl7gen send`.

## Why

Testing an HL7 v2 interface means generating realistic-looking messages, and there's
surprisingly little good open tooling for that outside of expensive commercial engines.
`hl7gen` fills that gap: a small, free, scriptable tool that generates structurally valid
HL7 v2.5 messages for any of ~185 message types, validates messages you already have, and
can convert common message types straight to FHIR.

## Features

- **Generate** — synthetic HL7 v2.5 messages for any standard message type (`ADT_A01`,
  `ORU_R01`, `ORM_O01`, ...), fully populated (not just the required-field skeleton).
- **Validate** — parse and check any HL7 v2 message, yours or generated.
- **Convert to FHIR** — turn common ADT/ORU/ORM messages into a FHIR `Bundle`
  (Patient/Encounter/Observation). See [Supported message types](#fhir-conversion-coverage) below —
  this is intentionally not universal coverage.
- **Send** — deliver a message to any TCP/IP HL7 receiver.
- **`--realistic`** — optionally use Claude to generate a clinically coherent synthetic
  patient persona (name, DOB, address, phone) that seeds the message, instead of pure
  random values. Requires `ANTHROPIC_API_KEY`; without it, generation just uses
  Faker-based randomization — the tool is fully usable for free either way.
- **Web playground** — try it in the browser with no install (`docker compose up`, see
  below).
- **GitHub Action** — generate test HL7 data directly in CI (see `action/action.yml`).
- **MCP server** — expose generate/validate/convert as tools any MCP client (Claude
  Desktop, Claude Code, etc.) can call directly. See [MCP server](#mcp-server) below.

## App Layout
<img width="524" alt="image" src="https://github.com/user-attachments/assets/d706bdeb-ba30-46f8-9751-8ee5f074616c" />

## CLI

```bash
hl7gen generate ADT_A01 --count 5 --out ./messages   # write 5 messages to disk
hl7gen generate ORU_R01 --realistic                  # AI-realistic patient data
hl7gen validate ./messages/ADT_A01_1.hl7
hl7gen to-fhir ./messages/ADT_A01_1.hl7
hl7gen send ./messages/ADT_A01_1.hl7 --host localhost --port 2575
hl7gen types                                          # list all message types
hl7gen structure ADT_A01                              # JSON structure tree
```

## Web playground

Run locally:

```bash
docker compose up --build
```

Open http://localhost:8000 — generate, validate, and convert messages entirely in the
browser. Set `ANTHROPIC_API_KEY` in your environment before `docker compose up` to enable
the realistic-data option there too.

**Deploy your own copy to Render:** connect this repo on [Render](https://dashboard.render.com)
via **New +** → **Blueprint** — it picks up `render.yaml` and deploys `webapp/Dockerfile`
automatically (free tier). See `decisions/0011-render-for-public-playground.md`.

## MCP server

```bash
pip install "hl7gen[mcp]"
```

Exposes 5 tools over the [Model Context Protocol](https://modelcontextprotocol.io):
`generate_hl7_message`, `validate_hl7_message`, `hl7_to_fhir`, `get_hl7_structure`,
`list_hl7_message_types`. It runs locally over stdio — an MCP client launches
`hl7gen-mcp` as a subprocess, no network or Docker involved.

For Claude Code: this repo ships a `.mcp.json`, so opening it in Claude Code makes the
server available automatically. For other clients, point them at the `hl7gen-mcp` command
(installed by the `mcp` extra above). See `decisions/0013-mcp-server.md` for what's exposed,
what's deliberately not (message sending — a side-effecting operation), and why.

Also published as an [MCPB bundle](https://github.com/modelcontextprotocol/mcpb) for
one-click install in compatible hosts — download `hl7gen.mcpb` from the
[latest release](https://github.com/mwaseem75/hl7gen/releases/latest). It uses the `uv`
runtime type, so dependencies install automatically at first run — no separate `pip install`
needed. See `decisions/0014-mcpb-bundle-for-smithery.md`.

### Claude Code plugin

```
/plugin marketplace add mwaseem75/hl7gen
/plugin install hl7gen@hl7gen-marketplace
```

Bundles the MCP server above with a skill (`SKILL.md`) that teaches Claude when to reach
for hl7gen and flags real gotchas discovered while building it (like HL7's `\r` segment
separator getting silently mangled by naive text handling). See
`decisions/0015-skill-and-plugin.md`.

## FHIR conversion coverage

`hl7gen to-fhir` currently supports: `ADT_A01`, `ADT_A02`, `ADT_A03`, `ADT_A04`, `ADT_A05`,
`ADT_A06`, `ADT_A08`, `ORU_R01`, `ORM_O01`, `SIU_S12`. Unsupported types raise a clear error
rather than producing a partial or silently wrong conversion — see
`decisions/0003-fhir-coverage-scope.md`.

## GitHub Action

```yaml
- uses: mwaseem75/hl7gen-action@v1
  with:
    message-type: ADT_A01
    count: 10
    out-dir: test-data/hl7
```

Lives in its own repo: [mwaseem75/hl7gen-action](https://github.com/mwaseem75/hl7gen-action)
— see there for full docs (inputs/outputs, example workflow).

## Project layout

```
src/hl7gen/     core package (generator, validator, fhir_export, ai_realistic, mllp_client, cli)
webapp/         FastAPI web playground + static frontend
action/         GitHub Action wrapping the CLI
tests/          pytest suite
decisions/      one file per architectural decision (ADR-style) — read before changing scope
tasks.md        phase tracker
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see `LICENSE`.
