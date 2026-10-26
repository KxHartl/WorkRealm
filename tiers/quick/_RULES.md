## How these rules bind

Each rule carries an ID and says what enforces it. **git** means `.githooks/` refuses a commit
that breaks it, whichever tool or person makes the commit; **claude** means a Claude Code hook
acts on it as it happens (stops the write or command, or loads the context); **advisory** means
only this text holds it, so it
depends on you. The checks live in `.ai/policy.py`; their messages quote the rule ID.
Never bypass a check with `--no-verify`. If a check is wrong, say so and fix the check.
Where the workspace has the WorkRealm GitHub workflow, every push runs the same checks again,
so a commit that skipped the hooks is still caught.

**Use the helpers.** `python .ai/wr.py` does each common step the way the checks accept it:
`status`, `checkpoint`, `handoff`, and at higher tiers `note`, `source add`, `decide`, `open-item`,
`adr new`, `exp new`, `run new`, `release cut` (`--help` lists them). Prefer them to doing it by hand.

## Communication

> **R-LANG** · enforced by: git

{{CHAT_LANG}} **Final outputs** — what the work hands over, such as a report, a seminar paper or a
presentation, in `reports/` and `releases/` — are written in Croatian. **Everything else is
English:** code, comments, commit messages, notes, decisions, plans, `STATE.md` and these rules.
The pre-commit check warns (never blocks) when non-English text is added anywhere else than the
final outputs, `references/` and `data/raw/`; quoting a source verbatim is fine, and so is
text in `code`.

## Names follow the standard of what they name

> **R-NAMES** · enforced by: git

The first of these that applies decides a name:

1. **A tool requires it:** `README.md`, `LICENSE`, `CHANGELOG.md`, `Dockerfile`, `Makefile`,
   `package.json`, `test_*.py`, a Java class's file.
2. **The standard of the language or format**, below.
3. **What the project already set:** `.editorconfig`, linter configuration, a numbering scheme
   the client or a norm mandates.
4. **Otherwise:** lowercase ASCII kebab-case, ISO 8601 dates first (`2026-10-26-site-survey.md`).

| What | Standard | Example |
|---|---|---|
| Branch | Conventional Branch: `<type>/<short-desc>`, a ticket key first | `feat/ABC-123-cache-warmup`, `docs/setup-guide` |
| Commit · tag · repository | Conventional Commits · SemVer · lowercase kebab | `fix(api): ...` · `v1.2.0` · `site-survey-2026` |
| Python | PEP 8: modules and functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE` | `data_loader.py`, `test_loader.py` |
| JavaScript · TypeScript | files kebab-case, React components `PascalCase`; values `camelCase`, types `PascalCase` | `user-store.ts`, `UserCard.tsx` |
| Java · Kotlin · C# | one type per file, named after it, `PascalCase`; Java packages `lower.dot` | `DataLoader.java` |
| Go · Rust · C · C++ · R | files `snake_case`; Go tests `_test.go` | `data_loader.go`, `load_data.R` |
| Shell · PowerShell | `kebab-case.sh` · `Verb-Noun.ps1` with an approved verb | `Get-Report.ps1` |
| SQL · CSV columns · environment | `snake_case` · `snake_case` with the unit · `UPPER_SNAKE` | `length_mm`, `GITHUB_PAT` |
| JSON · YAML keys | the schema of the tool that reads them | |
| Notebooks · LaTeX | ordered `NN-desc.ipynb` · kebab-case, labels `fig:` `tab:` `sec:` `eq:` | `01-explore-raw.ipynb` |
| Documents · figures | default; `-v01` while drafting, `-v1.0` once issued; figures numbered | `fig-03-load-curve.png` |
| Received files (sources, raw data) | made standard once, when they arrive: ASCII, lowercase kebab-case, lowercase extension; the original name is noted where the file is logged | `izvjesce-o-stanju-2024.pdf` |
| Derived data | the stem of the file it comes from, then what was done | `data/raw/survey-2026.csv` → `data/processed/survey-2026-cleaned.csv` |

Every name is ASCII, the Croatian final outputs' too: a letter with a diacritic becomes its
closest ASCII letter (`č` `ć` → `c`, `š` → `s`, `ž` → `z`, `đ` → `d`). A commit is **refused** when a name would
break a checkout somewhere: a reserved Windows name (`CON`, `NUL`, `COM1` ...), one of
`< > : " \ | ? *`, a trailing dot or space, two paths that differ only in case, or a path over
200 characters. It **warns** about non-ASCII letters, spaces and a branch outside
`<type>/<short-desc>`. `python .ai/wr.py names` lists what to rename and `names --fix` renames it
with `git mv`. `source add`, `source promote` and the helpers that create files already name them
this way. A received file is write-once once committed, so fix its name before the first commit.

## Context first

> **R-STATE** · enforced by: claude

Read `STATE.md` before doing anything — it is the only memory that survives between sessions.
In Claude Code the session-start hook prints it with the workspace status, and again after a
context compaction; in other tools, run `python .ai/wr.py status` first.
Update it whenever the goal, the next step or a blocker changes, and before ending a session
(`python .ai/wr.py handoff`).

## Commit every logical unit, immediately

> **R-COMMIT** · enforced by: git, claude

- After each logical unit of work: `python .ai/checkpoint.py "type: what changed"`.
  Do not wait for the end of the task, and do not wait to be asked.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` …), checked on every commit.
  The body says **why**.
- **AI marking is for work a subagent did on its own.** Its commits get the robot tag in the
  subject and an `AI-Agent: <name>` trailer, added automatically in Claude Code. Work done at the
  user's prompt, by the main agent, is committed unmarked. Never add or remove the mark by hand;
  the two parts must appear together, and a commit with only one is refused.
- The `post-commit` hook pushes every commit when a remote exists. A local-only commit is one
  disk failure from gone.
- Before finishing a response, `git status --porcelain` must be empty. The Claude Stop hook
  enforces it; in other tools it is on you.

## Work on a ticket names it

> **R-TICKET** · enforced by: git

When the work belongs to a ticket, its branch carries the key:
`python .ai/wr.py ticket start ABC-123 "short title"` creates `feat/ABC-123-short-title`. Every
commit on it ends with a `Refs: ABC-123` trailer, which `python .ai/checkpoint.py` adds; the
commit check warns (never blocks) when it is missing. A workspace made for one ticket
(`wr new --ticket ABC-123`) treats every branch as that ticket's.

## Secrets never enter Git

> **R-SECRETS** · enforced by: git

Secrets live in `.env`, which is gitignored; `.env.example` carries the shape, never the values.
Commits containing files that look like secrets are refused, and so is a literal credential in
`.mcp.json` or `.claude/settings.json`: those reference variables (`${GITHUB_PAT}`), which Claude
Code reads from the environment it starts in. If one is committed anyway:
**stop, do not push, rotate the secret.**

## Verify, don't recall

> **R-VERIFY** · advisory

Claims about current tool behaviour — versions, APIs, limits, prices, licences — are checked
against current documentation before they are written down or acted on. Cite where it came from.

## Stay in scope

> **R-SCOPE** · advisory

Do what was asked. If the work turns out bigger than this tier was set up for, say so and suggest
`wr upgrade --to <tier>` instead of growing structure ad hoc.
