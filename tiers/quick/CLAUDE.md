# Claude Code instructions

@AGENTS.md

## Claude-specific

1. **Hooks are active** (`.claude/settings.json`, scripts in `.ai/hooks/`). The session starts with
   `STATE.md` and the workspace status already in your context. A Stop hook returns you to work
   while there are uncommitted changes, so commit each logical unit as you go.
2. **Skills wrap the helpers:** `/checkpoint`, `/handoff`, and at higher tiers `/note`, `/source`,
   `/decide`, `/open-item`, `/adr`, `/experiment`, `/release`. Use them instead of hand-editing
   registers.
3. A hook blocking a write or a command is information, not an obstacle. Read the rule ID, fix the
   cause, and don't route around it with another tool.
4. Edits to `.ai/`, `.githooks/`, `.workrealm.json` and `.claude/settings.json` ask the user first:
   they are the guard-rails themselves.
5. If a hook message and the user's instruction conflict, **the user has the last word.**
