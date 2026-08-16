---
name: hl7gen
description: Use when generating, validating, or converting HL7 v2 healthcare messages, or converting HL7 v2 to FHIR. Covers synthetic test-message generation for any of 185 HL7 v2 message types across versions 2.1–2.8.2, message validation, FHIR R5/R4B conversion, and structure exploration (required/optional/repeating fields). Triggers on requests like "generate an HL7 message", "create ADT_A01 test data", "validate this HL7 message", "convert HL7 to FHIR", "synthetic patient data for testing", "HL7 interoperability testing".
---

# hl7gen

Generates, validates, and converts synthetic HL7 v2 test data. No vendor lock-in — works
against any HL7 v2 receiver, any of the 12 HL7 versions hl7apy supports (2.1–2.8.2).

## How to reach it

If the `hl7gen` MCP server is connected (bundled with this plugin), prefer its tools —
they're structured (JSON in/out) and don't require shelling out:
`generate_hl7_message`, `validate_hl7_message`, `hl7_to_fhir`, `get_hl7_structure`,
`list_hl7_message_types`.

Otherwise, use the CLI (`pip install hl7gen`):
```bash
hl7gen generate ADT_A01 --version 2.5 --count 5 --out ./messages
hl7gen validate ./messages/ADT_A01_1.hl7
hl7gen to-fhir ./messages/ADT_A01_1.hl7 --fhir-version R5
hl7gen structure ADT_A01
hl7gen types
```

Or import the library directly in Python: `hl7gen.generator.generate_message`,
`hl7gen.validator.validate_message`, `hl7gen.fhir_export.message_to_fhir`.

## Things worth knowing before using it

- **Generated messages are fully populated**, not just the required-field skeleton — a
  generated `ORU_R01` includes `PID`/`PV1`/`OBX`, not just `MSH`/`OBR`. This is deliberate
  (see the project's `decisions/0007`) — don't be surprised by messages larger than the bare
  HL7 grammar requires.
- **HL7 messages use a literal `\r` as the segment separator, not `\n`.** If you're handling
  a raw HL7 message string yourself (reading it from a file, editing it, passing it through
  a shell variable, or displaying it in a UI text box), be careful not to let it get
  normalized to `\n` — that silently corrupts the message without raising an error (hl7apy's
  parser doesn't reject `\n`-separated input, it just mis-parses). This bit us twice in this
  project's own development: once in file I/O, once in a browser `<textarea>`. If validation
  or FHIR conversion unexpectedly returns empty/wrong results on a message that "looks right"
  when printed, suspect this first.
- **FHIR conversion covers a documented subset**, not all message types: `ADT_A01/02/03/04/
  05/06/08`, `ORU_R01`, `ORM_O01`, `SIU_S12`. Unsupported types raise a clear error — don't
  assume a NACK-style silent failure means the tool is broken; check `hl7_to_fhir`'s error
  message first.
- **`--realistic` / `realistic=true`** uses Claude to generate a coherent patient persona
  (name/DOB/address/phone) if `ANTHROPIC_API_KEY` is set; without it, falls back to
  randomized data automatically — never fails outright for lack of a key.
- **`hl7gen send` (MLLP/TCP delivery) is not exposed as an MCP tool** — it's the one
  side-effecting operation (pushes data to a network host), deliberately excluded from the
  MCP server's read-only/generate-only tool set. Use the CLI directly for that.
