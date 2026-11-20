# Privacy and security

## Data handled

This skill stores no personal data. The only data written to disk is:

- **Goal state files** (`.claude/goals/<session_id>.json`): the goal objective text, turn notes written by Claude, token counts, and timestamps. These are created by the user and stored locally. They are git-ignored by default.
- **Goal history** (`~/.claude/goal-history.jsonl`): a log of cleared goals. Same content as above.
- **Price cache** (`price_cache.json`): a local copy of publicly available model pricing data fetched from LiteLLM or OpenRouter. No user data.

None of these files contain credentials, tokens, or identifiable user data beyond what the user typed as a goal objective.

## Secret management

No API keys are required to use this skill. Price fetching calls public, unauthenticated URLs. If network access is unavailable, the bundled price table is used as a fallback.

The `gh` CLI used by `release.sh` requires GitHub authentication, but that is a development tool, not a runtime dependency of the skill itself.

## File permissions

State files are created with restrictive permissions:

- `.claude/goals/` directory: `0o700` (owner read/write/execute only)
- Individual state files: `0o600` (owner read/write only)
- State writes use an atomic rename pattern (write to temp file, `os.replace()`) to prevent partial reads.

## Claude Code boundaries

The skill adds one permission rule to `.claude/settings.json`:

```
Bash(.venv/bin/python .claude/skills/goal/goal.py *)
```

This allows Claude to run `goal.py` with any arguments but nothing else. Claude cannot use this permission to run arbitrary Python or shell commands. The goal state files are stored under `.claude/goals/`, which is git-ignored and not accessible to external systems.

The Stop hook runs as the system user and has access to the filesystem. It only reads and writes the goal state file and the session transcript. It does not make network calls.
