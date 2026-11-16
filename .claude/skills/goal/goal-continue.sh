#!/usr/bin/env bash
# Stop hook: keeps an active /goal running until it completes, pauses, or hits a limit.
set -euo pipefail
PROJ="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
# No goal state directory means no goal was ever set. Skip the interpreter start.
[[ -d "$PROJ/.claude/goals" ]] || exit 0
PYTHON="$PROJ/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "goal-continue: project .venv interpreter missing." >&2; exit 1; }
exec "$PYTHON" "$PROJ/.claude/skills/goal/goal.py" stop-hook
