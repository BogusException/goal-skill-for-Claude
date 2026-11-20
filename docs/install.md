# Install

## Prerequisites

- [Claude Code](https://claude.ai/code) (any recent version)
- Python 3.9 or later (standard library only -- no extra packages required)

No API keys required.

## Automatic install

Clone or download this repository, then run the installer:

```bash
# Install for a single project (adds the skill to your current project only)
python install.py --scope project

# Install globally (available in every Claude Code project)
python install.py --scope global
```

The default scope is `project` when run from inside a project directory, `global` otherwise.

Restart Claude Code after installation so the Stop hook takes effect.

## What the installer does

**Project install** (`--scope project`):
- Copies `goal.py`, `goal-continue.sh`, `SKILL.md`, and `price_cache.json` into `<project>/.claude/skills/goal/`
- Adds the Stop hook entry to `<project>/.claude/settings.json`
- Adds the `Bash(...)` permission rule to `<project>/.claude/settings.json`

**Global install** (`--scope global`):
- Copies the same files into `~/.claude/skills/goal/`
- Patches `~/.claude/settings.json` with the hook and permission

## Manual install

If you prefer not to run the installer, follow these steps.

**1.** Copy `goal.py`, `goal-continue.sh`, and `SKILL.md` into `.claude/skills/goal/` inside your project (or `~/.claude/skills/goal/` for global).

**2.** Add the Stop hook to `.claude/settings.json` under `hooks.Stop[0].hooks`:

```json
{
  "type": "command",
  "command": "$CLAUDE_PROJECT_DIR/.claude/skills/goal/goal-continue.sh",
  "timeout": 30
}
```

For global install, replace `$CLAUDE_PROJECT_DIR/.claude/skills/goal/` with the absolute path to `~/.claude/skills/goal/`.

**3.** Add this to `permissions.allow` in the same file:

```json
"Bash(.venv/bin/python .claude/skills/goal/goal.py *)"
```

## Verifying the install

Restart Claude Code, open any project, and type:

```
/goal
```

You should see: `No goal is active.` with a list of available commands. If you see an error or nothing happens, check that the Stop hook entry and permission rule were added correctly.
