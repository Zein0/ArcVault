import datetime
from llm_client import LLMClient
from classifier import classify
from enricher import enrich
from router import route


def process(source: str, message: str, client: LLMClient) -> dict:
    """Run all pipeline steps for a single message."""
    classification = classify(message, client)
    enrichment = enrich(message, classification, client)
    routing = route(message, classification)

    return {
        "input": {"source": source, "message": message},
        "classification": classification,
        "enrichment": enrichment,
        "routing": routing,
        "metadata": {
            "provider": client.provider,
            "model": client.model,
            "pipeline_version": "1.0.0",
            "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
        },
    }
