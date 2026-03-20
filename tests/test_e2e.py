"""
E2E tests for the FastAPI /process endpoint.

Requires the server running before pytest:
    uvicorn api:app --port 8000

Skip these tests if the server is not available:
    pytest tests/test_e2e.py -v
"""
import pytest
import httpx

BASE_URL = "http://localhost:8000"

SAMPLES = [
    {  # 1 — Bug Report, Engineering, not escalated
        "source": "Email",
        "message": (
            "Hi, I tried logging in this morning and keep getting a 403 error. "
            "My account is arcvault.io/user/jsmith. "
            "This started after your update last Tuesday."
        ),
    },
    {  # 2 — Feature Request, Product, not escalated
        "source": "Web Form",
        "message": (
            "We'd love to see a bulk export feature for our audit logs. "
            "We're a compliance-heavy org and this would save us hours every month."
        ),
    },
    {  # 3 — Billing Issue, ESCALATED ($1,240 > $500)
        "source": "Support Portal",
        "message": (
            "Invoice #8821 shows a charge of $1,240 but our contract rate is "
            "$980/month. Can someone look into this?"
        ),
    },
    {  # 4 — Technical Question, IT/Security, not escalated
        "source": "Email",
        "message": (
            "I'm not sure if this is the right place to ask, but is there a way "
            "to set up SSO with Okta? We're evaluating switching our auth provider."
        ),
    },
    {  # 5 — Incident/Outage, ESCALATED (keyword: "multiple users affected")
        "source": "Web Form",
        "message": (
            "Your dashboard stopped loading for us around 2pm EST. "
            "Checked our end — it's definitely on yours. Multiple users affected."
        ),
    },
]

VALID_QUEUES = {
    "Engineering", "Product", "Billing",
    "IT/Security", "Human Review", "General Support",
}


@pytest.fixture(scope="session")
def client():
    """Shared httpx client for the session."""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    """Server must be reachable and return provider info."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "provider" in data
    assert "model" in data


# ── Response structure ────────────────────────────────────────────────────────

def test_process_returns_all_top_level_fields(client):
    """Response must include classification, enrichment, routing, metadata."""
    r = client.post("/process", json=SAMPLES[0])
    assert r.status_code == 200
    data = r.json()
    for field in ("classification", "enrichment", "routing", "metadata"):
        assert field in data, f"missing field: {field}"


@pytest.mark.parametrize("field", ["category", "priority", "confidence", "reasoning"])
def test_classification_fields(client, field):
    """All classification fields must be present."""
    r = client.post("/process", json=SAMPLES[0])
    assert field in r.json()["classification"]


@pytest.mark.parametrize("field", ["queue", "escalation_flag", "escalation_reason"])
def test_routing_fields(client, field):
    """All routing fields must be present."""
    r = client.post("/process", json=SAMPLES[0])
    assert field in r.json()["routing"]


@pytest.mark.parametrize("field", ["core_issue", "entities", "urgency_signal", "summary"])
def test_enrichment_fields(client, field):
    """All enrichment fields must be present."""
    r = client.post("/process", json=SAMPLES[0])
    assert field in r.json()["enrichment"]


# ── Escalation logic (deterministic) ─────────────────────────────────────────

def test_message_3_escalated_billing(client):
    """Invoice #8821: $1,240 > $500 must trigger billing escalation."""
    r = client.post("/process", json=SAMPLES[2])
    assert r.status_code == 200
    routing = r.json()["routing"]
    assert routing["escalation_flag"] is True
    assert routing["queue"] == "Human Review"


def test_message_5_escalated_keyword(client):
    """'Multiple users affected' keyword must trigger escalation."""
    r = client.post("/process", json=SAMPLES[4])
    assert r.status_code == 200
    routing = r.json()["routing"]
    assert routing["escalation_flag"] is True
    assert routing["queue"] == "Human Review"


def test_message_2_not_escalated(client):
    """Feature request must NOT escalate."""
    r = client.post("/process", json=SAMPLES[1])
    assert r.status_code == 200
    assert r.json()["routing"]["escalation_flag"] is False


def test_message_4_not_escalated(client):
    """SSO question must NOT escalate."""
    r = client.post("/process", json=SAMPLES[3])
    assert r.status_code == 200
    assert r.json()["routing"]["escalation_flag"] is False


# ── Queue validity ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sample", SAMPLES)
def test_all_queues_are_valid(client, sample):
    """Every message must route to a known queue."""
    r = client.post("/process", json=sample)
    assert r.json()["routing"]["queue"] in VALID_QUEUES


# ── Validation ────────────────────────────────────────────────────────────────

def test_empty_message_returns_422(client):
    """Empty message must be rejected with 422."""
    r = client.post("/process", json={"source": "Email", "message": ""})
    assert r.status_code == 422


def test_whitespace_message_returns_422(client):
    """Whitespace-only message must be rejected with 422."""
    r = client.post("/process", json={"source": "Email", "message": "   "})
    assert r.status_code == 422


# ── Batch endpoint ────────────────────────────────────────────────────────────

def test_batch_returns_correct_count(client):
    """Batch with 2 requests must return 2 results."""
    r = client.post("/batch", json={"requests": SAMPLES[:2]})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_batch_all_five(client):
    """Batch with all 5 samples must return 5 results with correct structure."""
    r = client.post("/batch", json={"requests": SAMPLES})
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 5
    for result in results:
        assert "routing" in result
        assert result["routing"]["queue"] in VALID_QUEUES


def test_empty_batch_returns_422(client):
    """Empty batch must be rejected with 422."""
    r = client.post("/batch", json={"requests": []})
    assert r.status_code == 422
