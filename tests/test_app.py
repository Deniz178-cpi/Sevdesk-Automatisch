import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app import auth, main
from app.extractor import extract_invoice
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


def login(http: TestClient, password: str = "geheim"):
    return http.post("/login", data={"password": password}, follow_redirects=False)


@pytest.fixture
def client():
    captured = []
    sevdesk = fake_sevdesk(captured)
    claude = FakeClaude(EXTRACTED)
    main.app.dependency_overrides[main.get_sevdesk] = lambda: sevdesk
    main.app.dependency_overrides[main.get_claude] = lambda: claude
    http = TestClient(main.app)
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
    result = extract_invoice(claude, "5 Stunden Webdesign ...", units, today=date(2026, 10, 20))
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
    http = TestClient(main.app)
    assert http.get("/healthz").status_code == 200
    assert http.get("/", follow_redirects=False).headers["location"] == "/login"
    assert http.post("/api/parse", json={"text": "x"}).status_code == 401
    assert login(http, "falsch").headers["location"] == "/login?fehler=falsch"
    assert http.get("/api/meta").status_code == 401
    assert login(http).headers["location"] == "/"
    assert http.get("/").status_code == 200


def test_app_is_closed_without_password(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD")
    http = TestClient(main.app)
    assert http.get("/").status_code == 503
    assert http.post("/api/invoice", json={}).status_code == 503


def test_lockout_after_failed_attempts():
    http = TestClient(main.app)
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
