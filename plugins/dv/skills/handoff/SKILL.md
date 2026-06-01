---
name: handoff
description: "Write a HANDOFF.md serializing this session — what shipped, decisions, what's next, gotchas. Use at session end; pairs with `dv:pickup`."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.1.0"
---

# /handoff — Generate Session Handoff Doc

Use this command at the end of any working session to write `HANDOFF.md` at the repo root.
Captures what was built, decisions made, what's next, and gotchas — so the next session
(yours or a teammate's) can `/pickup` and resume cold.

## Steps

### Step 1 — Gather context
```bash
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "(not a git repo — skipping repo context)"
else
  DEFAULT=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
  echo "=== Commits this session (branch vs ${DEFAULT:-main}) ==="
  git log "${DEFAULT:-main}..HEAD" --oneline 2>/dev/null || git log --oneline -10

  if command -v gh >/dev/null 2>&1; then
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
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
  else
    echo "(gh not in PATH — skipping GitHub queries)"
  fi

  echo "=== Uncommitted changes ==="
  git status --short
fi
```

### Step 2 — Write HANDOFF.md

Using everything from this session plus the gathered context, write `HANDOFF.md`:

```markdown
# HANDOFF — [YYYY-MM-DD, time of day]

[One paragraph (2-3 sentences) framing the session — what arc you were on, what the goal was, what came before. Sets context for everything below.]

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
  if git add HANDOFF.md && git commit -m "docs: update handoff"; then
    if git remote | grep -q .; then
      git push
    else
      echo "(no remote — skipping push)"
    fi
  fi
  ```
  If there ARE other uncommitted changes, skip the commit and note it in the confirmation. If the commit or push fails, surface the failure rather than continuing silently.
- Pairs with `/pickup` — the next session starts there
