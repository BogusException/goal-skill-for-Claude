# Todo

## In Progress

- [ ] Register the Stop hook and permission rule in `.claude/settings.json` (blocked by protect-files hook, needs a manual step). See `docs/goal.md` §5.
- [ ] First live run of `/goal` with the hook registered (set a small goal, confirm it continues, pauses, completes).

## Backlog

Improvements after the 1:1 replication. Ordered by value.

- [ ] **1. Realtime goal dashboard (CC canvas / Artifact).** Publish one private Artifact per goal and refresh it from the Stop hook after each turn. Data already collected in `.claude/goals/<session>.json`:
  - Status, objective, turn count, active time (pauses excluded), pause reason.
  - Token counters: input, output, cache creation, cache read, plus the per-model split (`by_model`).
  - Total cost in dollars: tokens x model price table. Show cost so far, burn rate ($/hour, $/turn), and projected cost at the current rate.
  - Budget bar in tokens and in dollars. Add `goals.max_goal_cost_usd` as a second limit next to the token budget.
  - Turn timeline: one row per continuation with duration, tokens, cost, last tool used, files touched.
  - Git progress: commits and changed files since goal start (`git diff --stat` against the start commit, recorded at `/goal` time).
  - Test status: last result of the verification command, if the goal names one.
  - Stall indicator: how many identical turns in a row.
  - Controls: pause, resume, raise budget. Use the artifact runtime capabilities (live data, state) if the account has them. Otherwise start with a read-only page the hook rewrites.
- [ ] **2. Cost accounting.** Price table file with per-model rates (input, output, cache write 5m, cache write 1h, cache read). Include subagent transcripts, which the session transcript does not contain today. Show cost in `/goal` output and the status line.
- [ ] **3. Status line integration.** Wire `goal.py statusline` into the user status line script (`~/.claude/2026-07_statusline-command.sh`), so the progress row shows in every turn. Needs a global config edit, so ask first.
- [ ] **4. Goal history.** Keep finished goals in `.claude/goals/history.jsonl` with final cost, duration, outcome. Add `/goal history` and a cost-per-goal average.
- [ ] **5. Independent completion check.** Today the agent judges its own completion, same as ChatGPT. Add an optional verifier: a fresh subagent that reads the objective and the evidence and tries to refute it before `complete` is accepted.
- [ ] **6. Prevent sleep while running.** Wrap the loop in `systemd-inhibit` or a caffeine-style inhibitor on Linux. Equivalent of the ChatGPT "Prevent sleep while running" setting.
- [ ] **7. Notifications.** Use the existing `notify.sh` hook to send a push message when a goal completes, pauses, or hits a limit.
- [ ] **8. Objective from file.** `/goal @path/to/spec.md` for objectives over 4,000 characters.
- [ ] **9. Worktree isolation.** Offer to start each goal in its own git worktree so parallel goals do not edit the same files.
- [ ] **10. Cross-session resume.** Test and document goal behavior after `claude --resume`.
- [ ] **11. Port to global skills.** Copy the skill to `~/.claude/skills/goal` and make the project path logic work from any repo.

## Done

- [x] Initial scaffold
- [x] `/goal` skill, state script, Stop-hook loop, config keys, 23 unit tests (2026-11-16)
- [x] CLAUDE.md Goal mode section, `docs/goal.md`
