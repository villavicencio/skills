---
name: critique
description: Stress-test a plan before implementing it by running three parallel critique subagents (a Skeptic hunting for risks and edge cases, a Simplifier cutting unnecessary complexity, and a Historian checking prior art and conventions), then synthesizing their findings into a revised plan. Use before a non-trivial change when the user wants the approach pressure-tested, says "critique this plan", or describes what they're about to build and wants multiple perspectives first.
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.4.0"
---

# /critique — Multi-Agent Plan Critique

Before implementing a non-trivial change, get multiple perspectives to stress-test
the approach.

<change_to_critique>
#$ARGUMENTS
</change_to_critique>

Optionally scope it: `/critique migrate from NVM to fnm` or `/critique redesign the lazy loader pattern`.

## Steps

### Step 1 — Draft the initial plan

Based on the change described above and the current codebase, draft a concrete
implementation plan. Include: what files change, what the changes are, and what the
expected outcome is.

### Step 2 — Launch three critique agents in parallel

Spin up three parallel Sonnet subagents, each with a different lens. Give each agent:
- The implementation plan from Step 1
- The relevant CLAUDE.md and codebase context
- Their specific critique perspective

**Agent A — "The Skeptic"**
```
You are reviewing an implementation plan. Your job is to find flaws, risks, and
things that could go wrong. Consider: edge cases, breaking changes, cross-environment
compatibility (different machines or OSes), rollback difficulty, and
whether this is solving the right problem. Be specific — name the files and
scenarios. Don't rubber-stamp anything.
```

**Agent B — "The Simplifier"**
```
You are reviewing an implementation plan. Your job is to find unnecessary complexity.
Consider: can this be done with fewer changes? Are we introducing abstractions we
don't need yet? Is there a simpler approach that achieves 90% of the benefit with
10% of the work? Would a future maintainer understand this without explanation?
Be specific — suggest concrete simplifications.
```

**Agent C — "The Historian"**
```
You are reviewing an implementation plan. Your job is to check if we've tried
something similar before and what happened. Read the git log and any prior-art the
project keeps — CLAUDE.md, a HANDOFF.md, or docs/solutions/ if they exist. Consider:
does this conflict with existing conventions in CLAUDE.md? Does it undo work from a
previous session? Are there documented reasons why the current approach exists? Be
specific — cite commits, docs, or conventions.
```

### Step 3 — Synthesize

Collect all three critiques and present a summary:

1. **Consensus** — what all three agree on (green light or red flag)
2. **Concerns raised** — specific issues from each agent, grouped by severity
3. **Suggested modifications** — concrete changes to the original plan
4. **Revised plan** — the improved plan incorporating valid critiques

### Step 4 — Present to user

Show the revised plan and ask: "Ready to implement, or want to adjust?"

Do NOT implement anything until the user approves.

## Notes
- Use Sonnet for the critique agents (cost-efficient, good enough for analysis)
- Each agent should read the relevant files, not just work from the plan text
- If all three agents approve with no concerns, say so — don't invent problems
- The goal is better decisions, not slower decisions
