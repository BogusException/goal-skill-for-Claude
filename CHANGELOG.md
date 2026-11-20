# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

---

## [1.4.0] - 2026-11-20 — CRC32(goal.py) `E9116B1C`

### Added: Requirements verification

- **`add-requirement` subcommand.** Register named requirements against a goal. Each has an id, a description, and an optional shell command to verify it. Requirements with no check command are marked manual.
- **`verify` subcommand.** Runs every auto-verifiable requirement's check command and prints a PASS/FAIL/MANUAL table. Saves results to the state file. Exits with ACTION: work when any requirement fails.
- **`complete` now enforces requirements.** When a goal has auto-verifiable requirements, `complete` runs them before marking the goal done. If any fail, completion is blocked with a list of which requirements failed and what the check command printed.
- **Requirements visible in `/goal` status.** When requirements are defined, the status view shows each one with its current pass/fail/manual/pending state.
- **Work prompt updated.** When requirements are attached to a goal, the continuation prompt includes an explicit rule to run `verify` before calling `complete`.

---

## [1.3.2] - 2026-11-20 — CRC32(goal.py) `243259E8`

### Fixed: Global installation path resolution and project-directory detection

- **`script_command()` used hardcoded project-relative paths.** The generated command contained `.venv/bin/python` and `.claude/skills/goal/goal.py`, which only work inside the project where the skill was developed. Replaced with `sys.executable` (the interpreter actually running the skill), `pathlib.Path(__file__).resolve()` (the script's real installed path), and `shlex.quote()` for both.
- **`goal-continue.sh` had a hardcoded absolute path to `goal.py`.** The global Stop hook embedded the installing user's home-directory path, breaking the hook for anyone else. Replaced with `SKILL_DIR` derived from `${BASH_SOURCE[0]}`, so the hook finds `goal.py` beside itself regardless of install location.
- **`project_dir()` fallback resolved to the skill's install directory.** `pathlib.Path(__file__).resolve().parents[3]` walked three levels up from the script file, which points to `~/.claude` for a global install rather than the active project. Replaced with `pathlib.Path.cwd().resolve()` so the fallback is always the working directory Claude Code launched from.
- **`install.py` regenerated the old broken `goal-continue.sh` on reinstall.** `_global_goal_continue()` was out of sync with the BASH_SOURCE fix and would overwrite it. Updated to generate the corrected script.
- **`install.py` `_global_skill_md()` performed a dead command-string substitution.** The source SKILL.md now uses a dynamic path (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}`), so the old text-replacement pattern would silently fail. Removed the command replacement; kept the `allowed-tools` replacement that injects the exact installed path.
- **SKILL.md invocation used a project-relative `python` and path.** Updated to `python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/goal/goal.py"` with `$ARGUMENTS` placed directly in the heredoc, eliminating the "copy the blockquote" instruction that required the AI to manually transfer the argument text.

---

## [1.3.0] - 2026-11-16

### Added

- **Activity log.** Each turn, Claude calls `goal.py log-entry --note "<one sentence>"` as the first action. `/goal log` shows the full per-turn history with timestamps. `/goal` (status view) shows the last 5 entries inline when a goal is active. This addresses the main frustration with long-running goals: no visibility into what actually happened across turns.
- **Goal history.** When you run `/goal clear`, the goal is appended to `~/.claude/goal-history.jsonl`. `/goal history` shows the last 20 cleared goals with status, turn count, creation time, and objective. Cross-session visibility into past work.
- **Dollar cost budget.** New config key `goals.max_cost_usd` in `.claude/goal-config.json`. When set, the stop hook checks estimated cost after each turn and triggers a budget-limited wrap-up if the threshold is reached. Complements the existing token budget for users who prefer to cap by dollars rather than tokens.
- **`/goal history` and `/goal log` slash commands.** Both are now routed through `run_slash`, so they work when typed as `/goal history` or `/goal log`.
- **`turns` field in goal state.** New array in the state JSON recording per-turn log entries. Old state files without this field are handled gracefully.

### Fixed

- **`/goal prices` via slash command was broken.** `prices` was not in `SLASH_BARE_COMMANDS` and not handled in `run_slash`, so `/goal prices` fell through to `run_set` and tried to create a goal with the objective "prices". Fixed by adding explicit handling in `run_slash`.

### Changed

- **`/goal prices` now filters to canonical model names by default.** The LiteLLM cache contains 415+ Claude model entries including provider-prefixed variants (`anthropic/claude-...`, `aihubmix/claude-...`, etc.). The default view now shows only models whose names start with `claude-` (25 entries). Pass `--all` or type `/goal prices --all` to see everything. This makes the common case readable without losing access to the full table.
- **`run_view` always shows the price source.** Previously the source name appeared only when bundled or stale. Now it appears as `Prices: LiteLLM (0d old)` for all cached sources.
- **`run_view` (no active goal) shows updated command list.** Added `History: /goal history` and updated the prices hint to show `[--refresh] [--all]`.
- **`build_work_prompt` updated.** Rule 1 is now "log this turn first": `log-entry --note "..."`. Original rules shift to 2-6. The log-entry call is described as a single Bash command to minimize overhead.

### Decisions recorded

- **Why append history on `clear` only?** `complete` leaves the state file on disk; the user may still want to inspect it before clearing. Recording history on `clear` captures everything cleanly -- completed, abandoned, and budget-limited goals all pass through it. No double-write problem.
- **Why is log-entry rule 1 in the work prompt?** Claude reliably executes the first rule. Putting logging at the end risks it being skipped if the turn ends unexpectedly. Recording intent ("what I will do") at the start is more robust than recording outcome at the end.
- **Why not auto-append history when a goal budget-limits or stalls?** Those states are recoverable -- the user can resume or edit the objective. The goal isn't "done" yet. Clearing is the definitive cleanup action and the right trigger for history.

---

## [1.2.0] - 2026-11-16

### Added

- **Multi-source pricing with offline fallback.** Price fetching now tries three sources in order: LiteLLM's model pricing JSON, then the OpenRouter API, then a bundled static table compiled at release time. The first source that returns valid data wins. The bundled table (`BUNDLED_PRICES`) guarantees cost tracking works even with no network access.
- **`source_name` in price cache.** The cache file now records which source provided the data (`LiteLLM`, `OpenRouter`, or `bundled`). `/goal prices` and `/goal prices --refresh` show the source name in the header line.
- **Bundled prices note.** When the bundled table is active (no network, no cached data), `/goal` status output shows a one-line note pointing to the refresh command instead of a silent stale-cache warning.

### Changed

- **`get_prices` return type.** Now returns a 3-tuple `(models, age_days, source_name)` instead of a 2-tuple. `source_name` is `"bundled"` when the static fallback is used, otherwise the network source name from the cache.
- **`run_prices` output.** "Fetching latest prices from LiteLLM..." changed to "Fetching latest prices..." because the source is not known until the fetch attempt completes. The result line reports the actual source used.
- **`get_prices` never returns `None` for models.** It previously returned `(None, None)` when no cache existed and `auto_fetch` was `False`. It now returns `(BUNDLED_PRICES, None, "bundled")` so cost estimation always has a price table.

### Decisions recorded

- **Why three sources?** LiteLLM and OpenRouter have different coverage and update cadences. Neither is guaranteed to be available. The bundled table is a last resort: it's accurate at release time and prevents a total cost-tracking blackout on air-gapped or offline machines. The order (LiteLLM first, OpenRouter second, bundled last) reflects decreasing freshness preference.
- **Why not cache the source name on every lookup?** `source_name` is only written when a network fetch succeeds and updates the cache. Reads from an existing cache return the `source_name` stored at fetch time. Bundled fallbacks never write to disk, so they don't pollute the cache state.

---

## [1.1.0] - 2026-11-16

### Added

- **Cost tracking.** `price_cache.json` is populated from LiteLLM's model pricing index on install. `estimate_cost()` computes spend from per-model token counts. Cost appears in `/goal` status output and in the completion report.
- **`prices` subcommand.** `goal.py prices` shows the cached price table. `goal.py prices --refresh` fetches the latest rates from LiteLLM before showing them. This is the correct command -- `--refresh-prices` as a top-level flag does not exist (see §Decisions).
- **30-day staleness warning.** When the price cache is older than 30 days, `/goal` prints the exact refresh command inline. The goal keeps running; nothing is blocked.
- **Standalone `install.py`.** Rewrote the installer to have no external dependencies -- it no longer imports from the monorepo's `lib/` directory. Supports `--scope project|global`, `--check`, `--dry-run`, `--force`. Auto-detects scope from cwd.
- **Global-scope install.** For `--scope global`, the installer generates a path-aware `goal-continue.sh` and `SKILL.md` with absolute paths to `~/.claude/skills/goal/goal.py`. The project's `.venv` is used for execution when available; falls back to system `python3`.
- **Price cache primed on install.** `install.py` calls `goal.py prices --refresh` during installation so the first `/goal` status check has pricing data.

### Changed

- **`run_view` (bare `/goal` with no active goal).** Previously printed nothing useful. Now prints: "No goal is active," plus the commands to start one, and a reminder of available subcommands. Users who run `/goal` before setting any goal now get a helpful prompt instead of silence.
- **`run_view` (terminal state).** When the goal status is `complete`, `budget_limited`, or `stall`, the output now appends: "This goal is finished. Run /goal clear to remove it, or /goal edit <new objective> to start another." Without this, users seeing "Status: complete" had no prompt for what to do next.
- **`run_view` (paused state).** Appends: "Run /goal resume to continue working."
- **`run_set` conflict error.** A second `/goal <text>` while a goal is active or paused now prints the current goal's full status block (objective, status, turns, tokens, cost) followed by specific options: `clear` to replace, `edit` to update the objective, and `resume` if the goal is paused. The previous error was a plain one-liner with no context.
- **`install.sh`.** No longer assumes a fixed monorepo venv location. Tries two candidate relative paths first (`../../../.venv` and `../../.venv`), then falls back to whatever `python3` is on `PATH`.

### Fixed

- `run_set` conflict message used an inline ternary expression inside an f-string that produced malformed output when the goal was paused. Rewritten using a list with conditional `append`.

### Decisions recorded

- **Why `prices --refresh` and not `--refresh-prices`?** The `prices` subcommand groups all price-related operations. `--refresh` is an argument to that subcommand. A top-level `--refresh-prices` flag would scatter price operations across the top-level argument namespace, which complicates the parser and doesn't match how other multi-verb CLIs work.
- **Why is `disable-model-invocation: true` still set?** See `docs/differences-from-chatgpt.md §Activation`.

---

## [1.0.0] - 2026-11-16

Initial release.

### Added

- `/goal <objective>` sets a persistent goal and starts work immediately.
- `/goal` with no arguments shows status, turn count, elapsed time, and token usage.
- `/goal pause`, `/goal resume`, `/goal edit <objective>`, `/goal clear`.
- Stop hook (`goal-continue.sh`) injects continuation prompts after each Claude turn. The hook exits immediately when no goal has ever been set, adding no overhead to unrelated projects.
- Goal state persisted in `.claude/goals/<session_id>.json` (git-ignored). Survives Claude Code restarts and Esc presses.
- Token budget enforcement: when the budget is exhausted, Claude gets one wrap-up turn, then the goal pauses with status `budget_limited`.
- Continuation limit: 100 turns by default, configurable via `goals.max_continuations` in `.claude/goal-config.json`.
- Stall guard: three consecutive identical assistant messages trigger an automatic pause with status `stall`.
- A second `/goal <text>` while a goal is active or paused is refused with an error. Use `/goal edit` to change the objective or `/goal clear` to delete it. Silent replacement could discard a multi-hour run.
- `goal-config.json` config keys: `features.goals`, `goals.max_goal_token_budget`, `goals.max_continuations`.
- `CLAUDE_GOAL_MAX_TOKEN_BUDGET` environment variable overrides the token budget.
- Installer (`install.py` + `install.sh`) for project-scope setup.
- 23 unit tests in `tests/test_goal.py` covering state management, token budgeting, continuation logic, and stall detection.
