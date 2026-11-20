# /goal for Claude Code

Replicates ChatGPT and Codex Goal mode. Source of the spec: learn.chatgpt.com (slash commands, long-running work, follow goals), read 2026-11-16.

## §1 Commands

| Command | Effect |
|---|---|
| `/goal <objective>` | Set the goal and start work. The objective is the first prompt and the completion criteria. |
| `/goal` | Show the goal, status, turn count, active time, tokens, estimated cost, and requirements. |
| `/goal pause` | Stop the continuation loop. Time and token counters stop. |
| `/goal resume` | Continue a paused goal. |
| `/goal edit <objective>` | Replace the objective. A paused goal resumes. |
| `/goal clear` | Delete the goal and record it in history. |
| `/goal log` | Show the per-turn activity log (what Claude said it would do each turn). |
| `/goal history` | Show the last 20 cleared goals with status, turn count, and objective. |
| `/goal prices [--refresh] [--all]` | Show cached token prices. `--refresh` fetches from LiteLLM or OpenRouter. `--all` includes provider-prefixed variants. |

Rules from the spec: the objective is non-empty and at most 4,000 characters. For longer text, put it in a file and point the goal at the file. Use plan mode first when the outcome is unclear. A goal does not widen permissions.

## §2 Mapping from ChatGPT to Claude Code

| ChatGPT/Codex feature | Claude Code implementation |
|---|---|
| Goal persists across turns | Stop hook `.claude/skills/goal/goal-continue.sh` returns `decision: block` with a continuation prompt while the goal is active |
| Goal is per chat | State file `.claude/goals/<session_id>.json` (git-ignored) |
| Agent stops when confident | Agent runs `goal.py complete --evidence "..."` after it audits each requirement |
| Pauses when it needs a decision | Agent runs `goal.py pause --reason "..."`, then asks |
| Progress row above the composer | `/goal` status output, per-turn `systemMessage`, and `goal.py statusline` for a status line script |
| `goals.max_goal_token_budget` | Same key in `.claude/goal-config.json`. Env override: `CLAUDE_GOAL_MAX_TOKEN_BUDGET` |
| `features.goals` | Same key in `.claude/goal-config.json`. Default true |
| Objectives are untrusted context (Codex 0.169.0) | Objective is wrapped in `<goal_objective>` with a data-only instruction |
| Prevent sleep while running | Not replicated. Linux has no equivalent setting. |

## §3 Decisions where the docs are silent

1. A second `/goal <text>` while a goal is active or paused is refused. Use `clear` or `edit`. A silent replace could destroy a multi-hour run.
2. Budget counts input, output and cache-creation tokens from the session transcript. Cache reads are excluded. Time spent paused is excluded.
3. When the budget is used up, the hook sends one wrap-up prompt, then lets the session stop. Status becomes `budget_limited`.
4. Safety limits that ChatGPT does not document: `goals.max_continuations` (default 100) and a stall guard (3 identical final messages pause the goal). Both pause the goal. Run `/goal resume` to continue.
5. Pressing Esc does not run Stop hooks. The goal stays active. The next message you send resumes the loop.

## §4 Requirements verification

Goals can carry machine-checkable requirements. When present, `goal.py complete` runs every automated check before marking the goal done -- if any fail, completion is blocked.

Claude manages requirements internally using two script subcommands:

```bash
# Add a requirement with an automated check
goal.py add-requirement --session $SESSION \
    --id tests --description "all tests pass" --check "python -m pytest -q"

# Add a manual requirement (no shell check -- Claude verifies it by inspection)
goal.py add-requirement --session $SESSION \
    --id review --description "PR reviewed"

# Run all checks and print a PASS/FAIL/MANUAL table
goal.py verify --session $SESSION
```

Requirements appear in `/goal` status output with their current state (pending, PASS, FAIL, MANUAL). The state file stores the last result and output from each check command.

`complete` calls `verify` automatically for all auto-checkable requirements. A goal with failing requirements cannot be marked complete until the checks pass.

## §5 Files

- `.claude/skills/goal/SKILL.md`: the `/goal` skill (user-invoked only).
- `.claude/skills/goal/goal.py`: state, counters, Stop-hook logic. Python standard library only. Run it with the project `.venv`.
- `.claude/skills/goal/goal-continue.sh`: Stop hook wrapper. Exits at once when no goal was ever set.
- `.claude/goal-config.json`: config keys.
- `tests/test_goal.py`: run with `.venv/bin/python -m unittest tests.test_goal`.

## §6 Install

The skill needs one Stop hook entry and one permission rule in `.claude/settings.json`:

```json
{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/skills/goal/goal-continue.sh", "timeout": 30}
```

```json
"Bash(.venv/bin/python .claude/skills/goal/goal.py *)"
```

Add the first to `hooks.Stop[0].hooks`. Add the second to `permissions.allow`.
