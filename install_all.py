#!/usr/bin/env python3
"""Install or verify every skill in ``.claude/skills`` by running each skill's own installer.

Each skill folder holds an ``install.sh``. This script runs that file from
inside the skill's folder, collects the JSON result, and prints one table.

Usage
    ./install-all.sh              install or update every skill that is out of date
    ./install-all.sh --check      verify only; exit 1 if any skill is not current
    ./install-all.sh --dry-run    show planned actions
    ./install-all.sh --force      overwrite drifted or newer installed copies

Sections
    1. Constants
    2. Discovery
    3. Running one skill
    4. Reporting
    5. Command line interface
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
INSTALLER_NAME = "install.sh"
PASS_THROUGH_FLAGS = ("check", "dry_run", "force")
TIMEOUT_SECONDS = 120

EXIT_OK = 0
EXIT_NOT_CURRENT = 1
EXIT_ERROR = 2


# ---------------------------------------------------------------------------
# 2. Discovery
# ---------------------------------------------------------------------------


def find_skill_dirs(skills_dir: pathlib.Path) -> list[pathlib.Path]:
    """List every skill folder, sorted by name. A skill has a SKILL.md."""
    return sorted(path.parent for path in skills_dir.glob("*/SKILL.md"))


# ---------------------------------------------------------------------------
# 3. Running one skill
# ---------------------------------------------------------------------------


def run_installer(skill_dir: pathlib.Path, flags: list[str], target_dir: Optional[pathlib.Path]) -> dict:
    """Run one skill's install.sh from its own folder and return a result row."""
    installer = skill_dir / INSTALLER_NAME
    if not installer.is_file():
        return {"name": skill_dir.name, "action": "no-installer", "reason": f"no {INSTALLER_NAME}", "exit_code": None}
    command = [str(installer), "--json", *flags]
    if target_dir:
        command += ["--target-dir", str(target_dir)]
    try:
        done = subprocess.run(
            command, cwd=skill_dir, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
        )
    except subprocess.TimeoutExpired:
        return {"name": skill_dir.name, "action": "error", "reason": "installer timed out", "exit_code": None}
    try:
        row = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        row = {"name": skill_dir.name, "action": "error", "reason": done.stderr.strip() or "no output"}
    row["exit_code"] = done.returncode
    return row


# ---------------------------------------------------------------------------
# 4. Reporting
# ---------------------------------------------------------------------------


def format_table(rows: list[dict]) -> str:
    """Render the results as an aligned text table."""
    header = ("skill", "source", "installed", "action", "reason")
    body = [
        (
            row["name"],
            row.get("source_version", "-"),
            row.get("installed_version") or "-",
            row["action"] + (" (done)" if row.get("did_write") else ""),
            row.get("reason", ""),
        )
        for row in rows
    ]
    widths = [max(len(str(line[i])) for line in [header, *body]) for i in range(len(header))]
    lines = ["  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(line)) for line in [header, *body]]
    return "\n".join(lines)


def decide_exit_code(rows: list[dict], is_check: bool) -> int:
    """Map the rows to an exit code."""
    if any(row["action"] == "error" or row.get("exit_code") == EXIT_ERROR for row in rows):
        return EXIT_ERROR
    if is_check and any(row["action"] != "current" for row in rows):
        return EXIT_NOT_CURRENT
    return EXIT_OK


# ---------------------------------------------------------------------------
# 5. Command line interface
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify only; exit 1 if any skill is not current")
    parser.add_argument("--dry-run", action="store_true", help="show planned actions; change nothing")
    parser.add_argument("--force", action="store_true", help="overwrite drifted or newer installed copies")
    parser.add_argument("--skills-dir", type=pathlib.Path, default=SKILLS_DIR, help="source skills folder")
    parser.add_argument("--target-dir", type=pathlib.Path, help="global skills directory (default ~/.claude/skills)")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run every skill's installer and print one table."""
    args = build_parser().parse_args(argv)
    flags = [f"--{name.replace('_', '-')}" for name in PASS_THROUGH_FLAGS if getattr(args, name)]
    skill_dirs = find_skill_dirs(args.skills_dir)
    if not skill_dirs:
        print(f"No skills found in {args.skills_dir}.", file=sys.stderr)
        return EXIT_ERROR
    rows = [run_installer(skill_dir, flags, args.target_dir) for skill_dir in skill_dirs]
    print(format_table(rows))
    return decide_exit_code(rows, args.check)


if __name__ == "__main__":
    sys.exit(main())
