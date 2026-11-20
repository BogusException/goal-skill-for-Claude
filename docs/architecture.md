# Architecture

## Overview

A single Python script (`goal.py`) implements a persistent goal mode for Claude Code. The user sets an objective once; a Stop hook drives Claude to keep working across turns until the work is done or Claude needs input. State survives restarts and context resets because it lives on disk, not in the conversation.

## Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `goal.py` | State machine, CLI, Stop hook logic, token tracking, price fetching | `.claude/skills/goal/goal.py` |
| `goal-continue.sh` | Stop hook wrapper. Reads the hook payload, calls `goal.py stop-hook`, exits immediately if no goal is set | `.claude/skills/goal/goal-continue.sh` |
| `SKILL.md` | Claude invocation instructions. Tells Claude how to run `goal.py` and act on its output | `.claude/skills/goal/SKILL.md` |
| `install.py` | Installer. Copies skill files and patches `.claude/settings.json` for project or global scope | `install.py` |
| `price_cache.json` | Local cache of per-model token prices, sourced from LiteLLM or OpenRouter | `.claude/skills/goal/price_cache.json` |
| `goal-config.json` | Per-project config (token budget, continuation limit, cost limit, feature flag) | `.claude/goal-config.json` (user-created) |

## Data flow

1. User types `/goal <objective>` in Claude Code.
2. SKILL.md instructs Claude to run `goal.py slash`, passing the argument text on stdin.
3. `goal.py` writes the goal state to `.claude/goals/<session_id>.json` and prints a work prompt.
4. Claude works on the objective for one turn.
5. When the turn ends, the Stop hook fires: `goal-continue.sh` runs `goal.py stop-hook` with the session payload (session ID, last assistant message, transcript path).
6. `goal.py stop-hook` reads the state, increments the turn counter, checks budget limits and stall detection, then prints `{"decision": "block", "reason": "<work prompt>"}` to stdout.
7. Claude Code receives the block decision and immediately starts another turn using the work prompt as the new input.
8. The loop continues until Claude calls `goal.py complete`, `goal.py pause`, or a limit is reached.

## External dependencies

| Dependency | Type | Purpose | Required? |
|------------|------|---------|-----------|
| LiteLLM model pricing JSON | Public HTTPS | Live per-model token prices | No -- falls back to bundled table |
| OpenRouter API | Public HTTPS | Secondary price source | No -- second fallback only |
| `gh` CLI | Local binary | GitHub release creation via `release.sh` | Only for cutting releases |
