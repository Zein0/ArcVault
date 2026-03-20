# Claude Code Prompt Plan

Run these prompts in Claude Code in order. Each one produces a commit.
CLAUDE.md keeps Claude aligned across all prompts.

---

## PHASE 1: Python Pipeline (main branch)

### Task 1 — Scaffold + Config
```
Read CLAUDE.md. Create the full file structure described there (empty files are fine 
for now except config.py). Build config.py with: LLMConfig dataclass, VALID_CATEGORIES, 
VALID_PRIORITIES, CATEGORY_TO_QUEUE dict, ESCALATION_KEYWORDS list, 
BILLING_ESCALATION_AMOUNT=500, CONFIDENCE_THRESHOLD (supports both 0.70 and 70 formats), 
and all 5 SAMPLE_INPUTS. Also create .env.example, .gitignore, requirements.txt (openai, 
python-dotenv). Commit: "feat: project scaffold and configuration"
```

### Task 2 — LLM Client
```
Build llm_client.py. Dual-provider client using the openai SDK for both OpenAI and 
Ollama. Ollama uses base_url pointing to /v1 endpoint. Include chat() for raw text 
and chat_json() that strips markdown code fences before parsing JSON. Provider selected 
by LLM_PROVIDER env var. Commit: "feat: dual-provider LLM client"
```

### Task 3 — Classifier
```
Build classifier.py and prompts/classify.txt. The system prompt classifies into one 
of the 5 categories, assigns priority, returns confidence 0.0-1.0. The classifier.py 
must validate output against VALID_CATEGORIES and VALID_PRIORITIES from config — unknown 
values fall back to defaults. Clamp confidence to 0.0-1.0 range. 
Commit: "feat: LLM classification with validation"
```

### Task 4 — Enricher
```
Build enricher.py and prompts/enrich.txt. The enrichment prompt receives raw message 
PLUS classification result. Extracts: core_issue (one sentence), entities (list of IDs, 
error codes, amounts, dates, services), urgency_signal (critical/high/normal/low), 
summary (2-3 sentences for receiving team). Validate urgency against allowed values.
Commit: "feat: LLM enrichment with entity extraction"
```

### Task 5 — Router
```
Build router.py. PURE business logic — NO LLM calls. Takes raw_message + classification 
+ enrichment. Maps category to queue via CATEGORY_TO_QUEUE dict. Checks 3 escalation 
triggers: (1) confidence < threshold, (2) keyword match in message, (3) billing amount 
> $500 using regex dollar extraction. Returns destination_queue, escalation_flag, 
escalation_reasons list. Commit: "feat: deterministic routing and escalation"
```

### Task 6 — Pipeline + Main
```
Build pipeline.py (orchestrator: ingestion → classify → enrich → route → assemble record) 
and main.py (CLI: loops through SAMPLE_INPUTS, calls pipeline, writes output/results.json 
with metadata). Include a summary table printed to stdout. 
Commit: "feat: pipeline orchestrator and CLI runner"
```

### Task 7 — Tests
```
Build tests/test_pipeline.py. Test ALL deterministic logic:
- Each category routes to correct queue (5 tests)
- Low confidence triggers escalation
- Keywords "outage" and "multiple users affected" trigger escalation
- $1,240 billing triggers escalation, $50 does not
- Exactly 0.70 confidence does NOT escalate, 0.69 does
- Dollar extraction handles $1,240 and $49.99
- Category normalisation is case-insensitive, unknown falls back
- Priority normalisation works
- Confidence clamping (over 1.0, negative, garbage string)
Target: 25+ tests. Run them and fix any failures.
Commit: "test: 25 unit tests for routing, escalation, validation"
```

### Task 8 — Run + Verify
```
Set up .env with my OpenAI API key. Run python main.py. Verify:
- All 5 messages process without errors
- Message 3 (billing $1,240) is escalated
- Message 5 (multiple users affected) is escalated  
- Messages 1, 2, 4 are NOT escalated
- output/results.json has all 5 complete records
Then run with LLM_PROVIDER=ollama to verify it works with both providers.
Commit: "feat: verified pipeline output for all 5 inputs"
```

---

## PHASE 2: n8n Integration (branch)

### Task 9 — Branch + FastAPI
```
git checkout -b n8n-integration
Create api.py with FastAPI. Three endpoints:
- POST /process — accepts {"source": "...", "message": "..."}, returns full pipeline result
- POST /batch — accepts {"requests": [...]}, processes all
- GET /health — returns provider info and status
Add fastapi and uvicorn to requirements.txt.
Commit: "feat: FastAPI webhook wrapper"
```

### Task 10 — n8n Workflow
```
Create n8n/workflow.json. The workflow:
1. Webhook trigger node (POST, receives source + message)
2. HTTP Request node calling POST http://localhost:8000/process
3. IF node checking response.routing.escalation_flag
4. True branch → output as escalated
5. False branch → output as normal
Must be valid importable n8n JSON.
Commit: "feat: n8n workflow"
```

### Task 11 — API Tests
```
Create tests/test_api.py using pytest + httpx (not Playwright). 
Test the FastAPI endpoints directly:
- POST /process with each sample input, verify response structure
- Verify message 3 and 5 are escalated in response
- GET /health returns provider info
Run tests. Commit: "test: API endpoint tests"
```

---

## PHASE 3: Documentation (back on main)

### Task 12 — Architecture Write-Up
```
git checkout main
Write docs/architecture.md covering:
- System design: how pieces connect, what triggers what
- Key decision: LLM for interpretation, Python for routing (and WHY)
- The 3 escalation triggers and why they're independent
- What I'd change at production scale (queues, retries, monitoring, cost)
- Phase 2 ideas (feedback loop, multi-language, embeddings)
Keep it 1-2 pages. Specific, not generic.
Commit: "docs: architecture write-up"
```

### Task 13 — Prompt Documentation
```
Write docs/prompt_docs.md. For each prompt (classify.txt, enrich.txt):
- What it does
- Why structured that way
- Tradeoffs made
- What I'd improve (confidence calibration, typed entities, few-shot examples)
Be honest about weaknesses.
Commit: "docs: prompt documentation"
```

### Task 14 — Final Sweep
```
Run pytest. Verify output/results.json exists with 5 records. Check messages 3 and 5 
are escalated. Fix anything broken. 
Commit: "chore: final validation — all tests passing"
```
