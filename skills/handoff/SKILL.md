---
name: handoff
description: Generate a session HANDOFF.md at the repo root capturing what was built, decisions made, what's next, and gotchas — so the next session can `/pickup` and be working within 60 seconds. Use at the end of any working session. Optionally scope it (`/handoff hero section`, `/handoff PR 28 work`).
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.1.0"
  suite: pickup-handoff
---

# /handoff — Generate Session Handoff Doc

Use this command at the end of any working session to write `HANDOFF.md` at the repo root.
Captures what was built, decisions made, what's next, and gotchas — so the next session
(yours or a teammate's) can `/pickup` and be working within 60 seconds.

Optionally scope it: `/handoff hero section` or `/handoff PR 28 work`.

## Steps

### Step 1 — Gather context
```bash
export PATH="$HOME/.config/nvm/versions/node/v24.13.0/bin:$PATH"

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

echo "=== Commits this session (branch vs main) ==="
git log main..HEAD --oneline 2>/dev/null || git log --oneline -10

if [ -n "$REPO" ]; then
  echo "=== Recently merged PRs (last 5) ==="
  gh pr list --repo "$REPO" --state merged --limit 5 --json number,title,mergedAt

  echo "=== Open PRs ==="
  gh pr list --repo "$REPO" --state open --json number,title,headRefName,url

  echo "=== Open PR review comments (first open PR) ==="
  OPEN_PR=$(gh pr list --repo "$REPO" --state open --json number --jq '.[0].number' 2>/dev/null)
  if [ -n "$OPEN_PR" ]; then
    gh pr view $OPEN_PR --repo "$REPO" --comments 2>/dev/null | tail -40
  fi
else
  echo "(No GitHub remote detected — skipping PR info)"
fi

echo "=== Uncommitted changes ==="
git status --short
```

### Step 2 — Write HANDOFF.md

Using everything from this session plus the gathered context, write `HANDOFF.md`:

```markdown
# HANDOFF — [YYYY-MM-DD, time of day]

## What We Built
[Concrete bullet list — PRs opened/merged, components changed, bugs fixed, docs added.
Name the files, PR numbers, and components. "Fixed hero clip-path" is weak. "PR #28 — tuned
ellipse(80% 56%) dome, reduced top padding pt-20→pt-6, moved brand label below subtitle" is good.]

## Decisions Made
[Architectural, design, or implementation calls and the reasoning behind them.
If a CLAUDE.md rule was added or updated, note it here.
If something was explicitly ruled out, say so and why — saves the next session from relitigating it.]

## What Didn't Work
[Approaches that failed, dead ends, or things explicitly ruled out — so the next session
doesn't relitigate or retry them. Include why they failed when known.]

## What's Next
[Prioritized list. Lead with the single most important thing.
Be specific: name the file, PR, or component. Vague summaries don't help the next session.]

## Gotchas & Watch-outs
[Anything that bit us, workarounds in place, known fragile spots, or things to check before
touching related code. When in doubt, over-document here.]
```

**Quality bar:** Every bullet should be specific enough that someone who wasn't in this session
knows exactly what happened and what to do next. No vague summaries.

### Step 3 — Check for blockers
Before confirming, scan for anything that would block the next session and call it out explicitly if found:
- Open PR with unresolved review comments → list them
- Uncommitted changes that should be stashed or committed first
- A decision that's still open / needs input from someone else

### Step 4 — Confirm
After writing, reply with:
- "✅ HANDOFF.md written."
- A 2-sentence plain-English summary of session state — what shipped and what's in flight
- If there are immediate blockers: "⚠️ Before next session: [specific thing]"

## Notes
- Overwrites existing HANDOFF.md — it's always current-session state, not a history log
- Commits the file automatically if there are no other uncommitted changes:
  ```bash
  git add HANDOFF.md && git commit -m "docs: update handoff"
  git remote | grep -q . && git push || echo "(no remote — skipping push)"
  ```
  If there ARE other uncommitted changes, skip the commit and note it in the confirmation.
- Pairs with `/pickup` — the next session starts there
