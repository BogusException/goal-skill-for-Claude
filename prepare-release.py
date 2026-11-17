#!/usr/bin/env python3
"""Package a skill for Claude Desktop upload.

Usage:
    python prepare-release.py            # run checks and build zip
    python prepare-release.py --check    # run checks only, no zip

The zip is written to releases/<name>-v<version>.zip inside the skill directory.
Run from anywhere -- the script always locates the skill by its own path.
"""

import py_compile
import re
import sys
import zipfile
from pathlib import Path

SCRIPT_VERSION = "1.0.0"
SKILL_ROOT = Path(__file__).parent

RELEASE_FILES = [
    "SKILL.md",
    "goal.py",
    "goal-continue.sh",
    "install.sh",
    "install.py",
    "CHANGELOG.md",
]
RELEASE_DIRS = ["docs"]


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    try:
        end = text.index("---", 3)
    except ValueError:
        return {}
    result = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip().strip('"')
    return result


def xml_tags_outside_fences(text: str) -> list:
    stripped = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.findall(r"<[a-zA-Z/][^>]*>", stripped)


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {status}  {label}{suffix}")
    return ok


def run_checks() -> tuple[bool, str, str]:
    passed = True
    name = version = ""

    skill_md = SKILL_ROOT / "SKILL.md"

    if not check("SKILL.md exists", skill_md.exists()):
        return False, "", ""

    fm = parse_frontmatter(skill_md.read_text())
    name = fm.get("name", "")
    version = fm.get("version", "")
    passed &= check("frontmatter: name", bool(name), name or "missing")
    passed &= check("frontmatter: version", bool(version), version or "missing")

    hits = xml_tags_outside_fences(skill_md.read_text())
    passed &= check(
        "SKILL.md: no XML-like tags",
        not hits,
        ", ".join(hits) if hits else "",
    )

    for f in RELEASE_FILES:
        passed &= check(f"file exists: {f}", (SKILL_ROOT / f).exists())

    goal_py = SKILL_ROOT / "goal.py"
    if goal_py.exists():
        try:
            py_compile.compile(str(goal_py), doraise=True)
            passed &= check("goal.py: syntax OK", True)
        except py_compile.PyCompileError as e:
            passed &= check("goal.py: syntax OK", False, str(e))

    cont = SKILL_ROOT / "goal-continue.sh"
    if cont.exists():
        passed &= check(
            "goal-continue.sh: executable",
            bool(cont.stat().st_mode & 0o111),
        )

    return passed, name, version


def build_zip(name: str, version: str) -> Path:
    releases_dir = SKILL_ROOT / "releases"
    releases_dir.mkdir(exist_ok=True)
    zip_path = releases_dir / f"{name}-v{version}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in RELEASE_FILES:
            src = SKILL_ROOT / f
            if src.exists():
                zf.write(src, f)

        for d in RELEASE_DIRS:
            src_dir = SKILL_ROOT / d
            if src_dir.is_dir():
                for item in sorted(src_dir.rglob("*")):
                    if item.is_file():
                        zf.write(item, str(item.relative_to(SKILL_ROOT)))

    with zipfile.ZipFile(zip_path) as zf:
        if "SKILL.md" not in zf.namelist():
            zip_path.unlink()
            print("  FAIL  SKILL.md not at zip root -- zip deleted")
            sys.exit(1)

    return zip_path


def main():
    check_only = "--check" in sys.argv

    print(f"prepare-release  v{SCRIPT_VERSION}")
    print(f"skill root: {SKILL_ROOT.resolve()}")
    print()
    print("Pre-release checks:")

    passed, name, version = run_checks()

    if not passed:
        print()
        print("Release aborted -- fix the errors above and try again.")
        sys.exit(1)

    if check_only:
        print()
        print("All checks passed. (--check mode, no zip created)")
        sys.exit(0)

    print()
    print(f"Building {name}-v{version}.zip...")
    zip_path = build_zip(name, version)

    print()
    print(f"Release ready:")
    print(f"  {zip_path.resolve()}")


if __name__ == "__main__":
    main()
