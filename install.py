#!/usr/bin/env python3
"""Install or verify the 'goal' skill in the global skills directory.

Thin entry point. All logic lives in ``lib/skill_installer.py`` at the
repository root. Run it through ``install.sh`` so the project .venv is used.

Usage
    ./install.sh              install, or update when the source is newer
    ./install.sh --check      verify only; exit 1 when the global copy is not current
    ./install.sh --dry-run    show the planned action
    ./install.sh --force      overwrite a drifted or newer installed copy
"""

from __future__ import annotations

import pathlib
import sys

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

SKILL_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[2]


# ---------------------------------------------------------------------------
# 2. Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run the shared installer for this skill folder."""
    sys.path.insert(0, str(REPO_ROOT / "lib"))
    from skill_installer import run

    return run(SKILL_DIR)


if __name__ == "__main__":
    sys.exit(main())
