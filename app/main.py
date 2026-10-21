"""Web-App: Rechnung diktieren -> Vorschau prüfen -> Entwurf in sevDesk anlegen."""

import os
from collections.abc import Callable
from datetime import date
from functools import lru_cache
from typing import Literal

import anthropic
import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth import access_control, router as auth_router
from app.extractor import DEFAULT_OLLAMA_MODEL, ExtractionError, extract_with_claude, extract_with_ollama
from app.paths import STATIC_DIR
from app.sevdesk import SevdeskClient, SevdeskError

app = FastAPI(title="sevDesk Rechnungs-Diktat", docs_url=None, redoc_url=None, openapi_url=None)
app.middleware("http")(access_control)
app.include_router(auth_router)


@lru_cache
def get_sevdesk() -> SevdeskClient:
    token = os.environ.get("SEVDESK_API_TOKEN")
    if not token:
        raise HTTPException(500, "SEVDESK_API_TOKEN ist nicht gesetzt.")
    return SevdeskClient(token, tax_rule_id=int(os.environ.get("SEVDESK_TAX_RULE", "1")))


@lru_cache
def get_extractor() -> Callable[[str, list[dict]], dict]:
    """KI für die Auswertung: AI_PROVIDER=ollama (Standard, lokal und kostenlos) oder claude."""
    provider = os.environ.get("AI_PROVIDER", "ollama").lower()
    if provider == "claude":
        claude = anthropic.Anthropic()
        return lambda text, units: extract_with_claude(claude, text, units)
    if provider == "ollama":
        http = httpx.Client(base_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"), timeout=300)
        model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        return lambda text, units: extract_with_ollama(http, model, text, units)
    raise HTTPException(500, f"Unbekannter AI_PROVIDER: {provider}")


class ParseRequest(BaseModel):
    text: str = Field(max_length=5000)


class Position(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    name: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    quantity: float = Field(gt=0)
    unit_id: int
    price_net: float
    tax_rate: Literal[0, 7, 19] = 19


class InvoiceDraft(BaseModel):
    contact_id: int
    invoice_date: date | None = None
    delivery_date: date | None = None
    header: str | None = Field(default=None, max_length=500)
    head_text: str | None = Field(default=None, max_length=5000)
    foot_text: str | None = Field(default=None, max_length=5000)
    time_to_pay: int | None = Field(default=None, ge=0, le=365)
    positions: list[Position] = Field(min_length=1, max_length=100)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/meta")
def meta(sevdesk: SevdeskClient = Depends(get_sevdesk)):
    """Einheiten und Kontakte für die Auswahllisten in der Vorschau."""
    try:
        return {"units": sevdesk.units(), "contacts": sevdesk.contacts()}
    except SevdeskError as e:
        raise HTTPException(502, str(e))


@app.post("/api/parse")
def parse(req: ParseRequest, sevdesk: SevdeskClient = Depends(get_sevdesk), extract=Depends(get_extractor)):
    if not req.text.strip():
        raise HTTPException(400, "Es wurde nichts diktiert.")
    try:
        draft = extract(req.text, sevdesk.units())
        matches = sevdesk.match_contacts(draft.get("customer_name", ""))
    except ExtractionError as e:
        raise HTTPException(502, str(e))
    except SevdeskError as e:
        raise HTTPException(502, str(e))
    draft["contact_matches"] = matches
    draft["contact_id"] = matches[0]["id"] if matches and matches[0]["score"] >= 0.6 else None
    return draft


@app.post("/api/invoice")
def create_invoice(draft: InvoiceDraft, sevdesk: SevdeskClient = Depends(get_sevdesk)):
    try:
        return sevdesk.create_draft_invoice(draft.model_dump(mode="json"))
    except SevdeskError as e:
        raise HTTPException(502, str(e))
