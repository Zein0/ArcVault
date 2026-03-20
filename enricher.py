import os
from llm_client import LLMClient

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "enrich.txt")

_VALID_URGENCY = {"critical", "high", "normal", "low"}


def _load_prompt() -> str:
    """Read the enrichment system prompt from disk."""
    with open(_PROMPT_PATH) as f:
        return f.read()


def enrich(message: str, classification: dict, client: LLMClient) -> dict:
    """Call the LLM to extract entities and generate a team-facing summary."""
    prompt = _load_prompt()
    user_content = (
        f"Message: {message}\n\n"
        f"Classification: {classification['category']} / "
        f"{classification['priority']} / "
        f"confidence={classification['confidence']}"
    )
    result = client.chat_json(prompt, user_content)

    urgency = result.get("urgency_signal", "normal").lower().strip()
    if urgency not in _VALID_URGENCY:
        urgency = "normal"

    return {
        "core_issue": result.get("core_issue", ""),
        "entities": result.get("entities", []),
        "urgency_signal": urgency,
        "summary": result.get("summary", ""),
    }
