import re
from config import (
    CATEGORY_TO_QUEUE,
    FALLBACK_QUEUE,
    CONFIDENCE_THRESHOLD,
    ESCALATION_KEYWORDS,
    BILLING_ESCALATION_THRESHOLD,
)


def _extract_dollar_amounts(text: str) -> list[float]:
    """Extract all dollar amounts from text. Handles $1,240 and $49.99 formats."""
    matches = re.findall(r"\$[\d,]+(?:\.\d{1,2})?", text)
    amounts = []
    for m in matches:
        cleaned = m.replace("$", "").replace(",", "")
        try:
            amounts.append(float(cleaned))
        except ValueError:
            pass
    return amounts


def _check_keyword_escalation(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in ESCALATION_KEYWORDS)


def _check_billing_escalation(message: str, category: str) -> bool:
    if category != "Billing Issue":
        return False
    amounts = _extract_dollar_amounts(message)
    return any(a > BILLING_ESCALATION_THRESHOLD for a in amounts)


def route(message: str, classification: dict) -> dict:
    """
    Deterministic routing and escalation. No LLM calls.
    Returns: { queue, escalation_flag, escalation_reason }
    """
    category = classification["category"]
    confidence = classification["confidence"]

    escalation_flag = False
    escalation_reason = None

    # Trigger 1: Low confidence
    if confidence < CONFIDENCE_THRESHOLD:
        escalation_flag = True
        escalation_reason = f"Low confidence: {confidence:.2%}"

    # Trigger 2: Keyword match
    elif _check_keyword_escalation(message):
        escalation_flag = True
        escalation_reason = "Escalation keyword detected"

    # Trigger 3: Billing dispute > $500
    elif _check_billing_escalation(message, category):
        escalation_flag = True
        escalation_reason = f"Billing dispute exceeds ${BILLING_ESCALATION_THRESHOLD:.0f}"

    queue = "Human Review" if escalation_flag else CATEGORY_TO_QUEUE.get(category, FALLBACK_QUEUE)

    return {
        "queue": queue,
        "escalation_flag": escalation_flag,
        "escalation_reason": escalation_reason,
    }
