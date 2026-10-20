"""Web-App: Rechnung diktieren -> Vorschau prüfen -> Entwurf in sevDesk anlegen."""

import os
from functools import lru_cache

import anthropic
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.auth import require_login, router as auth_router
from app.extractor import ExtractionError, extract_invoice
from app.paths import STATIC_DIR
from app.sevdesk import SevdeskClient, SevdeskError

app = FastAPI(title="sevDesk Rechnungs-Diktat")
app.middleware("http")(require_login)
app.include_router(auth_router)


@lru_cache
def get_sevdesk() -> SevdeskClient:
    token = os.environ.get("SEVDESK_API_TOKEN")
    if not token:
        raise HTTPException(500, "SEVDESK_API_TOKEN ist nicht gesetzt.")
    return SevdeskClient(token, tax_rule_id=int(os.environ.get("SEVDESK_TAX_RULE", "1")))


@lru_cache
def get_claude() -> anthropic.Anthropic:
    return anthropic.Anthropic()


class ParseRequest(BaseModel):
    text: str


class Position(BaseModel):
    name: str
    description: str | None = None
    quantity: float
    unit_id: int
    price_net: float
    tax_rate: float = 19


class InvoiceDraft(BaseModel):
    contact_id: int
    invoice_date: str | None = None
    delivery_date: str | None = None
    header: str | None = None
    head_text: str | None = None
    foot_text: str | None = None
    time_to_pay: int | None = None
    positions: list[Position]


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
def parse(req: ParseRequest, sevdesk: SevdeskClient = Depends(get_sevdesk), claude: anthropic.Anthropic = Depends(get_claude)):
    if not req.text.strip():
        raise HTTPException(400, "Es wurde nichts diktiert.")
    try:
        draft = extract_invoice(claude, req.text, sevdesk.units())
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
        return sevdesk.create_draft_invoice(draft.model_dump())
    except SevdeskError as e:
        raise HTTPException(502, str(e))
