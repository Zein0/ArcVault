import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ──────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# ── Pipeline ──────────────────────────────────────────────────────────────────
_raw_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))
CONFIDENCE_THRESHOLD = _raw_threshold / 100.0 if _raw_threshold > 1.0 else _raw_threshold
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# ── Valid Values ──────────────────────────────────────────────────────────────
VALID_CATEGORIES = [
    "Bug Report",
    "Feature Request",
    "Billing Issue",
    "Technical Question",
    "Incident/Outage",
]

VALID_PRIORITIES = ["Low", "Medium", "High"]

# ── Queue Routing (deterministic — NOT LLM-driven) ────────────────────────────
CATEGORY_TO_QUEUE = {
    "Bug Report": "Engineering",
    "Feature Request": "Product",
    "Billing Issue": "Billing",
    "Technical Question": "IT/Security",
    "Incident/Outage": "Engineering",
}
FALLBACK_QUEUE = "General Support"

# ── Escalation ────────────────────────────────────────────────────────────────
ESCALATION_KEYWORDS = [
    "outage",
    "down for all users",
    "data loss",
    "critical",
    "security breach",
    "all users affected",
    "multiple users affected",
    "billing error",
]
BILLING_ESCALATION_THRESHOLD = 500.0

# ── Sample Inputs ─────────────────────────────────────────────────────────────
SAMPLE_INPUTS = [
    {
        "id": 1,
        "source": "Email",
        "message": (
            "Hi, I tried logging in this morning and keep getting a 403 error. "
            "My account is arcvault.io/user/jsmith. "
            "This started after your update last Tuesday."
        ),
    },
    {
        "id": 2,
        "source": "Web Form",
        "message": (
            "We'd love to see a bulk export feature for our audit logs. "
            "We're a compliance-heavy org and this would save us hours every month."
        ),
    },
    {
        "id": 3,
        "source": "Support Portal",
        "message": (
            "Invoice #8821 shows a charge of $1,240 but our contract rate is "
            "$980/month. Can someone look into this?"
        ),
    },
    {
        "id": 4,
        "source": "Email",
        "message": (
            "I'm not sure if this is the right place to ask, but is there a way "
            "to set up SSO with Okta? We're evaluating switching our auth provider."
        ),
    },
    {
        "id": 5,
        "source": "Web Form",
        "message": (
            "Your dashboard stopped loading for us around 2pm EST. "
            "Checked our end — it's definitely on yours. Multiple users affected."
        ),
    },
]
