import json
import logging
import os
from llm_client import LLMClient
from pipeline import process
from config import SAMPLE_INPUTS, OUTPUT_DIR

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
log = logging.getLogger(__name__)


def main():
    """Process all 5 sample inputs through the triage pipeline and write results.json."""
    client = LLMClient()
    log.info("Provider: %s / Model: %s\n", client.provider, client.model)

    results = []
    for item in SAMPLE_INPUTS:
        log.info("Processing message %d...", item["id"])
        result = process(item["source"], item["message"], client)
        results.append(result)

        r = result["routing"]
        c = result["classification"]
        status = "ESCALATED" if r["escalation_flag"] else "OK"
        log.info(
            "  [%s] %s / %s → %s (conf=%d%%)",
            status, c["category"], c["priority"], r["queue"],
            int(c["confidence"] * 100),
        )
        if r["escalation_reason"]:
            log.info("  Reason: %s", r["escalation_reason"])
        log.info("")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results saved to %s", output_path)


if __name__ == "__main__":
    main()
