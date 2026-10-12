# Claude Code instructions

@AGENTS.md

## Claude-specific

1. **Hooks are active** (`.claude/settings.json`, scripts in `.ai/hooks/`). A Stop hook returns
   you to work while there are uncommitted changes — commit each logical unit as you go rather
   than waiting for it to force you.
2. A hook blocking a write is information, not an obstacle: read the message, don't route around
   it with a shell command.
3. If a hook message and the user's instruction conflict, **the user has the last word.**
