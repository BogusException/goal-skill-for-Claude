# Customizing

## Configuration

Create `.claude/goal-config.json` in your project root to override defaults. All keys are optional.

```json
{
  "features": {
    "goals": true
  },
  "goals": {
    "max_goal_token_budget": 200000,
    "max_continuations": 100,
    "max_cost_usd": null
  }
}
```

| Key | Default | Effect |
|-----|---------|--------|
| `features.goals` | `true` | Set to `false` to disable goal mode entirely for this project. The Stop hook exits immediately and `/goal` commands return an error. |
| `goals.max_goal_token_budget` | `null` (no limit) | Token budget per goal. Counts input + output + cache-creation tokens. When the budget runs out, Claude gets one wrap-up turn, then the goal pauses. Also settable via the `CLAUDE_GOAL_MAX_TOKEN_BUDGET` environment variable. |
| `goals.max_continuations` | `100` | Maximum number of continuation turns before the goal auto-pauses. Raise this for very long tasks. |
| `goals.max_cost_usd` | `null` (no limit) | Dollar cost cap. Checked after each turn using the local price cache. When reached, the goal pauses with status `budget_limited`. |

## Extension points

**To add a new subcommand** (e.g. `/goal archive`):

1. Write a `run_archive(session)` function in `goal.py` following the same pattern as `run_log`, `run_history`, etc.
2. Add a `commands.add_parser("archive")` entry in `build_parser()`.
3. Add an `elif args.command == "archive"` branch in `main()`.
4. If the command should be reachable via the slash interface, add handling in `run_slash()`.

**To add a new price source:**

Add an entry to the `_PRICE_SOURCES` list in `goal.py`:

```python
{
    "name": "MySource",
    "url": "https://example.com/prices.json",
    "parse": _parse_mysource,   # function: raw dict -> {model_name: {input, output, cache_creation, cache_read}}
}
```

Sources are tried in order. The first one that returns valid data wins.

**To add a new requirement check type:**

Requirements currently run any shell command via `subprocess`. The `_run_requirement_check()` function in `goal.py` is the place to add alternative verification strategies (e.g., HTTP health checks, file existence tests) before falling back to the shell command.

## Environment variables

| Variable | Effect |
|----------|--------|
| `CLAUDE_GOAL_MAX_TOKEN_BUDGET` | Overrides `goals.max_goal_token_budget` from the config file |
| `CLAUDE_PROJECT_DIR` | Tells `goal.py` where the project root is. Claude Code sets this automatically. |
| `CLAUDE_CONFIG_DIR` | Tells `goal.py` where `~/.claude` lives. Defaults to `$HOME/.claude`. |
| `CLAUDE_SESSION_ID` | Current session identifier. Set by Claude Code and passed to `goal.py` via the skill invocation. |
