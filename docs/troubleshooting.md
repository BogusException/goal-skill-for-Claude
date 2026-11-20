# Troubleshooting

## Common errors

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `/goal` does nothing, no output | Skill not installed or Stop hook not registered | Run `python install.py` and restart Claude Code |
| `Goal error: session id is missing or invalid` | `CLAUDE_SESSION_ID` not set | This is set automatically by Claude Code. If you see it, the skill is being invoked outside of Claude Code. |
| `Goal error: a goal is already active` | A previous goal is still running | Run `/goal clear` to delete it, or `/goal edit <objective>` to replace the objective |
| `Goal error: completion blocked -- the following requirements failed` | One or more `add-requirement` checks returned a non-zero exit code | Fix the failing requirements and retry `/goal complete` |
| `Goal error: no goal is set for this session` | Trying to run a subcommand (pause, resume, etc.) without an active goal | Run `/goal <objective>` first |
| Goal loops forever without completing | Stall guard not triggering, or Claude is not calling `goal.py complete` | Check `/goal log` to see what Claude is doing each turn. Run `/goal pause` to interrupt, then inspect. |
| Price data shows as "bundled" | No network access to LiteLLM or OpenRouter | Run `goal.py prices --refresh` when network is available |
| State file permission denied | Running on a filesystem that ignores Unix permissions | Ensure `.claude/goals/` is on a local filesystem |
| Hook fires but goal does not continue | `goal-continue.sh` can't find `goal.py` | Check that the `SKILL_DIR` path in `goal-continue.sh` resolves correctly. Run `bash -x .claude/skills/goal/goal-continue.sh` to trace it. |

## Logs and state

- **Active goal state**: `.claude/goals/<session_id>.json` in your project root
- **Goal history**: `~/.claude/goal-history.jsonl`
- **Session transcript**: `~/.claude/projects/<project_hash>/<session_id>.jsonl` -- contains full turn output including token usage
- **Price cache**: `.claude/skills/goal/price_cache.json`

The state file is plain JSON. Reading it directly is a reliable way to debug unexpected behavior.

## Getting help

Open an issue at the project repository. Include:

- The full error message (not just the last line)
- The contents of the active state file (`.claude/goals/<session_id>.json`) with any sensitive objective text redacted
- Claude Code version (`claude --version`) and Python version (`python3 --version`)
- Whether you used project or global install

The `/goal log` output is also useful -- it shows what Claude intended to do on each turn.
