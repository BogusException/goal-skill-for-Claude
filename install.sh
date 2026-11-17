#!/usr/bin/env bash
# Install the /goal skill. Tries the project .venv first, falls back to system python3.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Development: use the project venv if present. Standalone clone: use system python3.
PYTHON=""
for candidate in "$HERE/../../../.venv/bin/python" "$HERE/../../.venv/bin/python"; do
    [[ -x "$candidate" ]] && { PYTHON="$candidate"; break; }
done
if [[ -z "$PYTHON" ]]; then
    PYTHON="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
fi
[[ -n "$PYTHON" ]] || { echo "install: no python interpreter found" >&2; exit 2; }
exec "$PYTHON" "$HERE/install.py" "$@"
