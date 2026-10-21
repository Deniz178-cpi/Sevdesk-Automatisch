# Anleitung: Rechnungen per Sprache erstellen

Diese Anleitung führt dich Schritt für Schritt durch die Einrichtung. Du brauchst keine Programmierkenntnisse.

**Am Ende hast du:** Eine App auf deinem Handy, in die du Rechnungen hineinsprichst. Sie landen als Entwurf in sevDesk. Kostenlos, und nur in deinem WLAN erreichbar.

**Dauer:** ca. 30 Minuten, davon ist ein großer Teil Warten auf Downloads.

---

## Inhalt

1. [Was du brauchst](#1-was-du-brauchst)
2. [Python installieren](#2-python-installieren)
3. [Ollama installieren (die kostenlose KI)](#3-ollama-installieren-die-kostenlose-ki)
4. [Die App herunterladen](#4-die-app-herunterladen)
5. [Den sevDesk-API-Token holen](#5-den-sevdesk-api-token-holen)
6. [Erster Start](#6-erster-start)
7. [Am PC ausprobieren](#7-am-pc-ausprobieren)
8. [Am Handy einrichten](#8-am-handy-einrichten)
9. [Deine erste Rechnung](#9-deine-erste-rechnung)
10. [Im Alltag](#10-im-alltag)
11. [Probleme und Lösungen](#11-probleme-und-lösungen)

---

## 1. Was du brauchst

- [ ] **Einen Windows-PC oder Laptop** mit Windows 10 oder 11
  - Mindestens **16 GB Arbeitsspeicher** sind ideal. 8 GB gehen auch, dann dauert es länger.
  - Ca. **10 GB freier Speicherplatz**
  - So prüfst du den Arbeitsspeicher: Windows-Taste drücken, `Info` eintippen, **„Info zu Ihrem PC“** öffnen und bei **„Installierter RAM“** nachsehen.
- [ ] **Dein Handy** im selben WLAN wie der PC
- [ ] **Deine sevDesk-Zugangsdaten**
- [ ] **Ein Passwort für die App**, mindestens 16 Zeichen, z. B. `Sonne-Fahrrad-Kaffee-2026`. Schreib es dir auf.

---

## 2. Python installieren

Python ist die Programmiersprache, in der die App geschrieben ist. Du musst nichts damit programmieren, Windows braucht es nur, um die App auszuführen.

1. Öffne **[python.org/downloads](https://www.python.org/downloads/)**.
2. Klicke auf den großen gelben Knopf **„Download Python 3.x.x“**.
3. Öffne die heruntergeladene Datei (z. B. `python-3.13.x-amd64.exe`).
4. **⚠️ Ganz wichtig:** Setze ganz unten im Fenster den Haken bei **„Add python.exe to PATH“**.
5. Klicke auf **„Install Now“** und warte, bis **„Setup was successful“** erscheint.
6. Klicke auf **„Close“**.

> Nimm bitte die Version von python.org und **nicht** die aus dem Microsoft Store.

---

## 3. Ollama installieren (die kostenlose KI)

Ollama ist ein Programm, das die KI direkt auf deinem PC laufen lässt. Dadurch kostet es nichts, und deine Daten verlassen den PC nicht.

1. Öffne **[ollama.com/download](https://ollama.com/download)**.
2. Wähle **Windows** und klicke auf **„Download for Windows“**.
3. Öffne die heruntergeladene Datei `OllamaSetup.exe` und klicke auf **„Install“**.
4. Danach läuft Ollama im Hintergrund. Du erkennst es an einem kleinen **Lama-Symbol** unten rechts in der Taskleiste. Eventuell steckt es hinter dem kleinen Pfeil `^`.

Das KI-Modell selbst musst du **nicht** von Hand herunterladen. Das macht die App beim ersten Start automatisch.

---

## 4. Die App herunterladen

1. Öffne die GitHub-Seite des Projekts: **[github.com/Deniz178-cpi/Sevdesk-Automatisch](https://github.com/Deniz178-cpi/Sevdesk-Automatisch)**. Falls das Projekt privat ist, musst du bei GitHub angemeldet sein.
2. Klicke auf den grünen Knopf **„<> Code“** und dann auf **„Download ZIP“**.
3. Öffne deinen **Downloads**-Ordner und klicke mit der **rechten Maustaste** auf die Datei `Sevdesk-Automatisch-master.zip`.
4. Wähle **„Alle extrahieren …“**.
5. Als Ziel gibst du z. B. `C:\Users\DEINNAME\Documents` ein und klickst auf **„Extrahieren“**.

Danach hast du einen Ordner `Sevdesk-Automatisch-master`. Darin liegen unter anderem die Dateien `start.bat` und `ANLEITUNG.md`.

> ⚠️ Starte die App **nicht direkt aus der ZIP-Datei** heraus. Sie muss vorher entpackt sein.

---

## 5. Den sevDesk-API-Token holen

Der API-Token ist wie ein Schlüssel, mit dem die App in deinem Namen Rechnungsentwürfe in sevDesk anlegen darf.

1. Melde dich am PC auf **[my.sevdesk.de](https://my.sevdesk.de)** an.
2. Klicke auf **Einstellungen** (Zahnrad), dann auf **Benutzer**.
3. Öffne **deinen eigenen Benutzer**.
4. Dort findest du den **API-Token**, eine lange Zeichenkette aus Buchstaben und Zahlen. Kopiere ihn.

> Falls du ihn nicht findest: In der sevDesk-Hilfe nach **„API-Token“** suchen. Die Menüs ändern sich manchmal.
>
> 🔒 Gib den Token niemandem weiter. Mit ihm hat man vollen Zugriff auf deine Buchhaltung.

---

## 6. Erster Start

### 6.1 Einrichten lassen

1. Öffne den Ordner `Sevdesk-Automatisch-master`.
2. **Doppelklicke auf `start.bat`.**
3. Erscheint ein blaues Fenster **„Der Computer wurde durch Windows geschützt“**:
   - Klicke auf **„Weitere Informationen“**.
   - Dann auf **„Trotzdem ausführen“**.

   Das passiert, weil die Datei nicht von einer bekannten Firma stammt.
4. Ein schwarzes Fenster öffnet sich, und die App richtet sich ein. Das dauert 1–2 Minuten.
5. Danach öffnet sich automatisch der **Editor** mit der Datei `.env`.

### 6.2 Zugangsdaten eintragen

Im Editor siehst du mehrere Zeilen. Trag **direkt hinter dem `=`** ein, ohne Leerzeichen und ohne Anführungszeichen:

```
SEVDESK_API_TOKEN=hier-deinen-sevdesk-token-einfügen
APP_PASSWORD=Sonne-Fahrrad-Kaffee-2026
```

Alle anderen Zeilen lässt du, wie sie sind. Dann **speichern** (`Strg` + `S`) und den Editor schließen.

### 6.3 Richtig starten

1. **Doppelklicke nochmal auf `start.bat`.**
2. Beim ersten Mal lädt die App jetzt das **KI-Modell herunter**, ca. 5 GB. Je nach Internet dauert das 5–30 Minuten, und du siehst einen Fortschrittsbalken. Das passiert nur einmal.
3. Fragt die **Windows-Firewall** „Zugriff zulassen?“:
   - Setze den Haken bei **„Private Netzwerke“**.
   - Klicke auf **„Zugriff zulassen“**.
   - Ohne diese Erlaubnis kann dein Handy die App nicht erreichen.
4. Wenn alles läuft, siehst du:

```
  ==============================================
   Rechnung diktieren läuft!
   Am PC:    https://localhost:8443
   Am Handy: https://192.168.178.25:8443
   (Handy muss im selben WLAN sein)
   Beenden: dieses Fenster schließen
  ==============================================
```

📝 **Schreib dir die Adresse hinter „Am Handy“ auf.** Bei dir steht dort eine andere Zahl als im Beispiel.

> Lass das schwarze Fenster offen. Solange es offen ist, läuft die App.

---

## 7. Am PC ausprobieren

1. Öffne am PC **Chrome** oder **Edge** und gib ein: **`https://localhost:8443`**
2. Es erscheint **„Die Verbindung ist nicht privat“**. Das ist normal, weil die App ihr Sicherheitszertifikat selbst erstellt hat.
   - Klicke auf **„Erweitert“**.
   - Dann auf **„Weiter zu localhost (unsicher)“**.
3. Gib dein **App-Passwort** ein und klicke auf **„Anmelden“**.
4. Du siehst die App mit dem blauen Knopf **„🎤 Diktat starten“**. 🎉

---

## 8. Am Handy einrichten

Dein Handy muss im **selben WLAN** sein wie der PC, nicht im Gast-WLAN und nicht über mobile Daten.

### Android (Chrome)

1. Öffne **Chrome** und tippe die Adresse von „Am Handy“ ein, z. B. `https://192.168.178.25:8443`. Ganz wichtig: mit **`https://`** am Anfang.
2. Bei **„Die Verbindung ist nicht privat“**: auf **„Erweitert“** tippen, dann auf **„Weiter zu 192.168… (unsicher)“**.
3. Mit deinem **App-Passwort** anmelden.
4. Beim ersten Tippen auf **🎤** fragt Chrome nach dem Mikrofon. Tippe auf **„Zulassen“**.
5. **Als App speichern:** Tippe oben rechts auf das Menü **⋮** und dann auf **„Zum Startbildschirm hinzufügen“**.

### iPhone (Safari)

1. Öffne **Safari** und tippe die Adresse von „Am Handy“ ein, z. B. `https://192.168.178.25:8443`.
2. Bei **„Diese Verbindung ist nicht privat“**:
   - Tippe auf **„Details einblenden“**.
   - Tippe dann auf **„diese Website besuchen“** und bestätige nochmal mit **„Website besuchen“**.
3. Mit deinem **App-Passwort** anmelden.
4. Beim ersten Tippen auf **🎤** nach dem Mikrofon gefragt: **„Erlauben“**.
5. **Als App speichern:** Tippe unten auf **Teilen** (Viereck mit Pfeil) und dann auf **„Zum Home-Bildschirm“**.

---

## 9. Deine erste Rechnung

> 💡 Mach die erste Rechnung am besten für einen **Testkunden**, so siehst du ohne Risiko, wie alles funktioniert.

1. Tippe auf **„🎤 Diktat starten“** und sprich ganz normal, zum Beispiel:

   > „Rechnung an Bäckerei Müller. Fünf Stunden Webdesign zu je 80 Euro. Dazu eine Hosting-Pauschale über 120 Euro. Leistungsdatum war letzten Freitag, Zahlungsziel 14 Tage.“

2. Tippe auf **„⏹ Diktat beenden“** und dann auf **„Auswerten“**. Die KI braucht jetzt **10–60 Sekunden**, je nach PC.
3. **Prüfe die Vorschau:**
   - **Kunde:** Stimmt der Kunde? Falls nicht, wähle ihn aus der Liste.
   - **Gelber Kasten:** Hier weist die KI auf Unklarheiten hin.
   - **Positionen, Mengen, Preise:** Du kannst alles antippen und ändern.
   - **Unten:** die Summe netto, Umsatzsteuer und brutto.
4. Tippe auf **„Als Entwurf in sevDesk anlegen“**.
5. Über den Link **„In sevDesk öffnen →“** siehst du den Entwurf direkt in sevDesk. Dort prüfst du ihn und versendest ihn wie gewohnt.

### Tipps zum Sprechen

- **Kunde:** Nenne ihn so, wie er in sevDesk heißt. Ein Teil reicht, z. B. „Müller“.
- **Preise:** Sie gelten als **netto**. Sagst du „brutto“, rechnet die App um.
- **Steuersatz:** Ohne Angabe gelten **19 %**. Sag „7 Prozent“, wenn es ermäßigt ist.
- **Datum:** „gestern“, „letzten Freitag“ oder „am 3. Oktober“ funktionieren.
- **Fehler beim Sprechen:** Kein Problem. Du kannst den Text im Textfeld vor dem Auswerten korrigieren, oder später in der Vorschau.

---

## 10. Im Alltag

### App starten

Doppelklick auf **`start.bat`**. Danach am Handy einfach das gespeicherte App-Symbol antippen.

### App beenden

Das **schwarze Fenster schließen**.

### Automatisch beim PC-Start starten (optional)

1. Klicke mit der rechten Maustaste auf `start.bat` und wähle **„Verknüpfung erstellen“**.
2. Drücke `Windows-Taste` + `R`, gib **`shell:startup`** ein und drücke Enter.
3. Ziehe die Verknüpfung in den Ordner, der sich öffnet.

### Feste Adresse fürs Handy (empfohlen)

Der Router gibt dem PC manchmal eine neue Adresse, z. B. `.25` statt `.31`. Dann funktioniert das Lesezeichen am Handy nicht mehr. So verhinderst du das:

- **FRITZ!Box:** Öffne `fritz.box` im Browser, dann **Heimnetz → Netzwerk**. Klicke beim PC auf den **Stift** und setze den Haken bei **„Diesem Netzwerkgerät immer die gleiche IPv4-Adresse zuweisen“**.
- **Andere Router:** Suche in den Einstellungen nach **„DHCP-Reservierung“** oder **„feste IP“**.

### Passwort ändern

1. Öffne `.env` im Ordner mit Rechtsklick → **„Öffnen mit“** → **Editor**.
2. Ändere `APP_PASSWORD=`, speichere und starte `start.bat` neu.
3. Alle Geräte müssen sich danach neu anmelden.

### Abmelden

Oben rechts in der App auf **„Abmelden“** tippen.

---

## 11. Probleme und Lösungen

### Beim Starten (schwarzes Fenster)

| Meldung | Lösung |
|---|---|
| **„Python fehlt“** | Schritt 2 wiederholen und den Haken bei **„Add python.exe to PATH“** nicht vergessen. Danach den PC neu starten. |
| **„Ollama ist nicht installiert“** | Schritt 3 durchführen. |
| **„Ollama ist installiert, läuft aber nicht“** | Im Startmenü **„Ollama“** suchen und öffnen. Danach `start.bat` erneut starten. |
| **„Bitte zuerst die Datei .env ausfüllen“** | Schritt 6.2: Token und Passwort in `.env` eintragen und speichern. |
| **„Der Download hat nicht geklappt“** | Internetverbindung prüfen und `start.bat` erneut starten. Der Download macht dort weiter, wo er aufgehört hat. |
| Fenster geht sofort wieder zu | Ordner öffnen, oben in die Adressleiste `cmd` tippen, Enter drücken, dann `start.bat` eintippen und Enter. Jetzt bleibt die Fehlermeldung sichtbar. |

### Am Handy

| Problem | Lösung |
|---|---|
| **Seite lädt nicht / „nicht erreichbar“** | 1. Läuft das schwarze Fenster am PC? 2. Ist das Handy im **selben WLAN** (nicht Gast-WLAN, nicht mobile Daten)? 3. Hast du **`https://`** und **`:8443`** eingegeben? 4. Firewall: Windows-Taste → `Firewall` → **„App über die Windows-Firewall kommunizieren lassen“** → bei **Python** den Haken bei **„Privat“** setzen. |
| **Adresse geht plötzlich nicht mehr** | Der PC hat eine neue Adresse bekommen. Schau im schwarzen Fenster nach der neuen Adresse und richte die **feste Adresse** ein (siehe [Im Alltag](#10-im-alltag)). |
| **„Zugriff nur aus dem eigenen WLAN/LAN“** | Du bist nicht im Heim-WLAN. Bei manchen Handys hilft es, **„Mobile Daten“** kurz auszuschalten. |
| **Sicherheitswarnung kommt wieder** | Normal, wenn sich die Adresse des PCs geändert hat. Einfach wieder bestätigen. |
| **Mikrofon-Knopf fehlt oder reagiert nicht** | **Android:** Chrome → ⋮ → Einstellungen → Website-Einstellungen → Mikrofon → erlauben. **iPhone:** Einstellungen → Allgemein → Tastatur → **„Diktierfunktion“ aktivieren**. **Firefox** kann keine Spracherkennung, nutze Chrome bzw. Safari. **Immer möglich:** Ins Textfeld tippen und die **Mikrofon-Taste der Tastatur** benutzen. |
| **„Bitte neu anmelden“** | Passwort wurde geändert, oder du warst 30 Tage nicht angemeldet. Einfach neu anmelden. |
| **„Zu viele Fehlversuche“** | 15 Minuten warten, dann mit dem richtigen Passwort anmelden. |

### Beim Auswerten oder Anlegen

| Meldung | Lösung |
|---|---|
| **„Ollama läuft nicht“** | Lama-Symbol in der Taskleiste fehlt: Ollama über das Startmenü starten. |
| **„KI-Modell fehlt“** | `start.bat` schließen und neu starten, das Modell wird dann geladen. |
| **„Die lokale KI hat zu lange gebraucht“** | Andere große Programme schließen und nochmal versuchen. Bei schwachen PCs: in `.env` die Zeile `OLLAMA_MODEL=qwen2.5:3b` eintragen. Das ist schneller, aber etwas ungenauer. |
| **Kunde wird nicht gefunden** | Den Namen so sagen, wie er in sevDesk steht, oder ihn in der Vorschau aus der Liste wählen. Neue Kunden zuerst in sevDesk anlegen. |
| **KI versteht Positionen falsch** | In der Vorschau korrigieren. Tipp: Langsamer sprechen und jede Position in einem eigenen Satz nennen. |
| **„sevDesk … fehlgeschlagen (401)“** | Der API-Token ist falsch. Schritt 5 wiederholen, den Token neu in `.env` eintragen und `start.bat` neu starten. |
| **„sevDesk … fehlgeschlagen (422)“ oder andere sevDesk-Fehler** | Meldung abfotografieren oder kopieren und an den Entwickler schicken. |

---

## Gut zu wissen

- **Kosten:** Die App ist komplett kostenlos, auch die KI. Sie nutzt nur deinen Strom.
- **Datenschutz:**
  - Dein Diktat wird auf deinem PC ausgewertet.
  - Nur die fertige Rechnung geht an sevDesk.
  - Ausnahme ist die Spracherkennung des Handy-Browsers: Bei Android läuft sie über Google, beim iPhone über Apple.
- **Sicherheit:**
  - Die App ist nur in deinem WLAN erreichbar und mit Passwort geschützt.
  - Richte im Router **keine Portfreigabe** für die App ein.
- **Nur Entwürfe:** Die App verschickt nie selbst Rechnungen. Du prüfst und versendest immer in sevDesk.
