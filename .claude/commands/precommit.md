Run the full pre-commit checklist for ArcVault. Execute ALL of the following checks in order and report pass/fail for each:

1. **Tests** — run: `python -m pytest tests/ -v`
   - All tests must pass. If any fail, show the failure and stop.

2. **Lint** — run: `python -m ruff check . --fix`
   - No lint errors allowed. Report any that ruff couldn't auto-fix.

3. **Secret scan** — run: `grep -r "sk-" --include="*.py" --include="*.txt" --include="*.md" --include="*.json" . | grep -v ".env.example" | grep -v "CLAUDE.md" | grep -v "docs/" | grep -v ".claude/"`
   - If ANY matches found, STOP. Do not commit. Remove the secret first.

4. **Env check** — run: `git status`
   - Confirm `.env` is NOT in the staged files. If it is, unstage it immediately.

5. **Summary** — report ✅ or ❌ for each check. Only proceed with `git commit` if all 4 are ✅.
