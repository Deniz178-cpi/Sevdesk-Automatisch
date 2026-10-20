"""Startet die App im Heimnetz: lädt .env, erzeugt ein HTTPS-Zertifikat und zeigt die Adresse fürs Handy."""

import datetime
import ipaddress
import os
import socket
from pathlib import Path

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

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


def lan_ip() -> str | None:
    """IP-Adresse dieses Rechners im WLAN/LAN (es werden dabei keine Daten verschickt)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 80))
            ip = s.getsockname()[0]
        return ip if ipaddress.ip_address(ip).is_private else None
    except OSError:
        return None


def cert_covers(ip: str | None) -> bool:
    if not (CERT_FILE.exists() and KEY_FILE.exists()):
        return False
    cert = x509.load_pem_x509_certificate(CERT_FILE.read_bytes())
    if cert.not_valid_after_utc < datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30):
        return False
    if ip is None:
        return True
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    return ipaddress.ip_address(ip) in names.get_values_for_type(x509.IPAddress)


def create_cert(ip: str | None) -> None:
    """Selbst signiertes Zertifikat, damit der Browser das Mikrofon freigibt (nur über HTTPS erlaubt)."""
    CERT_DIR.mkdir(exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Rechnung diktieren")])
    alt_names = [x509.DNSName("localhost"), x509.DNSName(socket.gethostname()), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    if ip:
        alt_names.append(x509.IPAddress(ipaddress.ip_address(ip)))
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


def main() -> None:
    load_env(ROOT / ".env")
    if not os.environ.get("APP_PASSWORD") or not os.environ.get("SEVDESK_API_TOKEN"):
        print("\n  Bitte zuerst die Datei .env ausfüllen (SEVDESK_API_TOKEN und APP_PASSWORD).\n")
        return

    ip = lan_ip()
    if not cert_covers(ip):
        create_cert(ip)
        print("  Neues Zertifikat erstellt. Am Handy einmal die Sicherheitswarnung bestätigen.")

    print("\n  ==============================================")
    print("   Rechnung diktieren läuft!")
    print(f"   Am PC:    https://localhost:{PORT}")
    if ip:
        print(f"   Am Handy: https://{ip}:{PORT}")
    print("   (Handy muss im selben WLAN sein)")
    print("   Beenden: dieses Fenster schließen")
    print("  ==============================================\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, ssl_certfile=str(CERT_FILE), ssl_keyfile=str(KEY_FILE), log_level="warning")


if __name__ == "__main__":
    main()
