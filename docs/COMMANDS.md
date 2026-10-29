# WorkRealm commands

Full reference for `wr` and the in-workspace helpers. The overview is in the [README](../README.md).

```
wr new NAME [--quick | --project] [--dir PARENT] [--lang match|en|hr] [--remote | --no-remote]
           [--with github,rag] [--ticket KEY] [--template]
wr integrate github,rag [--path WORKSPACE]
wr upgrade --to task|project [--path WORKSPACE]
wr sync [--check] [--path WORKSPACE]
wr doctor [--fix] [--ci] [--path WORKSPACE]
wr adopt PATH [--tier quick|task|project] [--dry-run]
```

- Language (R-LANG): final outputs (`reports/`, `releases/`: a report, a seminar paper, a
  presentation) are Croatian; everything else (code, comments, commits, notes, decisions, plans,
  `STATE.md`) is English. `--lang` only sets the chat rule; `match` (the default) replies in the
  language the user writes in.
- Names (R-NAMES): a tool's required name first, then the standard of the language or format
  (PEP 8 for Python, `PascalCase` files for Java and C#, Conventional Branch for branches ...),
  then the project's own configuration, else lowercase ASCII kebab-case. Every name is ASCII
  (`č` → `c`, `đ` → `d`); received files are renamed to the standard when they arrive, with the
  original name logged. Names that break a checkout on Windows or macOS are refused; non-ASCII
  names, spaces and off-convention branches warn, and `python .ai/wr.py names --fix` renames them.
  Adopting a repository with its own style (snake_case notes, an Obsidian vault):
  `python .ai/wr.py names notes --style --rewrite-refs` lists what the default style renames and
  how many files' links change; add `--fix` to do it. Code and folders with code keep their
  style, `--keep GLOB` keeps a name a tool's config uses, and a rename that would break a
  `[[wikilink]]` is refused as a whole.
- `upgrade` adds the missing files, rewrites the generated block of `AGENTS.md` (your
  *Project-specific rules* section is kept), the `hooks` key of `.claude/settings.json` and the
  tool-owned files in `.ai/`, `.githooks/` and `.claude/skills/`. Your own files are never overwritten.
- `sync` re-syncs the work agents and skills from AgentBrain (`~/.agentbrain`, or
  `AGENTBRAIN_PATH`) for the workspace's tier, prunes the ones whose source is gone, and records
  the brain version and commit. `--check` reports drift and writes nothing. `new` and `upgrade`
  sync automatically; without a brain they warn and carry on.

- `doctor` checks that the guard-rails still work:
  - version, tool files, settings and rules block;
  - `core.hooksPath` (after a fresh clone, commits are not checked until it is set);
  - remote and unpushed commits; a failed background push is kept in `.git/workrealm-push.log`
    and shown here, in the status and at session start until a push lands;
  - branches already merged and worktrees outside `.claude/worktrees/` or gone from disk (R-BRANCH);
  - the environment: platform, container and host (or `WORKREALM_ENV`) matched against the
    optional `environments` in `.workrealm.json`, each with the `tools` it needs, the `services`
    it must reach and its `setup` command, e.g.
    `{"name": "lab-pc", "host": "lab-*", "tools": ["git", "git-lfs"], "services": [{"name": "qdrant", "url": "http://qdrant.lan:6333"}]}`;
  - work tree, the AgentBrain pin, tracked secrets (including literal tokens in `.mcp.json`);
  - hygiene: tracked virtualenvs, build output (`node_modules/`, `__pycache__/`, `build/`, ...)
    and files over 10 MB, with the command that untracks them;
  - a whole-tree policy pass that lists existing violations without blocking them.

  `--fix` repairs what is safe to repair: hooks path, tool files, settings, rules block, sync, and
  pushing a branch that has no upstream or whose last push failed, pruning vanished worktrees. It never touches secrets (they need rotating), never
  untracks files, and never takes over a `core.hooksPath` another tool set: that is reported
  until its hooks call `.githooks/pre-commit` and `.githooks/commit-msg`. `--ci` skips the checks
  of local state and exits 1 on a failure.
- `adopt` brings an existing folder under WorkRealm and **moves nothing**:
  - it maps the folder's own names onto the roles (`literature/` as sources, `dist/` as releases,
    ADRs kept in `decisions/`, and so on); a folder counts only if it holds tracked files, so
    ignored build output is never a role;
  - it keeps each naming rule only where the folder already follows it, adapts ADR numbering to
    the existing style, and relaxes the rest;
  - it adds the rules block to an existing `AGENTS.md` without touching your text;
  - it makes `CLAUDE.md` and `GEMINI.md` import it;
  - it reports what doesn't fit, including tracked virtualenvs, build output and large files;
  - it **overwrites nothing of another tool's**: if `.ai/`, `.githooks/`, `.claude/skills/` or the
    workflow already hold a file that is not WorkRealm's, it lists the conflict and stops before
    writing anything;
  - the repository's own hooks in `.git/hooks` keep running: WorkRealm's hooks call the one of the
    same name, and any other gets a forwarder in `.githooks/`.

  `--role ROLE=PATH` (repeatable) overrides a wrong guess, e.g. `--role inbox=data/staging`.
  `--dry-run` shows all of this and writes nothing. A folder without Git first gets a baseline
  commit of what is already there; its virtualenvs and build output are ignored before that.

- `--with` / `integrate` add MCP servers to `.mcp.json` (your own servers are kept):

  | Name | Server | Needs |
  |---|---|---|
  | `github` | GitHub's remote server: repos, issues, pull requests, actions | `GITHUB_PAT` in the environment |
  | `rag` | AgentBrain's RAG server (search and ingest the shared corpus), started by `.ai/rag_server.py` | AgentBrain 2.6.0 |

  Claude Code reads `${VAR}` from the environment it starts in, not from `.env`, and asks once
  whether to trust the servers. `doctor` checks the entries and, locally, the variables.
- `--ticket KEY` records the ticket the workspace serves. Inside any workspace,
  `python .ai/wr.py ticket start KEY "title"` creates `feat/KEY-title`; `checkpoint.py` adds
  `Refs: KEY` to every commit on it, and the commit check warns when it is missing. With GitHub
  Issues, issue #42's key is `GH-42`, which GitHub links like `#42`.
- Task and project workspaces get `.github/workflows/workrealm.yml`: on every push and pull
  request it runs `python .ai/policy.py ci`, which re-checks the pushed commits (a commit made
  with `--no-verify` fails there) and the whole tree for secrets. It needs no secrets.

- `--template` makes the new workspace a GitHub template repository. A new workspace then needs
  no WorkRealm on the machine: "Use this template" on GitHub (or
  `gh repo create NAME --template OWNER/REPO --private --clone`), then, in the clone,
  `python .ai/wr.py init`. It names the workspace after its folder (or `--name`), dates it, turns
  the git hooks on and commits. One template per tier is enough; keep it current with
  `wr doctor --fix` in the template repo.

**After cloning a workspace**, run `python .ai/wr.py init` once. The hooks are versioned, but Git
does not turn on a hooks path by itself; the session status says when they are off.
