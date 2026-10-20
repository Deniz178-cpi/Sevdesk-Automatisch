# sevDesk Rechnungs-Diktat

Rechnungen per Sprache erfassen: Du sprichst ins Handy oder in den PC, die App versteht Kunde, Positionen, Preise und Daten, zeigt dir eine **Vorschau zum Prüfen**, und legt die Rechnung dann als **Entwurf in sevDesk** an. Versenden machst du wie gewohnt in sevDesk.

## So funktioniert's

1. **🎤 Diktat starten** drücken und sprechen, z. B.:
   > „Rechnung an Bäckerei Müller, fünf Stunden Webdesign à 80 Euro und eine Hosting-Pauschale über 120 Euro, Leistungsdatum letzten Freitag, Zahlungsziel 14 Tage.“
2. **Auswerten**: Claude (KI von Anthropic) liest die Angaben heraus. Den Kunden sucht die App in deinen sevDesk-Kontakten.
3. **Vorschau prüfen**: Kunde, Daten, Positionen, Einheiten, Preise und Steuersatz kannst du ändern. Unklarheiten werden gelb markiert.
4. **Als Entwurf in sevDesk anlegen**: Die Rechnung landet als Entwurf in sevDesk. Ein Link öffnet sie direkt.

Was die App annimmt:
- Genannte Preise sind **Nettopreise** (sagst du „brutto“, wird umgerechnet).
- Steuersatz **19 %**, außer du sagst 7 % oder 0 %.
- Die Rechnungsadresse kommt aus dem sevDesk-Kontakt.
- Ohne genanntes Rechnungsdatum gilt heute. Betreff, Kopf- und Fußtext nimmt sevDesk aus deinen Standardeinstellungen.

## Was du brauchst

| Was | Woher |
|---|---|
| **sevDesk API-Token** | sevDesk → Einstellungen → Benutzer → dein Benutzer → API-Token |
| **Anthropic API-Key** | [console.anthropic.com](https://console.anthropic.com) → API Keys (Kosten pro Rechnung im Cent-Bereich) |
| **Passwort für die App** | Frei wählbar. Schützt die App, da sie Zugriff auf deine Buchhaltung hat |

## Online stellen (empfohlen, damit es auch am Handy geht)

Spracherkennung im Browser funktioniert nur über **HTTPS**. Am einfachsten geht das mit [Render](https://render.com) (Gratis-Tarif reicht):

1. Bei Render mit GitHub anmelden → **New → Blueprint** → dieses Repository wählen (`render.yaml` wird erkannt).
2. Die drei Werte `SEVDESK_API_TOKEN`, `ANTHROPIC_API_KEY` und `APP_PASSWORD` eintragen → **Apply**.
3. Die angezeigte Adresse (`https://….onrender.com`) am Handy öffnen. Benutzername beim Login ist egal, Passwort ist dein `APP_PASSWORD`.
4. Tipp: Auf dem Handy „Zum Home-Bildschirm hinzufügen“, dann ist die App wie eine normale App erreichbar.

Hinweis: Im Gratis-Tarif schläft die App nach ca. 15 Minuten ohne Nutzung. Der erste Aufruf danach dauert dann etwa 30 Sekunden.

## Lokal am PC starten

```bash
pip install -r requirements.txt
cp .env.example .env        # Werte eintragen
set -a; source .env; set +a
uvicorn app.main:app --reload
```

Dann <http://localhost:8000> öffnen. Auf `localhost` funktioniert das Mikrofon auch ohne HTTPS.

## Browser

- **Spracherkennung:** Chrome (Android/PC), Safari (iPhone/Mac) und Edge.
- **Firefox:** Hier gibt es keine Spracherkennung im Browser. Nutze stattdessen die Mikrofon-Taste der Handy-Tastatur oder tippe den Text ein.

## Entwicklung

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Aufbau:
- `app/main.py`: Web-Server (FastAPI) mit Passwortschutz
- `app/extractor.py`: Diktat → strukturierte Rechnungsdaten (Claude)
- `app/sevdesk.py`: sevDesk-API: Kontakte, Einheiten, Rechnungsentwurf anlegen
- `app/static/index.html`: Oberfläche mit Spracheingabe und Vorschau
