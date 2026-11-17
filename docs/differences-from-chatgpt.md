# Differences from ChatGPT Goal mode

This skill replicates ChatGPT's Goal mode as closely as Claude Code's architecture permits, but there are real gaps. This document lists each one, explains why it exists, and says whether a workaround is available. Read this before assuming behavior is identical.

---

## Activation

**ChatGPT:** Typing `/goal <objective>` starts it. Depending on the client version, natural-language phrases like "work on this until it's done" may also trigger it automatically.

**This skill:** Only starts when you explicitly type `/goal <objective>`. Natural-language phrases do nothing.

**Why:** Claude Code skills have an `invocation` flag that lets the model activate a skill based on context matching. That flag is intentionally disabled here (`disable-model-invocation: true` in `SKILL.md`). The reason: this skill starts an autonomous loop using a Stop hook. If the model misread context and activated it on a task you didn't intend to hand off, the loop would run unsupervised. The cost of a false activation is higher than the cost of requiring an explicit `/goal`. If you want natural-language activation, remove `disable-model-invocation: true` from `SKILL.md` -- but understand the tradeoff.

---

## Continuation visibility

**ChatGPT:** The loop is smooth. You see Claude producing output turn after turn. The mechanism driving the loop is hidden from the transcript.

**This skill:** Each continuation is injected by the Stop hook as a new turn. If you open the transcript or watch Claude Code's input stream, you can see the hook's continuation prompt. This is not a bug -- it's a consequence of using Claude Code's public hook API, which injects prompts through the normal message pathway.

**Why:** Claude Code's Stop hook mechanism is the only way to inject text between turns without user input. It goes through the same channel as a user message. There is no background signal path.

**Practical effect:** The transcript is longer and the boundary between turns is explicit. Some people find this reassuring (you can audit exactly what's driving the loop). Others find it noisy.

---

## Stopping / Esc behavior

**ChatGPT:** Pressing the Stop button halts goal mode immediately.

**This skill:** Pressing Esc in Claude Code interrupts the current turn, but Esc does **not** run Stop hooks. The goal state file still records the goal as active. When you send the next message, the loop resumes.

**Why:** This is a Claude Code architectural constraint. The Stop hook only fires after a turn completes normally. An Esc-interrupted turn doesn't fire it.

**Workaround:** To actually pause the goal, type `/goal pause`. To delete it, type `/goal clear`. Don't rely on Esc to stop the loop.

---

## Progress indicator

**ChatGPT:** While a goal is active, a row above the composer shows the current objective and progress.

**This skill:** No passive UI indicator. The terminal prompt looks the same whether a goal is running or not.

**Why:** Claude Code does not expose an API for injecting UI elements into the composer area.

**Workaround:** Type `/goal` at any time to see the current status. If your terminal supports a status line script, `goal.py statusline` outputs a compact one-liner you can embed in a shell prompt or tmux status bar.

---

## Goal scope and persistence

**ChatGPT:** Goal mode is scoped to the current chat session. Close the chat, lose the goal.

**This skill:** The goal persists in `.claude/goals/<session_id>.json`. It survives Claude Code restarts. If you close Claude Code mid-goal and reopen it in the same project, the loop resumes on the next turn.

**Why:** State-on-disk is how Claude Code's hook system maintains context between process restarts. This is an enhancement over ChatGPT behavior, not a limitation. The tradeoff is that you must explicitly clear completed goals with `/goal clear`.

---

## Cost tracking

**ChatGPT:** Goal mode does not report per-goal token usage or estimated cost.

**This skill:** `/goal` reports cumulative tokens by model and estimated cost from a local price cache. The cache is sourced from LiteLLM's model pricing index and refreshed manually with `goal.py prices --refresh`.

**Why:** This is an addition, not a replication. Claude Code makes token usage accessible via the session transcript, so it was possible to add. It was not in the original ChatGPT spec.

---

## Safety limits

**ChatGPT:** Limits exist but are not publicly documented.

**This skill:** Explicit, configurable, documented limits:
- 100 continuations per goal (configurable: `goals.max_continuations`)
- Token budget (configurable: `goals.max_goal_token_budget`, default 200,000)
- Stall guard: 3 identical consecutive assistant turns trigger automatic pause

All three pause the goal rather than silently stopping it. Run `/goal resume` to continue past a limit if you have a reason to.

---

## Summary table

| Feature | ChatGPT | This skill |
|---|---|---|
| Explicit `/goal <text>` activation | yes | yes |
| Natural-language activation | sometimes | no (by design) |
| Continuation mechanism | server-side, hidden | Stop hook, visible in transcript |
| Esc stops the loop | yes | no -- use `/goal pause` |
| Progress indicator while running | yes | no -- use `/goal` to check |
| Goal survives session restart | no | yes |
| Per-goal cost tracking | no | yes |
| Documented safety limits | no | yes |
| Config keys (`goals.*`, `features.goals`) | yes | yes |
| Permissions not expanded | yes | yes |
