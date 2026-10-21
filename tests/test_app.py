import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app import auth, main
from app.extractor import extract_with_claude, extract_with_ollama, normalize
from app.sevdesk import BASE_URL, SevdeskClient, SevdeskError, build_invoice_payload

CONTACTS = [
    {"id": "11", "name": "Bäckerei Müller GmbH", "customerNumber": "1001"},
    {"id": "12", "surename": "Anna", "familyname": "Schmidt", "customerNumber": "1002"},
    {"id": "13", "name": "Autohaus Weber", "customerNumber": "1003"},
]
UNITS = [{"id": "1", "name": "Stk"}, {"id": "9", "name": "Std"}, {"id": "7", "name": "pauschal"}]


def fake_sevdesk(captured: list):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "test-token"
        path = request.url.path.removeprefix("/api/v1")
        if path == "/Contact":
            return httpx.Response(200, json={"objects": CONTACTS})
        if path == "/Unity":
            return httpx.Response(200, json={"objects": UNITS})
        if path == "/SevUser":
            return httpx.Response(200, json={"objects": [{"id": "77"}]})
        if path == "/Invoice/Factory/saveInvoice":
            captured.append(json.loads(request.content))
            return httpx.Response(201, json={"objects": {"invoice": {"id": "555", "invoiceNumber": "RE-1042"}}})
        return httpx.Response(404, json={"error": "unknown"})

    http = httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return SevdeskClient("test-token", http=http)


class FakeClaude:
    def __init__(self, result: dict):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._result = result

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(self._result))])


EXTRACTED = {
    "customer_name": "Bäckerei Müller",
    "invoice_date": None,
    "delivery_date": "2026-10-16",
    "header": None,
    "head_text": None,
    "foot_text": None,
    "time_to_pay": 14,
    "positions": [
        {"name": "Webdesign", "description": None, "quantity": 5, "unit": "Std", "price_net": 80, "tax_rate": 19},
        {"name": "Hosting", "description": "Jahrespauschale", "quantity": 1, "unit": "pauschal", "price_net": 120, "tax_rate": 19},
    ],
    "hints": [],
}


@pytest.fixture(autouse=True)
def password(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    auth._failures.clear()


LAN_CLIENT = ("192.168.1.20", 50000)


def lan_client() -> TestClient:
    return TestClient(main.app, client=LAN_CLIENT)


def login(http: TestClient, password: str = "geheim"):
    return http.post("/login", data={"password": password}, follow_redirects=False)


@pytest.fixture
def client():
    captured = []
    sevdesk = fake_sevdesk(captured)
    claude = FakeClaude(EXTRACTED)
    main.app.dependency_overrides[main.get_sevdesk] = lambda: sevdesk
    main.app.dependency_overrides[main.get_extractor] = lambda: (lambda text, units: extract_with_claude(claude, text, units))
    http = lan_client()
    assert login(http).headers["location"] == "/"
    yield http, captured, claude
    main.app.dependency_overrides.clear()


def test_contact_matching_finds_partial_names():
    sevdesk = fake_sevdesk([])
    assert sevdesk.match_contacts("Bäckerei Müller")[0]["id"] == 11
    assert sevdesk.match_contacts("müller")[0]["id"] == 11
    assert sevdesk.match_contacts("Anna Schmidt")[0]["name"] == "Anna Schmidt"
    assert sevdesk.match_contacts("Weber")[0]["id"] == 13


def test_extract_maps_units_and_sends_date():
    claude = FakeClaude(EXTRACTED)
    units = [{"id": 1, "name": "Stk"}, {"id": 9, "name": "Std"}, {"id": 7, "name": "pauschal"}]
    result = extract_with_claude(claude, "5 Stunden Webdesign ...", units, today=date(2026, 10, 20))
    assert [p["unit_id"] for p in result["positions"]] == [9, 7]
    call = claude.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert "Dienstag, der 2026-10-20" in call["messages"][0]["content"]
    assert call["output_config"]["format"]["type"] == "json_schema"


def test_parse_endpoint_preselects_best_contact(client):
    http, _, _ = client
    response = http.post("/api/parse", json={"text": "Rechnung an Bäckerei Müller ..."})
    assert response.status_code == 200
    body = response.json()
    assert body["contact_id"] == 11
    assert body["positions"][0]["unit_id"] == 9


def test_invoice_endpoint_creates_draft(client):
    http, captured, _ = client
    response = http.post("/api/invoice", json={
        "contact_id": 11,
        "invoice_date": "2026-10-20",
        "delivery_date": "2026-10-16",
        "time_to_pay": 14,
        "positions": [{"name": "Webdesign", "quantity": 5, "unit_id": 9, "price_net": 80, "tax_rate": 19}],
    })
    assert response.status_code == 200
    assert response.json() == {"id": "555", "invoiceNumber": "RE-1042", "url": "https://my.sevdesk.de/fi/detail/type/RE/id/555"}

    invoice = captured[0]["invoice"]
    assert invoice["status"] == "100"
    assert invoice["contact"] == {"id": 11, "objectName": "Contact"}
    assert invoice["contactPerson"] == {"id": 77, "objectName": "SevUser"}
    assert invoice["invoiceDate"] == "20.10.2026"
    assert invoice["deliveryDate"] == "16.10.2026"
    assert invoice["taxRule"] == {"id": 1, "objectName": "TaxRule"}
    assert captured[0]["takeDefaultAddress"] is True
    pos = captured[0]["invoicePosSave"][0]
    assert pos["unity"] == {"id": 9, "objectName": "Unity"}
    assert (pos["quantity"], pos["price"], pos["taxRate"]) == (5.0, 80.0, 19.0)


def test_payload_requires_contact_and_positions():
    with pytest.raises(SevdeskError):
        build_invoice_payload({"contact_id": None, "positions": [{}]}, 1)
    with pytest.raises(SevdeskError):
        build_invoice_payload({"contact_id": 1, "positions": []}, 1)


def test_requires_login():
    http = lan_client()
    assert http.get("/healthz").status_code == 200
    assert http.get("/", follow_redirects=False).headers["location"] == "/login"
    assert http.post("/api/parse", json={"text": "x"}).status_code == 401
    assert login(http, "falsch").headers["location"] == "/login?fehler=falsch"
    assert http.get("/api/meta").status_code == 401
    assert login(http).headers["location"] == "/"
    assert http.get("/").status_code == 200


def test_app_is_closed_without_password(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD")
    http = lan_client()
    assert http.get("/").status_code == 503
    assert http.post("/api/invoice", json={}).status_code == 503


def test_lockout_after_failed_attempts():
    http = lan_client()
    for _ in range(auth.MAX_FAILURES - 1):
        assert login(http, "falsch").headers["location"] == "/login?fehler=falsch"
    assert login(http, "falsch").headers["location"] == "/login?fehler=gesperrt"
    # Auch das richtige Passwort wird während der Sperre abgelehnt.
    assert login(http).headers["location"] == "/login?fehler=gesperrt"
    assert http.get("/api/meta").status_code == 401


def test_logout_and_password_change_end_session(client, monkeypatch):
    http, _, _ = client
    assert http.get("/").status_code == 200
    monkeypatch.setenv("APP_PASSWORD", "neues-passwort")
    assert http.get("/", follow_redirects=False).status_code == 303
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    assert http.get("/").status_code == 200
    http.post("/logout")
    assert http.get("/", follow_redirects=False).headers["location"] == "/login"


def test_forged_or_expired_session_rejected():
    assert not auth.valid_session("9999999999.abc", "geheim")
    assert not auth.valid_session(auth.make_session("geheim", now=0), "geheim")
    assert auth.valid_session(auth.make_session("geheim"), "geheim")


def test_blocks_devices_outside_local_network(monkeypatch):
    internet = TestClient(main.app, client=("8.8.8.8", 50000))
    assert internet.get("/login").status_code == 403
    assert login(internet).status_code == 403
    assert internet.get("/healthz").status_code == 403
    # Gefälschter X-Forwarded-For-Header hilft nicht, solange TRUST_PROXY nicht gesetzt ist.
    assert internet.get("/login", headers={"X-Forwarded-For": "192.168.1.5"}).status_code == 403
    for ip in ("127.0.0.1", "10.0.0.7", "172.16.0.3", "fd00::5"):
        assert TestClient(main.app, client=(ip, 50000)).get("/login").status_code == 200
    monkeypatch.setenv("LAN_ONLY", "0")
    assert internet.get("/login").status_code == 200


def test_ollama_extraction_and_errors():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if body["model"] == "fehlt":
            return httpx.Response(404, json={"error": "model not found"})
        messy = {**EXTRACTED, "time_to_pay": "14", "invoice_date": "kein Datum",
                 "positions": [{"name": "Webdesign", "quantity": "5", "unit": "std", "price_net": "80,5", "tax_rate": 16},
                               {"name": "", "quantity": 1}]}
        return httpx.Response(200, json={"message": {"role": "assistant", "content": json.dumps(messy)}, "done": True})

    http = httpx.Client(base_url="http://ollama", transport=httpx.MockTransport(handler))
    units = [{"id": 1, "name": "Stk"}, {"id": 9, "name": "Std"}]
    result = extract_with_ollama(http, "qwen2.5:7b", "Diktat", units, today=date(2026, 10, 20))
    assert seen[0]["stream"] is False and seen[0]["format"]["type"] == "object"
    assert result["time_to_pay"] == 14 and result["invoice_date"] is None
    assert result["positions"] == [{"name": "Webdesign", "description": None, "quantity": 5.0, "unit": "Std",
                                    "unit_id": 9, "price_net": 80.5, "tax_rate": 19}]
    assert any("16 %" in h for h in result["hints"])

    from app.extractor import ExtractionError
    with pytest.raises(ExtractionError, match="ollama pull fehlt"):
        extract_with_ollama(http, "fehlt", "Diktat", units)

    def offline(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ExtractionError, match="Ollama läuft nicht"):
        extract_with_ollama(httpx.Client(base_url="http://ollama", transport=httpx.MockTransport(offline)), "m", "x", units)


def test_normalize_handles_garbage():
    assert normalize({})["positions"] == []
    assert normalize({"positions": ["kaputt", {"name": "A", "quantity": None}]})["positions"][0]["quantity"] == 1


def test_start_creates_certificate_for_lan_ip(tmp_path, monkeypatch):
    import start
    monkeypatch.setattr(start, "CERT_DIR", tmp_path)
    monkeypatch.setattr(start, "CERT_FILE", tmp_path / "cert.pem")
    monkeypatch.setattr(start, "KEY_FILE", tmp_path / "key.pem")
    assert not start.cert_covers("192.168.1.20")
    start.create_cert("192.168.1.20")
    assert start.cert_covers("192.168.1.20")
    assert not start.cert_covers("192.168.1.99")

    env = tmp_path / ".env"
    env.write_text("# Kommentar\nFOO_TEST=bar\nQUOTED_TEST=\"x y\"\n", encoding="utf-8")
    monkeypatch.delenv("FOO_TEST", raising=False)
    monkeypatch.delenv("QUOTED_TEST", raising=False)
    start.load_env(env)
    assert start.os.environ["FOO_TEST"] == "bar" and start.os.environ["QUOTED_TEST"] == "x y"
    monkeypatch.delenv("FOO_TEST")
    monkeypatch.delenv("QUOTED_TEST")


def test_start_checks_ollama(monkeypatch):
    import start

    class FakeResponse:
        def __init__(self, models):
            self._models = models

        def json(self):
            return {"models": self._models}

    pulled = []
    monkeypatch.setattr(start.subprocess, "run", lambda cmd: pulled.append(cmd) or SimpleNamespace(returncode=0))

    monkeypatch.setattr(start.httpx, "get", lambda *a, **k: FakeResponse([{"name": "qwen2.5:7b", "model": "qwen2.5:7b"}]))
    assert start.ensure_ollama() and pulled == []

    monkeypatch.setattr(start.httpx, "get", lambda *a, **k: FakeResponse([]))
    assert start.ensure_ollama() and pulled == [["ollama", "pull", "qwen2.5:7b"]]

    def offline(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(start.httpx, "get", offline)
    monkeypatch.setattr(start.shutil, "which", lambda name: None)
    assert not start.ensure_ollama()
