"""Wandelt gesprochenen Text mit Claude in strukturierte Rechnungsdaten um."""

import json
from datetime import date

import anthropic

MODEL = "claude-opus-5-5"
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

SYSTEM_PROMPT = """Du bist ein Assistent, der aus diktierten Notizen (deutsch, oft umgangssprachlich und \
per Spracherkennung transkribiert) die Daten für eine Rechnung in sevDesk herausliest.

Regeln:
- Preise sind Nettopreise in Euro pro Einheit. Wird ein Gesamtpreis für mehrere Einheiten genannt, \
rechne den Einzelpreis aus. Wird ausdrücklich "brutto" gesagt, rechne mit dem Steuersatz auf netto um.
- Steuersatz ist 19 %, außer es wird ausdrücklich 7 % oder 0 % genannt.
- Wähle für jede Position die passendste Einheit aus der vorgegebenen Liste (Stunden -> Stunde/Std, \
Pauschale -> pauschal, sonst Stück).
- Relative Datumsangaben ("gestern", "letzten Freitag") rechnest du anhand des heutigen Datums um. \
Ohne Angabe bleibt das Datum null.
- Positionsnamen kurz und sauber formulieren (z. B. "Webdesign Startseite"), Details in die Beschreibung.
- Erfinde nichts. Was unklar oder widersprüchlich ist, schreibst du als kurzen Hinweis in "hints"."""

POSITION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Kurzer Name der Leistung/des Artikels"},
        "description": {"type": ["string", "null"], "description": "Optionale Detailbeschreibung"},
        "quantity": {"type": "number"},
        "unit": {"type": "string", "description": "Name der Einheit aus der vorgegebenen Liste"},
        "price_net": {"type": "number", "description": "Nettopreis pro Einheit in EUR"},
        "tax_rate": {"type": "number", "enum": [0, 7, 19]},
    },
    "required": ["name", "description", "quantity", "unit", "price_net", "tax_rate"],
    "additionalProperties": False,
}

INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "customer_name": {"type": "string", "description": "Name des Kunden so wie genannt, leer wenn keiner genannt"},
        "invoice_date": {"type": ["string", "null"], "description": "Rechnungsdatum als YYYY-MM-DD"},
        "delivery_date": {"type": ["string", "null"], "description": "Liefer-/Leistungsdatum als YYYY-MM-DD"},
        "header": {"type": ["string", "null"], "description": "Betreff, nur wenn ausdrücklich genannt"},
        "head_text": {"type": ["string", "null"], "description": "Einleitungstext, nur wenn ausdrücklich genannt"},
        "foot_text": {"type": ["string", "null"], "description": "Schlusstext, nur wenn ausdrücklich genannt"},
        "time_to_pay": {"type": ["integer", "null"], "description": "Zahlungsziel in Tagen"},
        "positions": {"type": "array", "items": POSITION_SCHEMA},
        "hints": {"type": "array", "items": {"type": "string"}, "description": "Unklarheiten für den Nutzer"},
    },
    "required": [
        "customer_name", "invoice_date", "delivery_date", "header", "head_text",
        "foot_text", "time_to_pay", "positions", "hints",
    ],
    "additionalProperties": False,
}


class ExtractionError(Exception):
    pass


def extract_invoice(client: anthropic.Anthropic, spoken_text: str, units: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    unit_names = ", ".join(u["name"] for u in units)
    user_message = (
        f"Heute ist {WEEKDAYS[today.weekday()]}, der {today.isoformat()}.\n"
        f"Verfügbare Einheiten: {unit_names}\n\n"
        f"Diktat:\n{spoken_text}"
    )

    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": INVOICE_SCHEMA}},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.AuthenticationError as e:
        raise ExtractionError("Der Anthropic-API-Schlüssel ist ungültig.") from e
    except anthropic.RateLimitError as e:
        raise ExtractionError("Zu viele Anfragen an Claude, bitte kurz warten.") from e
    except anthropic.APIStatusError as e:
        raise ExtractionError(f"Claude-API-Fehler ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ExtractionError("Keine Verbindung zur Claude-API.") from e

    if response.stop_reason == "refusal":
        raise ExtractionError("Claude hat die Anfrage abgelehnt. Bitte anders formulieren.")
    if response.stop_reason == "max_tokens":
        raise ExtractionError("Das Diktat war zu lang, bitte in kleinere Teile aufteilen.")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise ExtractionError("Claude hat keine Daten zurückgegeben.")
    data = json.loads(text)
    return attach_unit_ids(data, units)


def attach_unit_ids(data: dict, units: list[dict]) -> dict:
    """Ordnet jeder Position die sevDesk-Einheiten-ID zu (Fallback: erste Einheit der Liste)."""
    by_name = {u["name"].lower(): u for u in units}
    for position in data.get("positions", []):
        unit = by_name.get(str(position.get("unit", "")).lower(), units[0])
        position["unit"] = unit["name"]
        position["unit_id"] = unit["id"]
    return data
