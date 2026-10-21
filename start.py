"""Startet die App im Heimnetz: lädt .env, erzeugt ein HTTPS-Zertifikat und zeigt die Adresse fürs Handy."""

import datetime
import ipaddress
import os
import shutil
import socket
import subprocess
from pathlib import Path

import httpx
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from app.extractor import DEFAULT_OLLAMA_MODEL

ROOT = Path(__file__).parent
CERT_DIR = ROOT / "certs"
CERT_FILE = CERT_DIR / "cert.pem"
KEY_FILE = CERT_DIR / "key.pem"
PORT = int(os.environ.get("PORT", "8443"))


def load_env(path: Path) -> None:
    """Liest KEY=WERT-Zeilen aus .env (bereits gesetzte Umgebungsvariablen haben Vorrang)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def lan_ips() -> list[str]:
    """IP-Adressen dieses Rechners im Heimnetz, wahrscheinlichste zuerst (es werden keine Daten verschickt)."""
    candidates = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 80))
            candidates.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        candidates += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    result = []
    for ip in candidates:
        address = ipaddress.ip_address(ip)
        if address.is_private and not address.is_loopback and not address.is_link_local and ip not in result:
            result.append(ip)
    return result


def cert_covers(ips: list[str]) -> bool:
    if not (CERT_FILE.exists() and KEY_FILE.exists()):
        return False
    cert = x509.load_pem_x509_certificate(CERT_FILE.read_bytes())
    if cert.not_valid_after_utc < datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30):
        return False
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    covered = names.get_values_for_type(x509.IPAddress)
    return all(ipaddress.ip_address(ip) in covered for ip in ips)


def create_cert(ips: list[str]) -> None:
    """Selbst signiertes Zertifikat, damit der Browser das Mikrofon freigibt (nur über HTTPS erlaubt)."""
    CERT_DIR.mkdir(exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Rechnung diktieren")])
    alt_names = [x509.DNSName("localhost"), x509.DNSName(socket.gethostname()), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    alt_names += [x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips]
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(key, hashes.SHA256())
    )
    KEY_FILE.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def ensure_ollama() -> bool:
    """Prüft, ob Ollama läuft und das KI-Modell da ist; lädt das Modell beim ersten Mal automatisch."""
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    try:
        tags = httpx.get(f"{url}/api/tags", timeout=5).json()
    except (httpx.HTTPError, ValueError):
        if shutil.which("ollama") is None:
            print("\n  Ollama ist nicht installiert.")
            print("  Bitte von https://ollama.com/download installieren und start.bat erneut starten.\n")
        else:
            print("\n  Ollama ist installiert, läuft aber nicht.")
            print("  Bitte Ollama über das Startmenü öffnen und start.bat erneut starten.\n")
        return False

    installed = {m.get("name") for m in tags.get("models", [])} | {m.get("model") for m in tags.get("models", [])}
    if model in installed or f"{model}:latest" in installed:
        return True
    print(f"\n  Lade das KI-Modell {model} (ca. 5 GB, nur beim ersten Mal) ...\n")
    try:
        result = subprocess.run(["ollama", "pull", model])
    except FileNotFoundError:
        print(f"\n  Bitte einmal in der Eingabeaufforderung ausführen: ollama pull {model}\n")
        return False
    if result.returncode != 0:
        print("\n  Der Download hat nicht geklappt. Bitte Internetverbindung prüfen und start.bat erneut starten.\n")
        return False
    return True


def main() -> None:
    load_env(ROOT / ".env")
    if not os.environ.get("APP_PASSWORD") or not os.environ.get("SEVDESK_API_TOKEN"):
        print("\n  Bitte zuerst die Datei .env ausfüllen (SEVDESK_API_TOKEN und APP_PASSWORD).\n")
        return
    if os.environ.get("AI_PROVIDER", "ollama").lower() == "ollama" and not ensure_ollama():
        return

    ips = lan_ips()
    if not cert_covers(ips):
        create_cert(ips)
        print("  Neues Zertifikat erstellt. Am Handy einmal die Sicherheitswarnung bestätigen.")

    print("\n  ==============================================")
    print("   Rechnung diktieren läuft!")
    print(f"   Am PC:    https://localhost:{PORT}")
    for index, ip in enumerate(ips):
        print(f"   {'Am Handy: ' if index == 0 else 'oder:     '}https://{ip}:{PORT}")
    print("   (Handy muss im selben WLAN sein)")
    print("   Beenden: dieses Fenster schließen")
    print("  ==============================================\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, ssl_certfile=str(CERT_FILE), ssl_keyfile=str(KEY_FILE), log_level="warning")


if __name__ == "__main__":
    main()
