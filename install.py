#!/usr/bin/env python3
"""Standalone installer for the /goal skill.

Usage
    python install.py [--scope project|global] [--check] [--dry-run] [--force]

Default scope is "project" when run from inside a directory that has a .claude/
folder, "global" otherwise.

Project install: copies files to <project>/.claude/skills/goal/ and patches
<project>/.claude/settings.json.

Global install: copies files to ~/.claude/skills/goal/, writes path-aware
goal-continue.sh and SKILL.md, and patches ~/.claude/settings.json. A globally
installed skill works in every Claude Code project without per-project setup.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

SKILL_NAME = "goal"
COPYABLE_FILES = ["goal.py", "goal-continue.sh", "SKILL.md"]

HOOK_COMMAND_PROJECT = "$CLAUDE_PROJECT_DIR/.claude/skills/goal/goal-continue.sh"
PERMISSION_PROJECT = "Bash(.venv/bin/python .claude/skills/goal/goal.py *)"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def claude_home() -> pathlib.Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return pathlib.Path(env) if env else pathlib.Path.home() / ".claude"


def _find_project_root() -> pathlib.Path:
    """Walk from cwd upward to find the first directory with .claude/."""
    cwd = pathlib.Path.cwd()
    for path in [cwd, *cwd.parents]:
        if (path / ".claude").is_dir():
            return path
    return cwd


def detect_scope() -> str:
    return "project" if (_find_project_root() / ".claude").is_dir() else "global"


def dest_dir(scope: str) -> pathlib.Path:
    if scope == "global":
        return claude_home() / "skills" / SKILL_NAME
    return _find_project_root() / ".claude" / "skills" / SKILL_NAME


def settings_path(scope: str) -> pathlib.Path:
    if scope == "global":
        return claude_home() / "settings.json"
    return _find_project_root() / ".claude" / "settings.json"


def source_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Generated files for global scope
# ---------------------------------------------------------------------------

def _global_goal_continue(skill_path: pathlib.Path) -> str:
    return f"""\
#!/usr/bin/env bash
# Stop hook for /goal skill (global install -- {skill_path}).
set -euo pipefail
SKILL_DIR="$(cd -- "$(dirname -- "${{BASH_SOURCE[0]}}")" && pwd)"
PROJ="${{CLAUDE_PROJECT_DIR:-$(pwd)}}"
export CLAUDE_PROJECT_DIR="$PROJ"
# No goals directory means no goal was ever set.
[[ -d "$PROJ/.claude/goals" ]] || exit 0
# Prefer the project venv; fall back to whatever python3 is on PATH.
PYTHON="$PROJ/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
    [[ -n "$PYTHON" ]] || {{ echo "goal-continue: no python interpreter found" >&2; exit 1; }}
fi
exec "$PYTHON" "$SKILL_DIR/goal.py" stop-hook
"""


def _global_skill_md(skill_path: pathlib.Path, src_skill_md: pathlib.Path) -> str:
    """Return SKILL.md with the allowed-tools permission patched for the exact global path."""
    text = src_skill_md.read_text(encoding="utf-8")
    old_allowed = "allowed-tools: Bash(.venv/bin/python .claude/skills/goal/goal.py *)"
    new_allowed = f"allowed-tools: Bash(python3 {skill_path}/goal.py *)"
    text = text.replace(old_allowed, new_allowed)
    return text


# ---------------------------------------------------------------------------
# settings.json helpers
# ---------------------------------------------------------------------------

def _load_settings(path: pathlib.Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_settings(path: pathlib.Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=".settings-", suffix=".json", delete=False
    ) as fh:
        json.dump(settings, fh, indent=2)
        fh.write("\n")
        tmp = fh.name
    os.replace(tmp, path)


def _hook_registered(settings: dict, command: str) -> bool:
    for group in settings.get("hooks", {}).get("Stop", []):
        for hook in group.get("hooks", []):
            if hook.get("command") == command:
                return True
    return False


def _permission_registered(settings: dict, permission: str) -> bool:
    return permission in settings.get("permissions", {}).get("allow", [])


def _patch_settings(settings: dict, hook_command: str, permission: str) -> None:
    settings.setdefault("hooks", {}).setdefault("Stop", [])
    stop_hooks = settings["hooks"]["Stop"]
    # Find or create the catch-all matcher group.
    target = next((g for g in stop_hooks if g.get("matcher", "") == ""), None)
    if target is None:
        target = {"matcher": "", "hooks": []}
        stop_hooks.append(target)
    target.setdefault("hooks", [])
    existing = {h.get("command") for h in target["hooks"]}
    if hook_command not in existing:
        target["hooks"].append({"type": "command", "command": hook_command, "timeout": 30})
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    if permission not in allow:
        allow.append(permission)


# ---------------------------------------------------------------------------
# File copy
# ---------------------------------------------------------------------------

def _copy_files(src: pathlib.Path, dst: pathlib.Path, force: bool, dry_run: bool) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for name in COPYABLE_FILES:
        src_file = src / name
        if not src_file.is_file():
            print(f"  warning: {name} not found in source, skipped")
            continue
        dst_file = dst / name
        if dst_file.is_file() and not force:
            if dst_file.stat().st_mtime >= src_file.stat().st_mtime:
                print(f"  skip {name} (already current)")
                continue
        verb = "would copy" if dry_run else "copy "
        print(f"  {verb} {name}")
        if not dry_run:
            shutil.copy2(src_file, dst_file)
            if name.endswith(".sh"):
                dst_file.chmod(0o755)


# ---------------------------------------------------------------------------
# Price fetch
# ---------------------------------------------------------------------------

def _fetch_prices(goal_py: pathlib.Path, dry_run: bool) -> None:
    if dry_run:
        print("  would fetch initial prices")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(goal_py), "prices", "--refresh"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            lines = [l for l in result.stdout.splitlines() if l.strip()]
            summary = lines[0] if lines else "ok"
            print(f"  {summary}")
        else:
            msg = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "unknown error"
            print(f"  price fetch failed (non-fatal): {msg}")
    except Exception as exc:
        print(f"  price fetch failed (non-fatal): {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--scope", choices=["project", "global"],
        help="installation scope (default: auto-detect)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="verify the install is current; exit 1 if not",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print what would happen without making changes",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite even when the installed copy is newer",
    )
    args = parser.parse_args(argv)

    scope = args.scope or detect_scope()
    src = source_dir()
    dst = dest_dir(scope)
    cfg = settings_path(scope)

    if scope == "global":
        hook_command = str(dst / "goal-continue.sh")
        permission = f"Bash(python3 {dst}/goal.py *)"
    else:
        hook_command = HOOK_COMMAND_PROJECT
        permission = PERMISSION_PROJECT

    print(f"scope:    {scope}")
    print(f"install:  {dst}")
    print(f"settings: {cfg}")
    print()

    if args.check:
        ok = True
        for name in COPYABLE_FILES:
            dst_file = dst / name
            src_file = src / name
            if not dst_file.is_file():
                print(f"  MISSING  {name}")
                ok = False
            elif src_file.is_file() and src_file.stat().st_mtime > dst_file.stat().st_mtime:
                print(f"  OUTDATED {name}")
                ok = False
            else:
                print(f"  ok       {name}")
        settings = _load_settings(cfg)
        if _hook_registered(settings, hook_command):
            print("  ok       Stop hook")
        else:
            print("  MISSING  Stop hook in settings.json")
            ok = False
        if _permission_registered(settings, permission):
            print("  ok       permission")
        else:
            print("  MISSING  permission in settings.json")
            ok = False
        return 0 if ok else 1

    # --- install ---
    print("Copying files...")
    _copy_files(src, dst, args.force, args.dry_run)

    if scope == "global":
        gc_path = dst / "goal-continue.sh"
        sm_path = dst / "SKILL.md"
        src_sm = src / "SKILL.md"
        if args.dry_run:
            print("  would write goal-continue.sh (global paths embedded)")
            if src_sm.is_file():
                print("  would write SKILL.md (global paths embedded)")
        else:
            gc_path.write_text(_global_goal_continue(dst), encoding="utf-8")
            gc_path.chmod(0o755)
            print("  wrote  goal-continue.sh (global paths embedded)")
            if src_sm.is_file():
                sm_path.write_text(_global_skill_md(dst, src_sm), encoding="utf-8")
                print("  wrote  SKILL.md (global paths embedded)")

    print(f"\nPatching {cfg}...")
    settings = _load_settings(cfg)
    if args.dry_run:
        hook_ok = _hook_registered(settings, hook_command)
        perm_ok = _permission_registered(settings, permission)
        print(f"  Stop hook:  {'already present' if hook_ok else 'would add'}")
        print(f"  permission: {'already present' if perm_ok else 'would add'}")
    else:
        _patch_settings(settings, hook_command, permission)
        _save_settings(cfg, settings)
        print("  settings.json updated")

    print("\nFetching initial prices...")
    _fetch_prices(dst / "goal.py", args.dry_run)

    if not args.dry_run:
        print("\nDone. Restart Claude Code for the Stop hook to take effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
