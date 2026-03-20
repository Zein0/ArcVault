import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from router import route, _extract_dollar_amounts
from classifier import normalise_category, normalise_priority


# ── Dollar Extraction ─────────────────────────────────────────────────────────

def test_extract_simple_dollar():
    assert _extract_dollar_amounts("charge of $1,240") == [1240.0]

def test_extract_decimal_dollar():
    assert _extract_dollar_amounts("price is $49.99") == [49.99]

def test_extract_multiple_amounts():
    amounts = _extract_dollar_amounts("was $980, now $1,240")
    assert 980.0 in amounts
    assert 1240.0 in amounts

def test_extract_no_amounts():
    assert _extract_dollar_amounts("no money mentioned") == []


# ── Category Normalisation ────────────────────────────────────────────────────

def test_normalise_category_exact():
    assert normalise_category("Bug Report") == "Bug Report"

def test_normalise_category_lowercase():
    assert normalise_category("bug report") == "Bug Report"

def test_normalise_category_uppercase():
    assert normalise_category("BUG REPORT") == "Bug Report"

def test_normalise_category_unknown():
    assert normalise_category("Complaint") == "Unknown"

def test_normalise_priority_lowercase():
    assert normalise_priority("high") == "High"

def test_normalise_priority_uppercase():
    assert normalise_priority("LOW") == "Low"

def test_normalise_priority_unknown_defaults_low():
    assert normalise_priority("urgent") == "Low"


# ── Queue Routing ─────────────────────────────────────────────────────────────

def _cls(category, confidence=0.90):
    return {"category": category, "confidence": confidence, "priority": "Medium"}

def test_route_bug_report():
    r = route("some bug", _cls("Bug Report"))
    assert r["queue"] == "Engineering"
    assert not r["escalation_flag"]

def test_route_feature_request():
    r = route("feature idea", _cls("Feature Request"))
    assert r["queue"] == "Product"
    assert not r["escalation_flag"]

def test_route_billing_no_escalation():
    r = route("invoice looks wrong, $200 charge", _cls("Billing Issue"))
    assert r["queue"] == "Billing"
    assert not r["escalation_flag"]

def test_route_technical_question():
    r = route("how do I configure X?", _cls("Technical Question"))
    assert r["queue"] == "IT/Security"
    assert not r["escalation_flag"]

def test_route_incident_outage():
    r = route("server error", _cls("Incident/Outage"))
    assert r["queue"] == "Engineering"

def test_route_unknown_category_fallback():
    r = route("something", _cls("Unknown"))
    assert r["queue"] == "General Support"


# ── Escalation: Low Confidence ────────────────────────────────────────────────

def test_escalate_low_confidence():
    r = route("some message", _cls("Bug Report", confidence=0.65))
    assert r["escalation_flag"] is True
    assert r["queue"] == "Human Review"

def test_no_escalate_at_exactly_threshold():
    """0.70 confidence should NOT escalate (threshold is strictly <)."""
    r = route("some message", _cls("Bug Report", confidence=0.70))
    assert r["escalation_flag"] is False

def test_escalate_just_below_threshold():
    """0.69 confidence SHOULD escalate."""
    r = route("some message", _cls("Bug Report", confidence=0.69))
    assert r["escalation_flag"] is True


# ── Escalation: Keywords ──────────────────────────────────────────────────────

def test_escalate_keyword_outage():
    r = route("there is an outage", _cls("Incident/Outage"))
    assert r["escalation_flag"] is True

def test_escalate_keyword_multiple_users():
    r = route("multiple users affected by this", _cls("Bug Report"))
    assert r["escalation_flag"] is True

def test_escalate_keyword_data_loss():
    r = route("we are experiencing data loss", _cls("Bug Report"))
    assert r["escalation_flag"] is True

def test_escalate_keyword_security_breach():
    r = route("possible security breach detected", _cls("Bug Report"))
    assert r["escalation_flag"] is True

def test_escalate_keyword_critical():
    r = route("this is critical and must be fixed", _cls("Bug Report"))
    assert r["escalation_flag"] is True

def test_no_escalate_normal_message():
    r = route("I have a general question about the API", _cls("Technical Question"))
    assert r["escalation_flag"] is False


# ── Escalation: Billing > $500 ────────────────────────────────────────────────

def test_escalate_billing_over_threshold():
    r = route(
        "Invoice #8821 shows $1,240 but contract is $980",
        _cls("Billing Issue"),
    )
    assert r["escalation_flag"] is True
    assert r["queue"] == "Human Review"

def test_no_escalate_billing_under_threshold():
    r = route("I was charged $200 instead of $150", _cls("Billing Issue"))
    assert r["escalation_flag"] is False

def test_no_escalate_billing_exactly_threshold():
    """$500 is NOT > $500, should not escalate."""
    r = route("I was charged $500 extra", _cls("Billing Issue"))
    assert r["escalation_flag"] is False

def test_billing_escalation_only_for_billing_category():
    """Large amount in non-billing category should not trigger billing escalation."""
    r = route("our contract is worth $2,000 monthly", _cls("Feature Request"))
    assert r["escalation_flag"] is False
