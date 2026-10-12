---
name: plan
description: Write or update a plan in docs/plans/ - goal, phases with exit criteria, risks. Use when the user wants to plan work, define phases or milestones, or when work is large enough that the next steps need structure beyond STATE.md.
argument-hint: "[topic]"
---

1. `python .ai/wr.py plan new "<topic>"` creates `docs/plans/<topic>.md`, or open the existing plan.
2. Each phase has **exit criteria** that can be checked, not adjectives. Link the decisions and
   open items a phase depends on.
3. Point `STATE.md` at the current phase; `STATE.md` says where things stand, the plan says where
   they are going.
4. Commit: `python .ai/checkpoint.py "docs(plans): <topic>" "<why the plan changed>"`.
