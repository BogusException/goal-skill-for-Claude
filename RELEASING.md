# Releasing

Run through this checklist in order before every release. Nothing ships until every item passes.

---

## 1. Version

- [ ] `VERSION` in `.claude/skills/goal/goal.py` is bumped correctly:
  - Patch (x.y.**Z**): bug fixes only, no new user-visible behavior
  - Minor (x.**Y**.0): new commands, flags, or user-visible behavior
  - Major (**X**.0.0): breaking changes to the public interface
- [ ] `CHANGELOG.md` has a `## [VERSION] - DATE` section for this version with a clear description of what changed.
- [ ] `SKILL.md` frontmatter `version:` matches `goal.py VERSION`.

---

## 2. Code

- [ ] All tests pass: `source .venv/bin/activate && python3 -m unittest tests/test_goal.py -v`
- [ ] No syntax errors in `goal.py`: `python3 -m py_compile .claude/skills/goal/goal.py`
- [ ] `goal-continue.sh` is executable: `ls -l .claude/skills/goal/goal-continue.sh`

---

## 3. Documentation audit

Go through each file and verify it reflects the current code. This is the step that gets skipped and causes embarrassment.

### README.md
- [ ] Test count is current (search for the number and compare to `python3 -m unittest ... -v | tail -1`).
- [ ] Command table includes all slash commands that users type directly.
- [ ] Install instructions match what `install.py` actually does.
- [ ] No version numbers hardcoded that are now stale.

### docs/goal.md
- [ ] Command table matches the actual slash commands.
- [ ] File paths under §4 are accurate.
- [ ] Install snippet under §5 matches the current `settings.json` format.

### docs/install.md
- [ ] Prerequisites are accurate (Python version, etc.).
- [ ] Install steps work from a clean clone -- verify mentally.

### docs/running.md
- [ ] Common tasks table includes new commands added in this release.
- [ ] Test command in the table is correct.

### docs/customizing.md
- [ ] Config key table includes any new keys added in this release.
- [ ] Extension points section reflects current code structure.

### docs/architecture.md
- [ ] Component table is current -- no missing or renamed files.
- [ ] Data flow steps match the actual hook and script behavior.

### docs/troubleshooting.md
- [ ] Error table includes errors that surfaced during this development cycle.

### docs/differences-from-chatgpt.md
- [ ] Summary table at the bottom reflects current behavior.

### docs/doc-index.md
- [ ] No entries pointing to deleted files.
- [ ] New docs added in this cycle are indexed.

---

## 4. File hygiene

- [ ] No placeholder text anywhere: `grep -r "(example)\|TODO\|FIXME\|placeholder\|Replace this line" docs/ README.md`
- [ ] No empty stub files: check `src/`, `tasks/`, any scaffold directories.
- [ ] No leftover worktree directories: `ls .claude/worktrees/` should be empty or absent.
- [ ] `.gitignore` covers any new generated files from this release cycle.
- [ ] `.gitattributes` `export-ignore` list excludes dev-only files from release archives.

---

## 5. Release

Once all items above are checked:

```bash
./release.sh
```

This script: runs tests, stamps CRC32 into CHANGELOG, commits pending changes, pushes to all remotes, and creates the GitHub release.

**If `release.sh` fails:** fix the error, do not re-run until the root cause is resolved. Never push manually to work around a failing release script.

---

## 6. Post-release

- [ ] Sync global installation: `cp .claude/skills/goal/goal.py ~/.claude/skills/goal/goal.py && cp .claude/skills/goal/SKILL.md ~/.claude/skills/goal/SKILL.md`
- [ ] Verify the GitHub release page: title is correct, notes are readable, archive downloads and contains the right files.
- [ ] Run `prepare-release.py --check` to verify the zip would pass all checks (optional but useful after structural changes).

---

## Common mistakes

- **Stale test count in README.** Add a test, forget to update the number. Fix: search `README.md` for the old count before every release.
- **SKILL.md version out of sync.** `goal.py VERSION` is the source of truth. `SKILL.md` frontmatter must match it.
- **Template placeholders left in docs.** Run the grep in §4 before every release. One `(example)` in a shipped doc is a credibility problem.
- **Skipping the global sync.** The release is on GitHub but your own install is running old code. Run the `cp` commands in §6 every time.
