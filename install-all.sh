#!/usr/bin/env bash
# Install or verify every skill by running each skill folder's own install.sh.
# Pass-through flags: --check --dry-run --force.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "install-all: project .venv interpreter missing at $PYTHON" >&2; exit 2; }
exec "$PYTHON" "$ROOT/install_all.py" "$@"
