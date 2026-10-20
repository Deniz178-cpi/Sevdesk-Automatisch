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

## Einrichtung unter Windows (einmalig, ca. 15 Minuten)

Dein PC sollte **mindestens 16 GB Arbeitsspeicher** haben. Mit 8 GB geht es auch, ist aber langsamer.

1. **Python installieren:** [python.org/downloads](https://www.python.org/downloads/). Im Installer unbedingt **„Add python.exe to PATH“** ankreuzen.
2. **Ollama installieren:** [ollama.com/download](https://ollama.com/download) → Windows. Danach läuft Ollama im Hintergrund (Lama-Symbol in der Taskleiste).
3. **KI-Modell laden:** Eingabeaufforderung öffnen (Windows-Taste → `cmd`) und eingeben:
   ```
   ollama pull qwen2.5:7b
   ```
   Der Download ist ca. 5 GB groß und wird nur einmal benötigt.
4. **App herunterladen:** Auf GitHub oben auf **Code → Download ZIP**, dann die ZIP-Datei entpacken, z. B. nach `Dokumente\Rechnung-diktieren`.
5. **`start.bat` doppelklicken.** Beim ersten Start wird alles eingerichtet, und es öffnet sich die Datei `.env` im Editor. Trag dort ein und speichere:
   - `SEVDESK_API_TOKEN=`: dein Token aus sevDesk → Einstellungen → Benutzer → API-Token
   - `APP_PASSWORD=`: ein Passwort deiner Wahl (mindestens 16 Zeichen)
6. **`start.bat` nochmal doppelklicken.** Fragt die **Windows-Firewall**, ob der Zugriff erlaubt werden soll, wähle **„Private Netzwerke“** und klicke auf Zulassen.

Das Fenster zeigt dir jetzt die Adressen, z. B.:
```
Am PC:    https://localhost:8443
Am Handy: https://192.168.178.25:8443
```

## Benutzung am Handy

1. Handy ins **selbe WLAN** wie den PC.
2. Die angezeigte Adresse **mit `https://`** öffnen.
3. Beim ersten Mal kommt eine **Sicherheitswarnung**. Das ist normal, denn das Zertifikat hat die App selbst erstellt, nicht eine offizielle Stelle. Tippe auf „Erweitert“ → „Weiter zu …“ (Chrome) bzw. „Details einblenden“ → „Website besuchen“ (Safari). Das ist nur einmal nötig.
4. Mit deinem `APP_PASSWORD` anmelden.
5. Tipp: Über „Zum Home-Bildschirm hinzufügen“ hast du die App wie eine normale App.

Die App ist nur erreichbar, solange `start.bat` läuft. Zum Beenden schließt du einfach das Fenster.

**Falls der Handy-Browser das Mikrofon trotzdem nicht freigibt:** Tippe ins Textfeld und nutze die **Mikrofon-Taste der Handy-Tastatur**. Das funktioniert immer.

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
| `OLLAMA_MODEL` | Lokales Modell, Standard `qwen2.5:7b`. Auf schwachen PCs geht auch `qwen2.5:3b`, das ist schneller, aber ungenauer (vorher `ollama pull qwen2.5:3b`) |
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
- `start.py` / `start.bat`: Start im Heimnetz mit HTTPS-Zertifikat
- `app/main.py`: Web-Server (FastAPI)
- `app/auth.py`: Nur-Heimnetz, Login, Sperre nach Fehlversuchen
- `app/extractor.py`: Diktat → Rechnungsdaten (Ollama oder Claude)
- `app/sevdesk.py`: sevDesk-API: Kontakte, Einheiten, Rechnungsentwurf
- `app/static/`: Oberfläche mit Spracheingabe, Vorschau und Login
