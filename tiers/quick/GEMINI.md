# Gemini CLI / Antigravity instructions

@./AGENTS.md

## Gemini-specific

1. **No harness hooks bind you here.** The Claude Code hooks in `.claude/` do not run for you;
   the git hooks in `.githooks/` are your safety net, and they refuse commits that break a
   machine-checked rule. Do not wait for them: commit each logical unit as you go with
   `python .ai/checkpoint.py "type: what changed"`.
2. A refused commit is information, not an obstacle: read the rule ID in the message, fix the
   cause, never bypass it with `--no-verify`.
3. If a check and the user's instruction conflict, **the user has the last word.**
