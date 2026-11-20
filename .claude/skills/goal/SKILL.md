---
name: goal
version: 1.4.0
description: Set a persistent goal and keep working across turns until it is verifiably done. Supports named requirements with automated verification. Replicates ChatGPT/Codex /goal. Use /goal {objective}, /goal (view), /goal pause, /goal resume, /goal clear, /goal edit {objective}, /goal log, /goal history, /goal prices, /goal verify.
argument-hint: "[objective | pause | resume | clear | edit {objective} | log | history | prices [--refresh] [--all] | verify | add-requirement]"
disable-model-invocation: true
allowed-tools: Bash(.venv/bin/python .claude/skills/goal/goal.py *)
---

# /goal

## Step 1: run the state script

```bash
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/goal/goal.py" \
    --session "${CLAUDE_SESSION_ID}" slash <<'GOAL_ARGS_EOF'
$ARGUMENTS
GOAL_ARGS_EOF
```

## Step 2: act on the output

The script prints a line that starts with `ACTION:`.

- `ACTION: work`: the goal is now active. Start working on the objective immediately, using the rules printed after the `ACTION: work` line. The objective is both your first prompt and the completion criteria. Do not ask the user to confirm.
- `ACTION: report`: show the output above the `ACTION:` line to the user as it is. Do not start any work.
- The output starts with `Goal error:`: show the error to the user and stop.

## How Goal mode works

A Stop hook (`.claude/skills/goal/goal-continue.sh`) restarts you after each turn while the goal is active. The goal ends only in one of these ways:

1. You run `complete` after you audit every requirement against real evidence.
2. You run `pause --reason` because you need a decision or are blocked.
3. The user runs `/goal pause` or `/goal clear`.
4. A limit is reached (token budget, 100 continuations, or 3 identical turns in a row).

While a goal is active, do not end a turn with a question. Pause first, then ask.

## Requirements

When a goal has verifiable requirements, add them after setting the goal:

```bash
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/goal/goal.py" \
    --session "${CLAUDE_SESSION_ID}" add-requirement \
    --id req-1 \
    --description "all tests pass" \
    --check "python -m pytest -q"
```

Before completing, run verify:

```bash
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/goal/goal.py" \
    --session "${CLAUDE_SESSION_ID}" verify
```

`complete` will also run all checks automatically and block completion if any fail.
