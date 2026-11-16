# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

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
