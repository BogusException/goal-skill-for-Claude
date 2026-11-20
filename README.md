# /goal for Claude Code

Gives Claude Code a persistent goal mode that works like ChatGPT's `/goal` command. Set an objective once, and Claude works across as many turns as it takes until the work is done or it needs a decision from you. No copy-pasting context between turns, no manually re-prompting.

## How it works

When you run `/goal <objective>`, the skill saves your goal to a local state file and activates a Stop hook (`goal-continue.sh`). After every turn Claude takes, the hook fires and asks Claude to continue working on the goal. Claude keeps going until it either completes the work (with verified evidence) or pauses to ask you something.

The goal persists across Claude Code restarts and survives Esc presses. The token and time counters only run while the goal is active, not while it is paused.

## Commands

| Command | What it does |
|---|---|
| `/goal <objective>` | Set the goal and start working immediately |
| `/goal` | Show current goal, status, turn count, time elapsed, tokens used, and estimated cost |
| `/goal pause` | Stop the loop. Claude won't continue until you resume. |
| `/goal resume` | Resume a paused goal |
| `/goal edit <new objective>` | Replace the objective. Resumes if paused. |
| `/goal clear` | Delete the goal entirely |

**Objectives** must be non-empty and under 4,000 characters. For longer specs, put them in a file and point the goal at the file path.

## Install

The installer handles both scopes. Clone or download this repo, then run:

```bash
# Install for a single project (registers hook and permission in .claude/settings.json)
python install.py --scope project

# Install globally (registers hook and permission in ~/.claude/settings.json)
python install.py --scope global
```

The default scope is `project` when run from inside a project directory, `global` otherwise. Restart Claude Code after either install so the new hook takes effect.

### What the installer does

**Project install** copies the skill files into `<project>/.claude/skills/goal/` and patches `<project>/.claude/settings.json`.

**Global install** copies the skill files into `~/.claude/skills/goal/` and patches `~/.claude/settings.json`. A globally-installed skill is available in every Claude Code project without any per-project setup.

### Manual install (project scope)

If you prefer not to run the installer:

**1.** Copy the skill files into your project's `.claude/skills/goal/` directory.

**2.** Register the Stop hook in `.claude/settings.json` under `hooks.Stop[0].hooks`:

```json
{
  "type": "command",
  "command": "$CLAUDE_PROJECT_DIR/.claude/skills/goal/goal-continue.sh",
  "timeout": 30
}
```

**3.** Add the permission to `permissions.allow` in the same file:

```json
"Bash(.venv/bin/python .claude/skills/goal/goal.py *)"
```

### Manual install (global scope)

Same as above, but use `~/.claude/settings.json` and replace `$CLAUDE_PROJECT_DIR/.claude/skills/goal/` with the absolute path to `~/.claude/skills/goal/` in both the hook command and the permission.

## Cost tracking

Running `/goal` after a session reports estimated cost alongside tokens and time. Costs are calculated from a local price cache (`price_cache.json`) sourced from the [LiteLLM model pricing index](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json), which covers all Claude models and is community-maintained.

**Refresh prices on demand:**

```bash
python goal.py prices --refresh
```

This fetches the latest pricing data and updates the local cache. Run it after Anthropic price changes or when you want to verify accuracy.

**Staleness warning:** When the cache is more than 30 days old, `/goal` prints a notice with the exact refresh command. The warning does not block the goal -- it appears inline in the status output so you can run the command directly from the Claude Code terminal.

The cache is stored beside `goal.py` and is git-ignored by default.

## Requirements verification

Goals can carry machine-checkable requirements. Claude adds them after setting the goal, and `complete` runs every automated check before marking the work done -- if any fail, completion is blocked until they pass.

```
/goal add all failing tests to the CI suite and make them green
```

Claude will add requirements like "all tests pass" with the actual check command, run them before completing, and show pass/fail status in `/goal` output. Manual requirements (no shell command) show as MANUAL and don't block completion automatically.

See [docs/goal.md §4](docs/goal.md) for the full details.

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

36 unit tests covering state management, token budgeting, continuation logic, stall detection, and requirements verification.

## Requirements

- Claude Code (any recent version)
- Python 3.9+ (standard library only -- no extra packages)
- A `.venv` virtualenv at the project root

## Background

This skill replicates the [ChatGPT Goal mode](https://learn.chatgpt.com) in Claude Code's hook system. The Stop hook is the key mechanism: it runs after every turn and returns a `decision: block` response that injects a continuation prompt, keeping Claude working without user input.

It is not an exact clone. Claude Code's architecture imposes real constraints, and a few behaviors are intentionally different. See [docs/differences-from-chatgpt.md](docs/differences-from-chatgpt.md) for the full breakdown.

---

Built with [Claude Code](https://claude.ai/code) (Anthropic).
