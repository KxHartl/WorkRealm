# WorkRealm — rules for AI agents working on the generator itself

This repo is the **template**, not a workspace. Its rules are short on purpose.

1. **Tiers are strict extensions.** Anything added to `tiers/task/` must still make sense at
   `project`; nothing in a higher tier may require moving or renaming a lower tier's file.
   Otherwise `wr upgrade` stops being a pure addition.
2. **Rules live in `tiers/*/_RULES.md` only.** Never write rule text into `wr.py` or into a
   tier's `CLAUDE.md`. Duplicated rules drift.
3. **Every behaviour has a test** in `tests/test_wr.py`. Run `python -m unittest discover tests`
   before committing; a failing suite is not committed.
4. **Standard library only** in `wr.py` and every hook. A workspace must work on a bare Python.
5. **Commit every logical unit immediately**, Conventional Commits, body says why. Bump
   `VERSION` and `CHANGELOG.md` for anything a generated workspace would notice.
6. **Chat:** reply in the language the user writes in. **Documents, code, commits:** English.
