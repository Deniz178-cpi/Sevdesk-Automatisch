"""Wandelt gesprochenen Text mit Claude in strukturierte Rechnungsdaten um."""

import json
import math
from datetime import date

import anthropic
import httpx

MODEL = "claude-opus-5-5"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
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


def build_user_message(spoken_text: str, units: list[dict], today: date) -> str:
    unit_names = ", ".join(u["name"] for u in units)
    return (
        f"Heute ist {WEEKDAYS[today.weekday()]}, der {today.isoformat()}.\n"
        f"Verfügbare Einheiten: {unit_names}\n\n"
        f"Diktat:\n{spoken_text}"
    )


def extract_with_ollama(http: httpx.Client, model: str, spoken_text: str, units: list[dict], today: date | None = None) -> dict:
    """Lokale KI über Ollama (kostenlos, läuft auf dem eigenen Rechner)."""
    today = today or date.today()
    try:
        response = http.post("/api/chat", json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(spoken_text, units, today)},
            ],
            "format": INVOICE_SCHEMA,
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0},
        })
    except httpx.ConnectError as e:
        raise ExtractionError("Ollama läuft nicht. Bitte Ollama starten (Symbol in der Taskleiste).") from e
    except httpx.TimeoutException as e:
        raise ExtractionError("Die lokale KI hat zu lange gebraucht. Bitte nochmal versuchen.") from e
    if response.status_code == 404:
        raise ExtractionError(f"KI-Modell fehlt. Bitte einmal ausführen: ollama pull {model}")
    if response.status_code >= 400:
        raise ExtractionError(f"Ollama-Fehler ({response.status_code}): {response.text[:300]}")
    try:
        data = json.loads(response.json()["message"]["content"])
    except (KeyError, ValueError) as e:
        raise ExtractionError("Die lokale KI hat keine gültigen Daten geliefert. Bitte nochmal versuchen.") from e
    return attach_unit_ids(normalize(data), units)


def extract_with_claude(client: anthropic.Anthropic, spoken_text: str, units: list[dict], today: date | None = None) -> dict:
    """Claude über die Anthropic-API (kostet ca. 1–2 Cent pro Rechnung)."""
    today = today or date.today()
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": INVOICE_SCHEMA}},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(spoken_text, units, today)}],
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
    try:
        data = json.loads(text)
    except ValueError as e:
        raise ExtractionError("Claude hat keine gültigen Daten geliefert. Bitte nochmal versuchen.") from e
    return attach_unit_ids(normalize(data), units)


def attach_unit_ids(data: dict, units: list[dict]) -> dict:
    """Ordnet jeder Position die sevDesk-Einheiten-ID zu (Fallback: erste Einheit der Liste)."""
    by_name = {u["name"].lower(): u for u in units}
    for position in data.get("positions", []):
        unit = by_name.get(str(position.get("unit", "")).lower(), units[0])
        position["unit"] = unit["name"]
        position["unit_id"] = unit["id"]
    return data


def _number(value, default: float) -> float:
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _iso_date(value) -> str | None:
    try:
        return date.fromisoformat(str(value)).isoformat() if value else None
    except ValueError:
        return None


def _text(value) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def normalize(data: dict) -> dict:
    """Bereinigt die KI-Ausgabe, damit auch kleinere lokale Modelle eine gültige Vorschau ergeben."""
    if not isinstance(data, dict):
        data = {}
    raw_hints = data.get("hints")
    hints = [str(h) for h in raw_hints if h] if isinstance(raw_hints, list) else []
    positions = []
    raw_positions = data.get("positions")
    for p in raw_positions if isinstance(raw_positions, list) else []:
        if not isinstance(p, dict) or not str(p.get("name") or "").strip():
            continue
        tax_rate = _number(p.get("tax_rate"), 19)
        if tax_rate not in (0, 7, 19):
            hints.append(f"Ungewöhnlicher Steuersatz {tax_rate:g} % bei „{p['name']}“ wurde auf 19 % gesetzt.")
            tax_rate = 19
        positions.append({
            "name": str(p["name"]).strip(),
            "description": str(p.get("description") or "").strip() or None,
            "quantity": _number(p.get("quantity"), 1),
            "unit": str(p.get("unit") or ""),
            "price_net": round(_number(p.get("price_net"), 0), 2),
            "tax_rate": tax_rate,
        })
    time_to_pay = data.get("time_to_pay")
    return {
        "customer_name": str(data.get("customer_name") or "").strip(),
        "invoice_date": _iso_date(data.get("invoice_date")),
        "delivery_date": _iso_date(data.get("delivery_date")),
        "header": _text(data.get("header")),
        "head_text": _text(data.get("head_text")),
        "foot_text": _text(data.get("foot_text")),
        "time_to_pay": max(0, int(_number(time_to_pay, 0))) if time_to_pay not in (None, "") else None,
        "positions": positions,
        "hints": hints,
    }
