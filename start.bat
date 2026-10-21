@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Rechnung diktieren

where py >nul 2>nul
if errorlevel 1 (
  echo Python fehlt. Bitte von https://www.python.org/downloads/ installieren und "Add python.exe to PATH" ankreuzen.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Erster Start: richte alles ein, das dauert einen Moment ...
  py -3 -m venv .venv || goto fehler
)
fc /b "requirements.txt" ".venv\installed-requirements.txt" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto fehler
  copy /y "requirements.txt" ".venv\installed-requirements.txt" >nul
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo.
  echo Die Datei .env wurde angelegt. Bitte SEVDESK_API_TOKEN und APP_PASSWORD eintragen,
  echo speichern und start.bat erneut starten.
  notepad ".env"
  exit /b 0
)

".venv\Scripts\python.exe" start.py
pause
exit /b 0

:fehler
echo Beim Einrichten ist etwas schiefgelaufen. Bitte die Meldung oben pruefen.
pause
exit /b 1
