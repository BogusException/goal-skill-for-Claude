#!/usr/bin/env bash
# Install or verify this skill globally. Pass-through flags: --check --dry-run --force --json.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "install: project .venv interpreter missing at $PYTHON" >&2; exit 2; }
cd "$HERE"
exec "$PYTHON" "$HERE/install.py" "$@"
