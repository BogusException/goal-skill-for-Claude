# Installing skills globally

Each skill in `.claude/skills/<name>/` has its own `install.sh`. The root `install-all.sh` runs each of them from inside its folder.

## §1 Commands

| Command | Effect |
|---|---|
| `.claude/skills/<name>/install.sh` | Install the skill to `~/.claude/skills/<name>`, or update it when the source version is higher. |
| `... --check` | Verify only. Exit 0 if the global copy is current, 1 if not, 2 on error. |
| `... --dry-run` | Show the planned action. |
| `... --force` | Overwrite a drifted or newer installed copy. |
| `... --json` | Print one JSON object. |
| `... --target-dir DIR` | Use another skills directory. `CLAUDE_CONFIG_DIR` also moves the default. |
| `./install-all.sh [flags]` | Run every skill's `install.sh` and print one table. |

## §2 Version rules

The version comes from `version: MAJOR.MINOR.PATCH` in the `SKILL.md` frontmatter. Bump it when you change a skill.

| Source vs installed | Action |
|---|---|
| Not installed | `install` |
| Source version higher | `update` |
| Same version, same content hash | `current` |
| Same version, different content | `drift`. Not overwritten without `--force`. |
| Installed version higher | `newer-installed`. Not overwritten without `--force`. |

Content hash: SHA-256 over every installed file. `install.sh`, `install.py`, `__pycache__` and `.git` are excluded.

## §3 Timestamps and backups

Each install writes `.install-meta.json` in the installed folder: `version`, `installed_at` (UTC), `source_hash`, `source_path`, `source_modified` (newest file time in the source). The status line shows these.

Before an update or forced overwrite, the old copy is saved to `~/.claude/skills/backups/<name>.YYYYMMDD-HHMMSS-NNNNNNNNN.bak` and the copy is verified. If the verify fails, nothing changes. The new copy is built in a temporary folder and renamed into place.

## §4 Add a skill

1. Create `.claude/skills/<name>/SKILL.md` with a `version:` field.
2. Copy `install.sh` and `install.py` from an existing skill folder. Change nothing in them.
3. Run `./install-all.sh --check`.

## §5 Files

- `lib/skill_installer.py`: shared logic.
- `.claude/skills/<name>/install.py`, `install.sh`: per-skill entry points.
- `install_all.py`, `install-all.sh`: runs every skill's installer.
- `tests/test_skill_installer.py`: `.venv/bin/python -m unittest tests.test_skill_installer`.
