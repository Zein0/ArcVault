# ArcVault Triage Pipeline — Architecture

## What It Does

Incoming customer messages are processed through a six-step pipeline that transforms raw text into a structured, routed ticket:

```
[1] Ingest → [2] Classify (LLM) → [3] Enrich (LLM) → [4] Route → [5] Escalate → [6] Output
```

Five sample inputs cover the full decision surface: bug reports, feature requests, billing disputes, technical questions, and incident reports.

---

## Separation of Concerns: LLM vs Python

The core design principle is a hard boundary between interpretation and decision-making.

**LLM handles interpretation (Steps 2–3):**
- `classifier.py` asks the LLM: "what kind of message is this, how urgent, and how confident are you?"
- `enricher.py` asks the LLM: "extract entities, describe the core issue, summarise for the team"

**Python handles decisions (Steps 4–5):**
- `router.py` maps category → queue using a static dict in `config.py`
- `router.py` checks three independent escalation triggers — no LLM involved

**Why this split?** LLM output is non-deterministic. You cannot unit-test it reliably. Routing and escalation are business rules that must be auditable, testable, and predictable. Keeping them in Python means a new engineer can read `config.py` and understand exactly what will happen without running any model.

---

## File Structure

```
main.py          CLI entry point — runs all 5 samples, writes output/results.json
pipeline.py      Orchestrator — chains classify → enrich → route
classifier.py    Step 2: calls LLM, validates output against VALID_CATEGORIES
enricher.py      Step 3: calls LLM, extracts entities and summary
router.py        Steps 4+5: deterministic routing dict + 3 escalation triggers
llm_client.py    Dual-provider wrapper (OpenAI / Ollama), same openai SDK for both
config.py        Single source of truth for all config: categories, queues, keywords, samples
prompts/         classify.txt and enrich.txt — system prompts for each LLM step
```

---

## LLM Provider Switching

Both OpenAI and Ollama are accessed via the `openai` Python SDK. Ollama exposes an OpenAI-compatible `/v1` endpoint. The only difference is the `base_url` and `api_key` passed to `OpenAI()`.

Switching provider: set `LLM_PROVIDER=ollama` in `.env`. Zero code changes.

This is possible because the interface is identical — `client.chat.completions.create(...)` works for both. `llm_client.py` wraps this in a `chat_json()` method that also strips markdown code fences before JSON parsing (some models wrap JSON in triple backticks).

---

## The Three Escalation Triggers

Any single trigger fires escalation (OR logic, not AND). They protect against different failure modes:

| Trigger | Condition | Why |
|---------|-----------|-----|
| Low confidence | `confidence < 0.70` | LLM isn't sure — don't route blindly |
| Keyword match | Hardcoded list of high-severity phrases | Catch urgent language the LLM might downgrade |
| Billing amount | `amount > $500` AND category is Billing Issue | Financial risk threshold; deterministic via regex |

The keyword list lives in `config.py` as `ESCALATION_KEYWORDS`. The billing threshold is `BILLING_ESCALATION_THRESHOLD = 500.0`. Both can be changed without touching any logic code.

Confidence supports both decimal (`0.70`) and percentage (`70`) formats. `config.py` auto-normalises on load.

---

## Output Schema

Each processed message produces:

```json
{
  "input": { "source": "Email", "message": "..." },
  "classification": {
    "category": "Bug Report",
    "priority": "Medium",
    "confidence": 0.92,
    "reasoning": "..."
  },
  "enrichment": {
    "core_issue": "...",
    "entities": ["403 error", "arcvault.io/user/jsmith"],
    "urgency_signal": "normal",
    "summary": "..."
  },
  "routing": {
    "queue": "Engineering",
    "escalation_flag": false,
    "escalation_reason": null
  },
  "metadata": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "pipeline_version": "1.0.0",
    "processed_at": "2026-03-20T..."
  }
}
```

The `metadata` block makes results reproducible — you can compare OpenAI vs Ollama runs and trace exactly what model produced what output.

---

## n8n Variant (n8n-integration branch)

The `n8n-integration` branch adds two files on top of `main`:

- `api.py` — a ~30-line FastAPI wrapper exposing `POST /process`, `POST /batch`, `GET /health`
- `n8n/workflow.json` — an importable n8n workflow: Webhook → HTTP Request (calls `/process`) → IF (escalation_flag) → branch to ESCALATED or NORMAL → Respond

The Python backend is identical. n8n provides visual orchestration and webhook management without changing any pipeline logic.

---

## What I'd Change at Production Scale

**1. Async processing.** The current pipeline blocks on two sequential LLM calls per message. At volume, replace with async workers (Celery + Redis, or AWS SQS + Lambda). The `pipeline.py` interface is already clean enough to slot in — just wrap `process()` in a task.

**2. Retry + dead-letter queue.** LLM API calls fail transiently. Wrap `chat_json()` in exponential backoff (tenacity). Failed messages after N retries go to a dead-letter queue for manual review rather than silently dropping.

**3. Confidence monitoring.** Log confidence scores and escalation rates to a time-series store. A drift toward lower confidence scores is an early signal that the prompt needs updating (model upgrade, prompt degradation, category distribution shift).

**4. Prompt versioning.** Store prompt text in a database or S3 with version IDs. A/B test new prompts on a shadow traffic split before full rollout. Flat files are fine for a prototype; at scale you need rollback capability.

**5. Feedback loop.** Human reviewers correcting misclassified tickets are the best training signal available. Store corrections and periodically inject them as few-shot examples in the classification prompt. This closes the loop between human judgment and model output.

---

## Phase 2: What I'd Add With Another Week

**1. Human-in-the-loop review UI.** Escalated tickets currently land in "Human Review" with no interface. I'd build a minimal FastAPI page showing the ticket, the classification reasoning, and two buttons: Confirm or Override. Overrides get logged as labelled training examples.

**2. Feedback loop into the prompt.** Collect confirmed overrides from the review UI and automatically inject the 5 most recent corrections as few-shot examples in `classify.txt`. This lets the prompt improve without any model retraining — just better context.

**3. Typed entity extraction.** The current `entities` field is a flat string array (`["403", "$1,240"]`). I'd change `enrich.txt` to return typed objects: `[{"type": "error_code", "value": "403"}, {"type": "amount", "value": 1240}]`. This makes downstream filtering and alerting possible without regex on free text.

**4. Multi-language support.** Add a language detection step before classification. Route non-English messages to a translation layer first, then through the same pipeline. Most LLMs handle this natively but explicit detection prevents silent degradation on mixed-language inputs.

**5. Confidence calibration.** The current self-reported confidence scores are not well-calibrated. I'd run the pipeline on 100 labelled examples, plot confidence vs. actual accuracy, and set the escalation threshold empirically rather than using the arbitrary 0.70 default.
