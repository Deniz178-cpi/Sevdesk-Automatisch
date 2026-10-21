"""Schlanker Client für die sevDesk-REST-API (nur das, was die Rechnungs-App braucht)."""

import difflib
import time
from datetime import date

import httpx

BASE_URL = "https://my.sevdesk.de/api/v1"
CACHE_SECONDS = 300
PAGE_SIZE = 1000

# Wird verwendet, falls /Unity nicht abgerufen werden kann (Standard-Einheiten von sevDesk).
FALLBACK_UNITS = [
    {"id": 1, "name": "Stk"},
    {"id": 9, "name": "Std"},
    {"id": 7, "name": "pauschal"},
]


class SevdeskError(Exception):
    pass


class SevdeskClient:
    def __init__(self, api_token: str, tax_rule_id: int = 1, http: httpx.Client | None = None):
        self.tax_rule_id = tax_rule_id
        self._http = http or httpx.Client(base_url=BASE_URL, timeout=30)
        self._http.headers.update({"Authorization": api_token, "Accept": "application/json"})
        self._cache: dict[str, tuple[float, object]] = {}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as e:
            raise SevdeskError("Keine Verbindung zu sevDesk. Bitte Internetverbindung prüfen.") from e
        if response.status_code == 401:
            raise SevdeskError("sevDesk lehnt den API-Token ab. Bitte SEVDESK_API_TOKEN in der .env prüfen.")
        if response.status_code >= 400:
            raise SevdeskError(f"sevDesk {method} {path} fehlgeschlagen ({response.status_code}): {response.text[:500]}")
        try:
            return response.json()
        except ValueError as e:
            raise SevdeskError(f"sevDesk hat eine unerwartete Antwort geschickt ({response.status_code}).") from e

    def _cached(self, key: str, loader):
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        value = loader()
        self._cache[key] = (time.monotonic(), value)
        return value

    # --- Stammdaten -------------------------------------------------------

    def contacts(self) -> list[dict]:
        """Alle Kontakte (Organisationen und Personen) als {id, name, customerNumber}."""

        def load():
            contacts, offset = [], 0
            while True:
                page = self._request("GET", "/Contact", params={"depth": 1, "limit": PAGE_SIZE, "offset": offset}).get("objects", [])
                contacts += [
                    {"id": int(c["id"]), "name": contact_display_name(c), "customerNumber": c.get("customerNumber")}
                    for c in page
                ]
                if len(page) < PAGE_SIZE:
                    return contacts
                offset += PAGE_SIZE

        return self._cached("contacts", load)

    def units(self) -> list[dict]:
        def load():
            try:
                data = self._request("GET", "/Unity")
            except SevdeskError:
                return FALLBACK_UNITS
            units = [{"id": int(u["id"]), "name": u.get("name") or u.get("translationCode", "")} for u in data.get("objects", [])]
            return units or FALLBACK_UNITS

        return self._cached("units", load)

    def contact_person_id(self) -> int:
        """ID des eigenen sevDesk-Benutzers (wird als Ansprechpartner auf der Rechnung benötigt)."""

        def load():
            users = self._request("GET", "/SevUser").get("objects", [])
            if not users:
                raise SevdeskError("Kein sevDesk-Benutzer gefunden.")
            return int(users[0]["id"])

        return self._cached("sevuser", load)

    def match_contacts(self, spoken_name: str, limit: int = 5) -> list[dict]:
        """Sucht Kontakte, deren Name dem gesprochenen Namen ähnelt (beste Treffer zuerst)."""
        needle = spoken_name.strip().lower()
        if not needle:
            return []
        scored = []
        for contact in self.contacts():
            name = contact["name"].lower()
            score = difflib.SequenceMatcher(None, needle, name).ratio()
            if needle in name or name in needle:
                score = max(score, 0.9)
            # Einzelne Wörter vergleichen, damit z. B. "Müller" auch "Bäckerei Müller GmbH" findet.
            for word in name.split():
                score = max(score, difflib.SequenceMatcher(None, needle, word).ratio() * 0.95)
            scored.append({**contact, "score": round(score, 2)})
        scored.sort(key=lambda c: c["score"], reverse=True)
        return [c for c in scored[:limit] if c["score"] >= 0.4]

    # --- Rechnung anlegen -------------------------------------------------

    def create_draft_invoice(self, draft: dict) -> dict:
        """Legt die Rechnung als Entwurf (Status 100) an und gibt {id, invoiceNumber, url} zurück."""
        payload = build_invoice_payload(draft, self.contact_person_id(), self.tax_rule_id)
        data = self._request("POST", "/Invoice/Factory/saveInvoice", json=payload)
        invoice = data.get("objects", {}).get("invoice", {})
        invoice_id = invoice.get("id")
        return {
            "id": invoice_id,
            "invoiceNumber": invoice.get("invoiceNumber"),
            "url": f"https://my.sevdesk.de/fi/detail/type/RE/id/{invoice_id}" if invoice_id else None,
        }


def contact_display_name(contact: dict) -> str:
    if contact.get("name"):
        return contact["name"]
    return " ".join(p for p in (contact.get("surename"), contact.get("familyname")) if p).strip() or f"Kontakt {contact.get('id')}"


def _german_date(iso: str | None) -> str | None:
    if not iso:
        return None
    return date.fromisoformat(iso).strftime("%d.%m.%Y")


def build_invoice_payload(draft: dict, contact_person_id: int, tax_rule_id: int = 1) -> dict:
    if not draft.get("contact_id"):
        raise SevdeskError("Bitte einen Kunden auswählen.")
    positions = draft.get("positions") or []
    if not positions:
        raise SevdeskError("Die Rechnung braucht mindestens eine Position.")

    tax_rates = sorted({float(p.get("tax_rate", 19)) for p in positions}, reverse=True)
    invoice = {
        "objectName": "Invoice",
        "mapAll": True,
        "contact": {"id": int(draft["contact_id"]), "objectName": "Contact"},
        "contactPerson": {"id": contact_person_id, "objectName": "SevUser"},
        "invoiceDate": _german_date(draft.get("invoice_date")) or date.today().strftime("%d.%m.%Y"),
        "discount": 0,
        "addressCountry": {"id": 1, "objectName": "StaticCountry"},  # 1 = Deutschland
        "status": "100",  # Entwurf
        "taxRule": {"id": tax_rule_id, "objectName": "TaxRule"},  # 1 = Umsatzsteuerpflichtige Umsätze
        "taxText": "Umsatzsteuer " + " / ".join(f"{r:g} %" for r in tax_rates),
        "invoiceType": "RE",
        "currency": "EUR",
        "showNet": True,
    }
    optional = {
        "deliveryDate": _german_date(draft.get("delivery_date")),
        "header": draft.get("header"),
        "headText": draft.get("head_text"),
        "footText": draft.get("foot_text"),
        "timeToPay": draft.get("time_to_pay"),
    }
    invoice.update({k: v for k, v in optional.items() if v not in (None, "")})

    invoice_positions = [
        {
            "objectName": "InvoicePos",
            "mapAll": True,
            "positionNumber": index,
            "name": p["name"],
            "text": p.get("description") or None,
            "quantity": float(p["quantity"]),
            "price": float(p["price_net"]),
            "unity": {"id": int(p["unit_id"]), "objectName": "Unity"},
            "taxRate": float(p.get("tax_rate", 19)),
        }
        for index, p in enumerate(positions)
    ]

    return {
        "invoice": invoice,
        "invoicePosSave": invoice_positions,
        "invoicePosDelete": None,
        "discountSave": None,
        "discountDelete": None,
        "takeDefaultAddress": True,
    }
