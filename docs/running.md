# Running

## Quick start

Type `/goal <objective>` in Claude Code. Claude starts working immediately.

```
/goal make all tests pass and push to main
```

The goal persists until Claude completes it, you pause it, or a limit is reached. You can close Claude Code and come back -- the goal resumes on your next message.

## Common tasks

| Task | Command |
|------|---------|
| Check goal status | `/goal` |
| Pause the loop | `/goal pause` |
| Resume after pause | `/goal resume` |
| Replace the objective | `/goal edit <new objective>` |
| Delete the goal | `/goal clear` |
| View turn-by-turn log | `/goal log` |
| View past goals | `/goal history` |
| Check token prices | `/goal prices` |
| Refresh price cache | `/goal prices --refresh` |
| Run tests | `source .venv/bin/activate && python3 -m unittest tests/test_goal.py -v` |
| Cut a release | `./release.sh` |
| Install the skill | `python install.py --scope project` or `--scope global` |

## Environment modes

There are no environment modes. The skill behaves the same way in all contexts. Configuration is per-project via `.claude/goal-config.json` -- see [customizing.md](customizing.md) for the available keys.
