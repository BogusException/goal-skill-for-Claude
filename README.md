# /goal for Claude Code

Gives Claude Code a persistent goal mode that works like ChatGPT's `/goal` command. Set an objective once, and Claude works across as many turns as it takes until the work is done or it needs a decision from you. No copy-pasting context between turns, no manually re-prompting.

## How it works

When you run `/goal <objective>`, the skill saves your goal to a local state file and activates a Stop hook (`goal-continue.sh`). After every turn Claude takes, the hook fires and asks Claude to continue working on the goal. Claude keeps going until it either completes the work (with verified evidence) or pauses to ask you something.

The goal persists across Claude Code restarts and survives Esc presses. The token and time counters only run while the goal is active, not while it is paused.

## Commands

| Command | What it does |
|---|---|
| `/goal <objective>` | Set the goal and start working immediately |
| `/goal` | Show current goal, status, turn count, time elapsed, tokens used |
| `/goal pause` | Stop the loop. Claude won't continue until you resume. |
| `/goal resume` | Resume a paused goal |
| `/goal edit <new objective>` | Replace the objective. Resumes if paused. |
| `/goal clear` | Delete the goal entirely |

**Objectives** must be non-empty and under 4,000 characters. For longer specs, put them in a file and point the goal at the file path.

## Install

**1. Copy the skill files** into your project's `.claude/skills/goal/` directory:

```
.claude/skills/goal/
  goal.py
  goal-continue.sh
  install.py
  install.sh
  SKILL.md
```

Or run the included installer (requires the project `.venv` to be active):

```bash
python install.py
```

**2. Register the Stop hook** in `.claude/settings.json` under `hooks.Stop[0].hooks`:

```json
{
  "type": "command",
  "command": "$CLAUDE_PROJECT_DIR/.claude/skills/goal/goal-continue.sh",
  "timeout": 30
}
```

**3. Add the permission** to `permissions.allow` in the same file:

```json
"Bash(.venv/bin/python .claude/skills/goal/goal.py *)"
```

**4. Restart Claude Code** so the new hook takes effect.

## Safety limits

- **100 continuations** per goal (configurable via `goals.max_continuations` in `.claude/goal-config.json`).
- **Token budget** checked each turn. When the budget runs out, Claude gets one wrap-up turn, then the goal pauses.
- **Stall guard**: if Claude produces three identical turns in a row, the goal pauses automatically.
- A second `/goal <text>` while a goal is active or paused is refused -- use `/goal edit` or `/goal clear` first. Silent replacement could discard hours of in-progress work.
- Goals do not expand Claude's permissions. If a step requires a tool or command Claude can't run, it pauses and tells you.

## Configuration

Optional. Create `.claude/goal-config.json` in your project root:

```json
{
  "features.goals": true,
  "goals.max_goal_token_budget": 200000,
  "goals.max_continuations": 100
}
```

The token budget can also be set via the environment variable `CLAUDE_GOAL_MAX_TOKEN_BUDGET`.

## Tests

```bash
.venv/bin/python -m unittest tests.test_goal
```

23 unit tests covering state management, token budgeting, continuation logic, and stall detection.

## Requirements

- Claude Code (any recent version)
- Python 3.9+ (standard library only -- no extra packages)
- A `.venv` virtualenv at the project root

## Background

This skill replicates the [ChatGPT Goal mode](https://learn.chatgpt.com) in Claude Code's hook system. The Stop hook is the key mechanism: it runs after every turn and returns a `decision: block` response that injects a continuation prompt, keeping Claude working without user input.
