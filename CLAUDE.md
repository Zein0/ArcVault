# ArcVault Triage Pipeline

## What This Is
AI-powered intake and triage pipeline for ArcVault (fictional B2B software company).
Takes 5 raw customer messages → classifies with LLM → extracts entities → routes to correct team → flags escalations.

## Git Strategy
- `main` branch: Python-only pipeline, triggered by `python main.py` — this is the submission
- `n8n-integration` branch: adds FastAPI wrapper + n8n workflow on top of main (bonus, same code)

## Architecture Rules
1. LLM does interpretation ONLY — classify (Step 2) and enrich (Step 3)
2. Python does decisions ONLY — route and escalate (Steps 4 + 6)
3. NEVER put routing logic in LLM prompts — routing is a dict in router.py
4. NEVER unit-test LLM output — non-deterministic, tests would be flaky
5. ALL config in config.py — categories, queues, thresholds, keywords, sample inputs
6. Temperature = 0.0 for classification (reproducibility)

## LLM Provider Switch
- `LLM_PROVIDER=openai` or `LLM_PROVIDER=ollama` in .env
- Both use the `openai` Python SDK (Ollama has compatible /v1 endpoint)
- Zero code changes to swap

## Categories
Bug Report, Feature Request, Billing Issue, Technical Question, Incident/Outage

## Priorities
Low, Medium, High

## Queue Routing (deterministic dict — NOT LLM)
- Bug Report → Engineering
- Feature Request → Product
- Billing Issue → Billing
- Technical Question → IT/Security
- Incident/Outage → Engineering
- Unknown / low confidence → General Support (fallback)

## Escalation Triggers (any one is enough)
1. Confidence < 0.70
2. Keywords in message: "outage", "down for all users", "data loss", "critical", "security breach", "all users affected", "multiple users affected", "billing error"
3. Billing dispute amount > $500

## Confidence Threshold
Supports both 0.70 (decimal) and 70 (percentage). Auto-detect: if value > 1.0, divide by 100.

## File Structure
```
arcvault-triage/
├── main.py              # CLI entry point — runs all 5 samples
├── pipeline.py          # Orchestrator — chains Steps 1→6
├── classifier.py        # Step 2: LLM classification + validation
├── enricher.py          # Step 3: LLM enrichment + entity extraction
├── router.py            # Steps 4+6: Deterministic routing + escalation
├── llm_client.py        # Dual-provider LLM client (OpenAI / Ollama)
├── config.py            # ALL config: categories, queues, thresholds, samples
├── prompts/
│   ├── classify.txt     # Classification system prompt
│   └── enrich.txt       # Enrichment system prompt
├── output/
│   └── results.json     # Generated output (deliverable)
├── tests/
│   └── test_pipeline.py # Unit tests — routing, escalation, validation only
├── docs/
│   ├── architecture.md  # System design write-up
│   └── prompt_docs.md   # Prompt documentation
├── .env.example
├── .gitignore
├── requirements.txt     # openai, python-dotenv
└── CLAUDE.md            # This file
```

## On n8n-integration branch (adds these files only)
```
├── api.py               # FastAPI wrapper (~30 lines, imports pipeline.py)
└── n8n/
    └── workflow.json    # Exported n8n workflow
```

## Commands
```bash
# Run pipeline
python main.py
LLM_PROVIDER=ollama python main.py

# Run tests (no API key needed)
python -m pytest tests/ -v

# n8n branch only
uvicorn api:app --reload --port 8000
curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"source":"Email","message":"test"}'
```

## Testing Philosophy
- Test ONLY deterministic logic: routing, escalation, dollar extraction, category normalisation
- Do NOT test LLM output
- All tests must pass before committing

## Commit Convention
feat:, fix:, test:, docs:, refactor:, chore:

## Sample Inputs
1. Email: "Hi, I tried logging in this morning and keep getting a 403 error. My account is arcvault.io/user/jsmith. This started after your update last Tuesday."
2. Web Form: "We'd love to see a bulk export feature for our audit logs. We're a compliance-heavy org and this would save us hours every month."
3. Support Portal: "Invoice #8821 shows a charge of $1,240 but our contract rate is $980/month. Can someone look into this?"
4. Email: "I'm not sure if this is the right place to ask, but is there a way to set up SSO with Okta? We're evaluating switching our auth provider."
5. Web Form: "Your dashboard stopped loading for us around 2pm EST. Checked our end — it's definitely on yours. Multiple users affected."

## Expected Results
- #1 → Bug Report / Medium / Engineering / not escalated
- #2 → Feature Request / Low / Product / not escalated
- #3 → Billing Issue / Medium / **ESCALATED** ($1,240 > $500)
- #4 → Technical Question / Low / IT/Security / not escalated
- #5 → Incident/Outage / High / **ESCALATED** (keyword: "multiple users affected")
