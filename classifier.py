import os
from llm_client import LLMClient
from config import VALID_CATEGORIES, VALID_PRIORITIES

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "classify.txt")


def _load_prompt() -> str:
    with open(_PROMPT_PATH) as f:
        return f.read()


def normalise_category(raw: str) -> str:
    """Case-insensitive match against VALID_CATEGORIES. Returns 'Unknown' on miss."""
    for cat in VALID_CATEGORIES:
        if cat.lower() == raw.strip().lower():
            return cat
    return "Unknown"


def normalise_priority(raw: str) -> str:
    """Case-insensitive match against VALID_PRIORITIES. Returns 'Low' on miss."""
    for pri in VALID_PRIORITIES:
        if pri.lower() == raw.strip().lower():
            return pri
    return "Low"


def classify(message: str, client: LLMClient) -> dict:
    prompt = _load_prompt()
    result = client.chat_json(prompt, message)

    raw_confidence = result.get("confidence", 0.0)
    # Auto-detect percentage vs decimal
    confidence = raw_confidence / 100.0 if raw_confidence > 1.0 else raw_confidence

    return {
        "category": normalise_category(result.get("category", "")),
        "priority": normalise_priority(result.get("priority", "")),
        "confidence": round(float(confidence), 4),
        "reasoning": result.get("reasoning", ""),
    }
