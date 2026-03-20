# ArcVault Triage Pipeline — Prompt Documentation

## Overview

The pipeline uses two LLM prompts. Both are system prompts stored as plain text files in `prompts/`. Both return JSON only — no prose, no markdown, no explanation. This is a deliberate constraint: JSON-only output makes parsing deterministic and removes a class of parse failures.

---

## Prompt 1: Classification (`prompts/classify.txt`)

### What It Does

Takes a raw customer message and returns:
- `category` — one of 5 fixed options
- `priority` — Low / Medium / High
- `confidence` — 0.0 to 1.0
- `reasoning` — one sentence explaining the classification

### Full Prompt

```
You are a customer support classifier for ArcVault, a B2B software platform.

Classify the incoming support message into exactly one of these categories:
- Bug Report
- Feature Request
- Billing Issue
- Technical Question
- Incident/Outage

Assign a priority:
- Low: general question, enhancement request, no service impact
- Medium: user-affecting bug, billing discrepancy, configuration issue
- High: service outage, data loss, security issue, multiple users affected

Return a confidence score from 0.0 to 1.0 indicating how certain you are.

Respond with ONLY valid JSON — no markdown, no explanation:
{
  "category": "<category>",
  "priority": "<priority>",
  "confidence": <0.0-1.0>,
  "reasoning": "<one sentence why>"
}
```

### Design Decisions

**Enumerated categories with exact spelling.** The prompt lists all 5 valid categories verbatim. This reduces hallucination — the model knows exactly what strings are acceptable. `classifier.py` still validates and normalises the output (case-insensitive match), so the system degrades gracefully if the model returns "bug_report" or "Bug report".

**Priority descriptions are outcome-based, not label-based.** Instead of "Medium = medium severity", the prompt defines priority by business impact: "user-affecting bug", "service outage". This grounds the model in the same logic the routing rules use.

**Temperature = 0.0.** Classification is a deterministic task — given the same message, we want the same category every time. Zero temperature maximises reproducibility. (Enrichment has the same setting; we never want creativity from these prompts.)

**Confidence is self-reported.** Asking the LLM to rate its own confidence is imperfect — models are not well-calibrated. A classification with `confidence=0.95` is not necessarily more correct than one with `confidence=0.80`. The confidence score is used as a soft signal: below 0.70 → escalate to human review. It catches cases where the model is genuinely uncertain, but it doesn't replace human judgement.

**JSON-only output.** The instruction "Respond with ONLY valid JSON" is reinforced by the example structure at the end. Most models follow this. `llm_client.chat_json()` also strips markdown code fences as a fallback.

### Known Weaknesses

**Confidence is poorly calibrated.** GPT-4o-mini tends to return high confidence (0.85–0.95) even for ambiguous messages. The 0.70 threshold rarely triggers in practice. A better approach would be to use the LLM's token-level probability scores, or to ask the model to classify twice with different seeds and compare.

**"Incident/Outage" vs "Bug Report" overlap.** A single-user login failure looks like a Bug Report; a multi-user login failure looks like an Incident/Outage. The model sometimes misclassifies based on phrasing. The escalation keyword list ("multiple users affected") serves as a safety net.

**No few-shot examples.** Adding 1-2 examples per category would improve accuracy, especially for edge cases. The tradeoff is prompt length (cost) and maintenance burden when categories change.

### What I'd Improve With More Time

- Add 1-2 few-shot examples per category in the system prompt
- Use OpenAI structured outputs (`response_format`) to eliminate parse failures
- Log confidence distributions over time to detect calibration drift
- Experiment with asking the model to classify twice and flag disagreements

---

## Prompt 2: Enrichment (`prompts/enrich.txt`)

### What It Does

Takes the raw message plus the classification result and returns:
- `core_issue` — one sentence root-cause summary
- `entities` — list of identifiers, error codes, dollar amounts, dates, usernames, URLs
- `urgency_signal` — critical / high / normal / low
- `summary` — 2-3 sentences written for the receiving team

### Full Prompt

```
You are a support ticket enrichment assistant for ArcVault, a B2B software platform.

You will receive a customer support message and its classification. Extract structured
information to help the receiving team resolve it faster.

Extract:
- core_issue: one sentence describing the root problem
- entities: list of any identifiers, error codes, dollar amounts, dates, usernames, or URLs mentioned
- urgency_signal: one of "critical", "high", "normal", "low" — based on business impact language
- summary: 2-3 sentences written for the team who will handle this ticket

Respond with ONLY valid JSON — no markdown, no explanation:
{
  "core_issue": "<one sentence>",
  "entities": ["<entity1>", "<entity2>"],
  "urgency_signal": "<critical|high|normal|low>",
  "summary": "<2-3 sentences for the receiving team>"
}
```

### Design Decisions

**Classification is passed in as context.** The enrichment prompt receives both the raw message AND the classification output (`category / priority / confidence`). This lets the model calibrate its summary for the right audience — an Incident/Outage summary should sound different from a Feature Request summary.

**`urgency_signal` is separate from `priority`.** Priority comes from the classification step (Low/Medium/High). `urgency_signal` is the enrichment step's independent read of the urgency language in the message (critical/high/normal/low). Having both lets the routing logic use whichever is more conservative. In practice, they agree most of the time — when they disagree, the classification priority takes precedence.

**Entity extraction is untyped.** The prompt asks for "any identifiers, error codes, dollar amounts, dates, usernames, or URLs". The entities list is a flat array of strings. This is intentional for v1 — it works well enough and avoids complex nested schemas. A production system would type-annotate entities (`{"type": "error_code", "value": "403"}`) for downstream query-ability.

**Summary is audience-aware.** The instruction "written for the team who will handle this ticket" nudges the model toward practical, actionable language rather than just restating the message. In practice this works well for Billing and Engineering tickets.

### Known Weaknesses

**Entity extraction misses some formats.** The model reliably extracts obvious entities (invoice numbers, error codes, URLs). It sometimes misses implicit entities like relative dates ("last Tuesday") or partial version strings. `router.py` has its own regex dollar extractor that is more reliable than the LLM for billing amounts — this is intentional defence-in-depth.

**`urgency_signal` calibration.** Similar to confidence, the model's urgency assessments are not well-calibrated. "Critical" is rare; most messages come back "normal" or "high". The signal is useful as a soft hint to the receiving team but shouldn't be used for hard routing decisions.

**Summary length is inconsistent.** Sometimes the model writes one long sentence, sometimes three short ones. Adding "Exactly 2-3 sentences" or using `max_tokens` to bound the output would improve consistency.

### What I'd Improve With More Time

- Type-annotate entities: `[{"type": "error_code", "value": "403"}, ...]`
- Add audience-specific instructions per category (e.g., "For Billing tickets, always state the disputed amount and contract rate")
- Use `max_tokens` to bound summary length
- Add a `suggested_action` field: one-line recommendation for the receiving agent
