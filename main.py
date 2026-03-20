import json
import os
from llm_client import LLMClient
from pipeline import process
from config import SAMPLE_INPUTS, OUTPUT_DIR


def main():
    client = LLMClient()
    print(f"Provider: {client.provider} / Model: {client.model}\n")

    results = []
    for item in SAMPLE_INPUTS:
        print(f"Processing message {item['id']}...")
        result = process(item["source"], item["message"], client)
        results.append(result)

        r = result["routing"]
        c = result["classification"]
        status = "ESCALATED" if r["escalation_flag"] else "OK"
        print(
            f"  [{status}] {c['category']} / {c['priority']} "
            f"→ {r['queue']} (conf={c['confidence']:.0%})"
        )
        if r["escalation_reason"]:
            print(f"  Reason: {r['escalation_reason']}")
        print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
