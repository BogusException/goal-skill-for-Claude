#!/usr/bin/env bash
# Cut a release: test -> CRC -> changelog -> commit -> push -> gh release create.
# Usage: ./release.sh [--dry-run]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

GOAL_PY=".claude/skills/goal/goal.py"
CHANGELOG="CHANGELOG.md"

# --- Read version from source ------------------------------------------------
VERSION="$(python3 -c "
import re, sys
text = open('$GOAL_PY').read()
m = re.search(r'^VERSION\s*=\s*[\"\\x27]([^\"\\x27]+)[\"\\x27]', text, re.MULTILINE)
sys.stdout.write(m.group(1) if m else '')
")"
[[ -n "$VERSION" ]] || { echo "release: VERSION not found in $GOAL_PY" >&2; exit 1; }
TAG="v$VERSION"
echo "version: $TAG"

# --- Check tag doesn't already exist -----------------------------------------
if git tag --list "$TAG" | grep -q .; then
    echo "release: tag $TAG already exists -- bump VERSION first" >&2
    exit 1
fi

# --- Run tests ----------------------------------------------------------------
echo "running tests..."
source .venv/bin/activate
python3 -m unittest tests/test_goal.py -v 2>&1 | tail -4
echo ""

# --- Compute CRC32 of goal.py ------------------------------------------------
CRC="$(python3 -c "
import binascii, pathlib
data = pathlib.Path('$GOAL_PY').read_bytes()
print(f'{binascii.crc32(data) & 0xFFFFFFFF:08X}')
")"
echo "CRC32(goal.py): $CRC"

# --- Stamp CRC into changelog if not already there ---------------------------
# Pattern: ## [1.3.2] - DATE  (with or without existing CRC suffix)
HEADER_PATTERN="^## \[${VERSION}\]"
if ! grep -q "$HEADER_PATTERN" "$CHANGELOG"; then
    echo "release: no changelog entry for $VERSION -- add one first" >&2
    exit 1
fi

# Replace the header line with one that includes the CRC (idempotent)
NEW_HEADER="## [${VERSION}] - $(grep "$HEADER_PATTERN" "$CHANGELOG" | sed 's/.*\] - //' | cut -d' ' -f1) — CRC32(goal.py) \`${CRC}\`"
# Strip any existing CRC suffix first, then add the canonical one
sed -i "s|${HEADER_PATTERN}.*|${NEW_HEADER}|" "$CHANGELOG"
echo "changelog header: $NEW_HEADER"

# --- Commit if dirty ---------------------------------------------------------
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo ""
    echo "committing pending changes..."
    if $DRY_RUN; then
        echo "  [dry-run] would commit: $(git diff --name-only; git diff --cached --name-only)"
    else
        git add -u
        git commit -m "Release $TAG"
    fi
fi

# --- Extract release notes from changelog ------------------------------------
NOTES="$(python3 -c "
import re, sys
text = open('$CHANGELOG').read()
# Grab everything between this version's header and the next ## header
m = re.search(r'(## \[${VERSION}\][^\n]*\n)(.*?)(?=\n## \[|\Z)', text, re.DOTALL)
sys.stdout.write(m.group(2).strip() if m else '')
")"
[[ -n "$NOTES" ]] || { echo "release: could not extract notes for $VERSION" >&2; exit 1; }

# Derive a one-line title: prefer first ### heading, fall back to first non-blank line
TITLE_BODY="$(echo "$NOTES" | grep -m1 '^### ' | sed 's/^### //')"
[[ -z "$TITLE_BODY" ]] && TITLE_BODY="$(echo "$NOTES" | grep -m1 '.' | sed 's/^[#* ]*//')"
RELEASE_TITLE="$TAG -- $TITLE_BODY"

# --- Push to remotes ---------------------------------------------------------
echo ""
echo "pushing to origin..."
$DRY_RUN || git push origin main

if git remote | grep -q '^github$'; then
    echo "pushing to github..."
    $DRY_RUN || git push github main
fi

# --- Create GitHub release ---------------------------------------------------
echo ""
echo "creating GitHub release $TAG..."
if $DRY_RUN; then
    echo "  [dry-run] title: $RELEASE_TITLE"
    echo "  [dry-run] notes preview:"
    echo "$NOTES" | head -8
else
    REPO="$(git remote get-url github 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||')"
    gh release create "$TAG" \
        --repo "$REPO" \
        --title "$RELEASE_TITLE" \
        --notes "$NOTES"
fi

echo ""
echo "done: $TAG released."
