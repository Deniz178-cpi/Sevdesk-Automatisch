"""Zugriffsschutz: nur aus dem eigenen Netz, Login per Passwort (APP_PASSWORD), Sperre nach Fehlversuchen."""

import hashlib
import hmac
import ipaddress
import os
import secrets
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from app.paths import STATIC_DIR

COOKIE_NAME = "session"
SESSION_SECONDS = 30 * 24 * 3600
MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60
PUBLIC_PATHS = {"/login", "/healthz"}

# IP -> Zeitpunkte der letzten Fehlversuche (nur im Speicher, reicht für eine Einzelperson-App).
_failures: dict[str, list[float]] = {}

router = APIRouter()


def _password() -> str | None:
    return os.environ.get("APP_PASSWORD") or None


def _signing_key(password: str) -> bytes:
    # Aus dem Passwort abgeleitet: Ein neues Passwort meldet automatisch alle Geräte ab.
    return hashlib.sha256(b"session-v1:" + password.encode()).digest()


def make_session(password: str, now: float | None = None) -> str:
    expires = str(int((time.time() if now is None else now) + SESSION_SECONDS))
    signature = hmac.new(_signing_key(password), expires.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def valid_session(token: str | None, password: str) -> bool:
    if not token or "." not in token:
        return False
    expires, signature = token.split(".", 1)
    expected = hmac.new(_signing_key(password), expires.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected) and expires.isdigit() and int(expires) > time.time()


def client_ip(request: Request) -> str:
    # X-Forwarded-For nur hinter einem eigenen Proxy beachten (TRUST_PROXY=1), sonst könnte jeder ihn fälschen.
    # Der Proxy hängt die echte Client-IP hinten an; vordere Einträge stammen vom Client.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and os.environ.get("TRUST_PROXY") == "1":
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unbekannt"


def is_local_network(ip: str) -> bool:
    """True für Geräte im eigenen WLAN/LAN (z. B. 192.168.x.x) und für den Rechner selbst."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if address.version == 6 and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_private or address.is_loopback or address.is_link_local


def lan_only_enabled() -> bool:
    return os.environ.get("LAN_ONLY", "1") != "0"


def _recent_failures(ip: str) -> list[float]:
    now = time.time()
    recent = [t for t in _failures.get(ip, []) if now - t < LOCK_SECONDS]
    _failures[ip] = recent
    return recent


def is_locked(ip: str) -> bool:
    return len(_recent_failures(ip)) >= MAX_FAILURES


async def access_control(request: Request, call_next):
    if lan_only_enabled() and not is_local_network(client_ip(request)):
        return Response("Zugriff nur aus dem eigenen WLAN/LAN.", status_code=403, media_type="text/plain; charset=utf-8")
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    password = _password()
    if not password:
        return Response("Die App ist gesperrt: APP_PASSWORD ist nicht gesetzt.", status_code=503, media_type="text/plain; charset=utf-8")
    if valid_session(request.cookies.get(COOKIE_NAME), password):
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Bitte neu anmelden."}, status_code=401)
    return RedirectResponse("/login", status_code=303)


@router.get("/login")
def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@router.post("/login")
async def login(request: Request):
    password = _password()
    if not password:
        return RedirectResponse("/", status_code=303)
    ip = client_ip(request)
    if is_locked(ip):
        return RedirectResponse("/login?fehler=gesperrt", status_code=303)

    form = parse_qs((await request.body()).decode(errors="replace"))
    given = (form.get("password") or [""])[0]
    if not secrets.compare_digest(given.encode(), password.encode()):
        _failures.setdefault(ip, []).append(time.time())
        reason = "gesperrt" if is_locked(ip) else "falsch"
        return RedirectResponse(f"/login?fehler={reason}", status_code=303)

    _failures.pop(ip, None)
    response = RedirectResponse("/", status_code=303)
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        COOKIE_NAME, make_session(password), max_age=SESSION_SECONDS,
        httponly=True, secure=secure, samesite="strict",
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
