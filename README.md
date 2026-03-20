# ArcVault Triage Pipeline

AI-powered intake pipeline for customer support messages. Classifies, enriches, routes, and escalates tickets using an LLM + deterministic business rules.

---

## What It Does

Takes a raw customer message and produces a structured ticket in one pass:

1. **Classify** — LLM assigns category, priority, and confidence score
2. **Enrich** — LLM extracts entities, core issue, and a team-facing summary
3. **Route** — Python maps category → queue using a static dict (no LLM)
4. **Escalate** — Python checks 3 independent triggers (no LLM)

### Queue Routing

| Category | Queue |
|----------|-------|
| Bug Report | Engineering |
| Feature Request | Product |
| Billing Issue | Billing |
| Technical Question | IT/Security |
| Incident/Outage | Engineering |

### Escalation Triggers (any one fires it)

| Trigger | Condition |
|---------|-----------|
| Low confidence | `confidence < 0.70` |
| Keyword match | "outage", "data loss", "critical", "security breach", "multiple users affected", … |
| Billing dispute | Amount `> $500` in a Billing Issue message |

---

## Branches

| Branch | What it adds |
|--------|-------------|
| `main` | Pure Python pipeline — `python main.py` |
| `n8n-integration` | FastAPI wrapper (`api.py`) + n8n workflow (`n8n/workflow.json`) |

---

## Setup

**Requirements:** Python 3.11+

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=your-key-here
```

### Using Ollama instead of OpenAI

```bash
# 1. Install Ollama: https://ollama.ai
# 2. Pull a model:
ollama pull qwen2.5-coder:7b

# 3. In .env:
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5-coder:7b
```

No code changes needed — both providers use the same `openai` SDK interface.

---

## Run

```bash
python main.py
```

Processes all 5 sample inputs and writes results to `output/results.json`.

### Expected output

```
Provider: openai / Model: gpt-4o-mini

Processing message 1...
  [OK] Bug Report / Medium → Engineering (conf=92%)

Processing message 2...
  [OK] Feature Request / Low → Product (conf=95%)

Processing message 3...
  [ESCALATED] Billing Issue / Medium → Human Review (conf=88%)
  Reason: Billing dispute exceeds $500

Processing message 4...
  [OK] Technical Question / Low → IT/Security (conf=91%)

Processing message 5...
  [ESCALATED] Incident/Outage / High → Human Review (conf=94%)
  Reason: Escalation keyword detected

Results saved to output/results.json
```

Messages 3 and 5 always escalate — the triggers are deterministic and don't depend on the LLM.

---

## Tests

```bash
python -m pytest tests/ -v
```

30 unit tests covering routing, escalation, dollar extraction, and category normalisation. **No API key needed** — tests only cover deterministic Python logic, never LLM output.

```bash
python -m ruff check .   # lint
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Ollama model |
| `CONFIDENCE_THRESHOLD` | `0.70` | Escalate if below (accepts `0.70` or `70`) |
| `OUTPUT_DIR` | `output` | Where to write `results.json` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Project Structure

```
main.py              CLI entry point
pipeline.py          Orchestrator — chains classify → enrich → route
classifier.py        Step 2: LLM classification + output validation
enricher.py          Step 3: LLM enrichment + entity extraction
router.py            Steps 4+5: deterministic routing + escalation
llm_client.py        Dual-provider wrapper (OpenAI / Ollama)
config.py            All config: categories, queues, keywords, thresholds, samples
prompts/
  classify.txt       Classification system prompt
  enrich.txt         Enrichment system prompt
output/
  results.json       Generated output (created on first run)
tests/
  test_pipeline.py   Unit tests — routing, escalation, validation only
docs/
  architecture.md    System design and tradeoff analysis
  prompt_docs.md     Prompt design, weaknesses, and improvement notes
```

---

## Docs

- [`docs/architecture.md`](docs/architecture.md) — system design, LLM/Python split rationale, escalation triggers, production scale considerations
- [`docs/prompt_docs.md`](docs/prompt_docs.md) — prompt design decisions, known weaknesses, what I'd improve
