"""FastAPI playground: try hl7gen in the browser, no install required."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from hl7gen.data import hl7_message_types
from hl7gen.fhir_export import UnsupportedMessageTypeError, message_to_fhir
from hl7gen.generator import generate_message
from hl7gen.structure import get_structure
from hl7gen.validator import validate_message

app = FastAPI(title="hl7gen playground")

STATIC_DIR = Path(__file__).parent / "static"


class GenerateRequest(BaseModel):
    message_type: str
    version: str = "2.5"
    realistic: bool = False


class ValidateRequest(BaseModel):
    message: str


class ToFhirRequest(BaseModel):
    message: str


@app.get("/api/types")
def api_types():
    return [{"code": code, "description": desc} for code, desc in sorted(hl7_message_types.items())]


@app.get("/api/structure/{message_type}")
def api_structure(message_type: str, version: str = "2.5"):
    try:
        return get_structure(message_type, version=version)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    try:
        message = generate_message(req.message_type, version=req.version, realistic=req.realistic)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": message}


@app.post("/api/validate")
def api_validate(req: ValidateRequest):
    result = validate_message(req.message)
    return {"valid": result.valid, "error": result.error}


@app.post("/api/to-fhir")
def api_to_fhir(req: ToFhirRequest):
    try:
        return message_to_fhir(req.message)
    except UnsupportedMessageTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse message: {exc}")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
