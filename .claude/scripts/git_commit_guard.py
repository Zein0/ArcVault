"""
PreToolUse hook — intercepts `git commit` bash calls and runs pre-commit checks.
Reads hook JSON from stdin. Outputs JSON with continue=false to block a failing commit.
"""
import json
import os
import re
import subprocess
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")

# Only act on git commit commands
if not re.search(r"\bgit\s+commit\b", cmd):
    sys.exit(0)

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(project_root)

failures = []

# 1. pytest
r1 = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
    capture_output=True,
    text=True,
)
if r1.returncode != 0:
    failures.append(f"PYTEST FAILED:\n{r1.stdout}{r1.stderr}")

# 2. ruff
r2 = subprocess.run(
    [sys.executable, "-m", "ruff", "check", "."],
    capture_output=True,
    text=True,
)
if r2.returncode != 0:
    failures.append(f"RUFF FAILED:\n{r2.stdout}")

# 3. secret scan (sk- keys)
r3 = subprocess.run(
    'grep -r "sk-" --include="*.py" --include="*.txt" --include="*.md" --include="*.json" .'
    ' | grep -v ".env.example" | grep -v "CLAUDE.md" | grep -v "docs/" | grep -v ".claude/"',
    shell=True,
    capture_output=True,
    text=True,
)
if r3.returncode == 0 and r3.stdout.strip():
    failures.append(f"SECRET LEAK DETECTED:\n{r3.stdout}")

if failures:
    print(json.dumps({
        "continue": False,
        "stopReason": "Pre-commit checks failed:\n\n" + "\n\n".join(failures),
    }))
