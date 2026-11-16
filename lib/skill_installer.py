#!/usr/bin/env python3
"""Install or verify one Claude Code skill in the global skills directory.

A skill is a folder that holds a ``SKILL.md`` whose frontmatter has a
``version: MAJOR.MINOR.PATCH`` field. This module compares the source copy in
this repository with the copy in ``~/.claude/skills`` and installs, updates, or
reports, using the version, a content hash, and file timestamps.

Sections
    1. Constants
    2. Data types
    3. Version and frontmatter parsing
    4. Hashing and timestamps
    5. Planning (decide the action)
    6. Applying (backup and copy)
    7. Reporting
    8. Command line interface
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

SKILL_FILE_NAME = "SKILL.md"
META_FILE_NAME = ".install-meta.json"
BACKUP_DIR_NAME = "backups"
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Installer tooling stays in the repository. It is not copied to the target.
EXCLUDED_NAMES = frozenset({"install.sh", "install.py", META_FILE_NAME, "__pycache__", ".git"})
EXCLUDED_SUFFIXES = (".pyc", ".pyo")

ACTION_INSTALL = "install"
ACTION_UPDATE = "update"
ACTION_CURRENT = "current"
ACTION_DRIFT = "drift"
ACTION_NEWER_INSTALLED = "newer-installed"
ACTIONS_THAT_WRITE = (ACTION_INSTALL, ACTION_UPDATE)

EXIT_OK = 0
EXIT_NOT_CURRENT = 1
EXIT_ERROR = 2


# ---------------------------------------------------------------------------
# 2. Data types
# ---------------------------------------------------------------------------


class InstallerError(Exception):
    """Raised for a problem the user must fix, such as a missing version."""


@dataclass
class Plan:
    """The decision for one skill, before any file changes."""

    name: str
    action: str
    reason: str
    source_version: str
    installed_version: Optional[str]
    source_hash: str
    source_modified: str
    installed_at: Optional[str]
    target: str


# ---------------------------------------------------------------------------
# 3. Version and frontmatter parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> dict[str, str]:
    """Return the ``key: value`` pairs of the leading frontmatter block.

    The parser handles flat scalar fields only. That is all a skill needs here,
    and it avoids a YAML dependency.
    """
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


def parse_version(text: str) -> tuple[int, int, int]:
    """Convert ``"1.2.3"`` to ``(1, 2, 3)``. Raise InstallerError otherwise."""
    match = VERSION_PATTERN.match(text.strip())
    if not match:
        raise InstallerError(f"Version {text!r} is not MAJOR.MINOR.PATCH.")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def read_skill_version(skill_dir: pathlib.Path) -> str:
    """Read the ``version`` field from a skill folder's SKILL.md."""
    skill_file = skill_dir / SKILL_FILE_NAME
    if not skill_file.is_file():
        raise InstallerError(f"{skill_file} does not exist.")
    version = parse_frontmatter(skill_file.read_text(encoding="utf-8")).get("version", "")
    if not version:
        raise InstallerError(f"{skill_file} has no 'version:' field in its frontmatter.")
    parse_version(version)
    return version


# ---------------------------------------------------------------------------
# 4. Hashing and timestamps
# ---------------------------------------------------------------------------


def is_excluded(path: pathlib.Path) -> bool:
    """True when a path is installer tooling or build output."""
    return path.name in EXCLUDED_NAMES or path.name.endswith(EXCLUDED_SUFFIXES)


def list_skill_files(root: pathlib.Path) -> list[pathlib.Path]:
    """List the files of a skill that are installed, in a stable order."""
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not any(is_excluded(pathlib.Path(part)) for part in relative.parts):
            files.append(path)
    return files


def hash_tree(root: pathlib.Path) -> str:
    """SHA-256 over the relative path and bytes of every installed file."""
    digest = hashlib.sha256()
    for path in list_skill_files(root):
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def newest_modified(root: pathlib.Path) -> str:
    """UTC ISO timestamp of the most recently changed installed file."""
    files = list_skill_files(root)
    if not files:
        return ""
    newest = max(path.stat().st_mtime for path in files)
    return dt.datetime.fromtimestamp(newest, dt.timezone.utc).isoformat(timespec="seconds")


def utc_now() -> str:
    """Current UTC time as an ISO string."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read_meta(target: pathlib.Path) -> dict[str, str]:
    """Read the install metadata written by a previous install, if any."""
    meta_file = target / META_FILE_NAME
    if not meta_file.is_file():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# 5. Planning (decide the action)
# ---------------------------------------------------------------------------


def find_skills_dir() -> pathlib.Path:
    """The global skills directory. CLAUDE_CONFIG_DIR overrides ``~/.claude``."""
    home = os.environ.get("CLAUDE_CONFIG_DIR")
    base = pathlib.Path(home) if home else pathlib.Path.home() / ".claude"
    return base / "skills"


def decide_action(source_version: str, installed_version: Optional[str], is_same_hash: bool) -> tuple[str, str]:
    """Return ``(action, reason)`` from the two versions and the content match."""
    if installed_version is None:
        return ACTION_INSTALL, "not installed"
    source = parse_version(source_version)
    try:
        installed = parse_version(installed_version)
    except InstallerError:
        return ACTION_UPDATE, f"installed version {installed_version!r} is not readable"
    if source > installed:
        return ACTION_UPDATE, f"{installed_version} -> {source_version}"
    if source < installed:
        return ACTION_NEWER_INSTALLED, f"installed {installed_version} is newer than source {source_version}"
    if is_same_hash:
        return ACTION_CURRENT, "version and content match"
    return ACTION_DRIFT, "same version, different content (bump the version or use --force)"


def build_plan(skill_dir: pathlib.Path, skills_dir: pathlib.Path) -> Plan:
    """Compare a source skill folder with its global copy."""
    name = skill_dir.name
    target = skills_dir / name
    source_version = read_skill_version(skill_dir)
    source_hash = hash_tree(skill_dir)
    installed_version: Optional[str] = None
    is_same_hash = False
    meta: dict[str, str] = {}
    if (target / SKILL_FILE_NAME).is_file():
        meta = read_meta(target)
        installed_version = (
            parse_frontmatter((target / SKILL_FILE_NAME).read_text(encoding="utf-8")).get("version") or "unversioned"
        )
        is_same_hash = hash_tree(target) == source_hash
    action, reason = decide_action(source_version, installed_version, is_same_hash)
    return Plan(
        name=name,
        action=action,
        reason=reason,
        source_version=source_version,
        installed_version=installed_version,
        source_hash=source_hash,
        source_modified=newest_modified(skill_dir),
        installed_at=meta.get("installed_at"),
        target=str(target),
    )


# ---------------------------------------------------------------------------
# 6. Applying (backup and copy)
# ---------------------------------------------------------------------------


def back_up_existing(target: pathlib.Path, skills_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Copy an existing install to ``skills/backups`` and verify the copy.

    Raises InstallerError when the copy cannot be verified, so the caller stops
    before it replaces the original.
    """
    if not target.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "000"
    backup = skills_dir / BACKUP_DIR_NAME / f"{target.name}.{stamp}.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.parent.chmod(0o700)
    shutil.copytree(target, backup, symlinks=True)
    if hash_tree(backup) != hash_tree(target):
        raise InstallerError(f"Backup of {target} did not verify. Nothing was changed.")
    return backup


def write_meta(target: pathlib.Path, plan: Plan, source: pathlib.Path) -> None:
    """Record what was installed, and when, next to the installed files."""
    meta = {
        "name": plan.name,
        "version": plan.source_version,
        "installed_at": utc_now(),
        "source_hash": plan.source_hash,
        "source_path": str(source),
        "source_modified": plan.source_modified,
    }
    (target / META_FILE_NAME).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def copy_skill(source: pathlib.Path, destination: pathlib.Path) -> None:
    """Copy the installable files of a skill, keeping file modes."""
    for path in list_skill_files(source):
        out = destination / path.relative_to(source)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)


def apply_plan(plan: Plan, skill_dir: pathlib.Path, skills_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Install or replace the global copy. Return the backup path, if any.

    The new copy is built in a temporary sibling folder and renamed into place,
    so a failed copy never leaves a half-installed skill.
    """
    target = pathlib.Path(plan.target)
    skills_dir.mkdir(parents=True, exist_ok=True)
    backup = back_up_existing(target, skills_dir)
    staging = pathlib.Path(tempfile.mkdtemp(prefix=f".{plan.name}-", dir=skills_dir))
    try:
        copy_skill(skill_dir, staging)
        write_meta(staging, plan, skill_dir)
        if hash_tree(staging) != plan.source_hash:
            raise InstallerError("Staged copy does not match the source. Nothing was changed.")
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return backup


# ---------------------------------------------------------------------------
# 7. Reporting
# ---------------------------------------------------------------------------


def format_line(plan: Plan, did_write: bool) -> str:
    """One readable status line for a skill."""
    verb = {ACTION_INSTALL: "installed", ACTION_UPDATE: "updated"}.get(plan.action, plan.action)
    shown = verb if did_write else plan.action
    installed = plan.installed_version or "-"
    when = plan.installed_at or "-"
    return (
        f"{plan.name}: {shown} | source {plan.source_version} (modified {plan.source_modified}) "
        f"| installed {installed} (at {when}) | {plan.reason}"
    )


def is_current(plan: Plan) -> bool:
    """True when the global copy needs no change."""
    return plan.action == ACTION_CURRENT


# ---------------------------------------------------------------------------
# 8. Command line interface
# ---------------------------------------------------------------------------


def build_parser(description: str) -> argparse.ArgumentParser:
    """Build the argument parser shared by every skill installer."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--check", action="store_true", help="verify only; exit 1 if not current")
    parser.add_argument("--dry-run", action="store_true", help="show the planned action; change nothing")
    parser.add_argument("--force", action="store_true", help="overwrite a drifted or newer installed copy")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of a line")
    parser.add_argument("--target-dir", type=pathlib.Path, help="global skills directory (default ~/.claude/skills)")
    return parser


def run(skill_dir: pathlib.Path, argv: Optional[list[str]] = None) -> int:
    """Entry point for a skill's install.py. Return the process exit code."""
    args = build_parser(f"Install or verify the '{skill_dir.name}' skill globally.").parse_args(argv)
    skills_dir = args.target_dir or find_skills_dir()
    try:
        plan = build_plan(skill_dir, skills_dir)
        is_forced = args.force and plan.action in (ACTION_DRIFT, ACTION_NEWER_INSTALLED)
        should_write = (plan.action in ACTIONS_THAT_WRITE or is_forced) and not (args.check or args.dry_run)
        backup = apply_plan(plan, skill_dir, skills_dir) if should_write else None
    except InstallerError as error:
        print(f"{skill_dir.name}: error | {error}", file=sys.stderr)
        return EXIT_ERROR
    if should_write:
        # Re-read the installed copy for its timestamp, but keep the action that was taken.
        acted = plan
        plan = build_plan(skill_dir, skills_dir)
        plan.action, plan.reason = acted.action, acted.reason
    if args.json:
        print(json.dumps({**asdict(plan), "did_write": should_write, "backup": str(backup) if backup else None}))
    else:
        print(format_line(plan, should_write))
        if backup:
            print(f"  previous copy saved to {backup}")
    if args.check:
        return EXIT_OK if is_current(plan) else EXIT_NOT_CURRENT
    return EXIT_OK


if __name__ == "__main__":
    print("Run a skill's install.sh instead.", file=sys.stderr)
    sys.exit(EXIT_ERROR)
