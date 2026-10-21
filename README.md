# sevDesk Rechnungs-Diktat

Rechnungen per Sprache erfassen: Du sprichst ins Handy oder in den PC, die App versteht Kunde, Positionen, Preise und Daten, zeigt dir eine **Vorschau zum Prüfen**, und legt die Rechnung dann als **Entwurf in sevDesk** an. Versenden machst du wie gewohnt in sevDesk.

Die App läuft **bei dir zu Hause auf deinem Windows-PC**:
- **Kostenlos:** Die KI läuft lokal mit [Ollama](https://ollama.com), es fallen keine Gebühren an.
- **Nur im WLAN:** Nur Geräte aus deinem eigenen WLAN/LAN können die App öffnen.
- **Daten bleiben bei dir:** Kundendaten gehen nur an sevDesk, nicht an einen KI-Anbieter.

## So funktioniert's

1. **🎤 Diktat starten** drücken und sprechen, z. B.:
   > „Rechnung an Bäckerei Müller, fünf Stunden Webdesign à 80 Euro und eine Hosting-Pauschale über 120 Euro, Leistungsdatum letzten Freitag, Zahlungsziel 14 Tage.“
2. **Auswerten**: Die KI liest die Angaben heraus, den Kunden sucht die App in deinen sevDesk-Kontakten.
3. **Vorschau prüfen**: Alles lässt sich ändern. Unklarheiten werden gelb markiert.
4. **Als Entwurf in sevDesk anlegen**: Die Rechnung landet als Entwurf in sevDesk, ein Link öffnet sie direkt.

Was die App annimmt:
- Genannte Preise sind **Nettopreise** (sagst du „brutto“, wird umgerechnet).
- Steuersatz **19 %**, außer du sagst 7 % oder 0 %.
- Die Rechnungsadresse kommt aus dem sevDesk-Kontakt.
- Ohne genanntes Rechnungsdatum gilt heute.

## Einrichtung

👉 **Schritt-für-Schritt-Anleitung für Windows: [ANLEITUNG.md](ANLEITUNG.md)**, inklusive Handy-Einrichtung und Hilfe bei Problemen.

Kurzfassung:
1. [Python](https://www.python.org/downloads/) (mit „Add python.exe to PATH“) und [Ollama](https://ollama.com/download) installieren.
2. Projekt als ZIP herunterladen und entpacken.
3. `start.bat` doppelklicken und in `.env` den `SEVDESK_API_TOKEN` und das `APP_PASSWORD` eintragen.
4. `start.bat` erneut starten. Beim ersten Mal wird das KI-Modell automatisch geladen.
5. Die angezeigte Adresse `https://…:8443` am Handy im selben WLAN öffnen.

## Sicherheit

- **Nur Heimnetz:** Zugriff nur von Geräten im eigenen WLAN/LAN. Anfragen aus dem Internet werden abgewiesen. Richte im Router **keine Portfreigabe** für die App ein.
- **Passwort:** Ohne `APP_PASSWORD` bleibt die App gesperrt. Nach 5 falschen Passwörtern ist der Login für das Gerät 15 Minuten gesperrt.
- **Sitzung:** Nach dem Login bleibst du 30 Tage angemeldet. Mit **Abmelden** (oben rechts) beendest du die Sitzung. Ein neues Passwort in `.env` meldet alle Geräte ab.
- **Verschlüsselung:** Die Verbindung zwischen Handy und PC ist mit HTTPS verschlüsselt.
- **Nur Entwürfe:** Die App legt nur Rechnungsentwürfe an. Sie verschickt und löscht nichts.

## Einstellungen in `.env`

| Einstellung | Bedeutung |
|---|---|
| `AI_PROVIDER` | `ollama` (Standard, lokal, kostenlos) oder `claude` (Anthropic-API, genauer, ca. 1–2 Cent pro Rechnung, braucht `ANTHROPIC_API_KEY`) |
| `OLLAMA_MODEL` | Lokales Modell, Standard `qwen2.5:7b`. Auf schwachen PCs geht auch `qwen2.5:3b`, das ist schneller, aber ungenauer. Ein neues Modell wird beim Start automatisch geladen |
| `LAN_ONLY` | `1` = nur Heimnetz (Standard), `0` = keine Netz-Beschränkung |

## Browser

- **Spracherkennung:** Chrome (Android/PC), Safari (iPhone/Mac) und Edge.
- **Firefox:** Hier gibt es keine Spracherkennung im Browser. Nutze stattdessen die Mikrofon-Taste der Tastatur.

## Entwicklung

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Aufbau:
- `start.py` / `start.bat`: Start im Heimnetz, HTTPS-Zertifikat, Ollama-Prüfung und Modell-Download
- `app/main.py`: Web-Server (FastAPI)
- `app/auth.py`: Nur-Heimnetz, Login, Sperre nach Fehlversuchen
- `app/extractor.py`: Diktat → Rechnungsdaten (Ollama oder Claude)
- `app/sevdesk.py`: sevDesk-API: Kontakte, Einheiten, Rechnungsentwurf
- `app/static/`: Oberfläche mit Spracheingabe, Vorschau und Login
