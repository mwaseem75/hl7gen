# hl7gen

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

```bash
docker compose up --build
```

Open http://localhost:8000 — generate, validate, and convert messages entirely in the
browser. Set `ANTHROPIC_API_KEY` in your environment before `docker compose up` to enable
the realistic-data option there too.

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

(Requires `hl7gen` to be published to PyPI — see `tasks.md`, Phase B.)

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
