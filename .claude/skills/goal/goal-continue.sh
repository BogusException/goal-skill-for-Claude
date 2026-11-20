#!/usr/bin/env bash
# Stop hook: keeps an active /goal running until it completes, pauses, or hits a limit.
set -euo pipefail
SKILL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJ="${CLAUDE_PROJECT_DIR:-$(cd "$SKILL_DIR/../../.." && pwd)}"
export CLAUDE_PROJECT_DIR="$PROJ"
# No goal state directory means no goal was ever set. Skip the interpreter start.
[[ -d "$PROJ/.claude/goals" ]] || exit 0
PYTHON="$PROJ/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "goal-continue: project .venv interpreter missing." >&2; exit 1; }
exec "$PYTHON" "$SKILL_DIR/goal.py" stop-hook
