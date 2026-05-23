---
name: pickup
description: Pick up where you left off at the start of a new session. Reads HANDOFF.md, surfaces in-flight context (open PRs, git state, recent compound-engineering artifacts, optional VPS health snapshot for openclaw-prod projects), and proposes a concrete next action. Use at session start to get oriented within 60 seconds.
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.1.0"
  suite: pickup-handoff
---

# /pickup — Pick Up Where We Left Off

Use this command at the start of a new session to get oriented fast.
Reads HANDOFF.md, loads relevant context, and tells you exactly where to start.

## Steps

### Step 1 — Read the handoff
```bash
cat HANDOFF.md 2>/dev/null || echo "No HANDOFF.md found."
```

If no HANDOFF.md exists, say so and fall back to git log:
```bash
git log --oneline -10
git status --short
```

### Step 2 — Load supporting context
```bash
export PATH="$HOME/.config/nvm/versions/node/v24.13.0/bin:$PATH"

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

if [ -n "$REPO" ]; then
  echo "=== Open PRs ==="
  gh pr list --repo "$REPO" --state open --json number,title,headRefName,url
else
  echo "(No GitHub remote detected — skipping PR info)"
fi

echo "=== Current branch ==="
git branch --show-current

echo "=== Uncommitted changes ==="
git status --short
```

### Step 2b — Surface compound-engineering artifacts

Check for recent CE artifacts (brainstorms, plans, solutions) modified in the last 7 days.
These represent in-flight feature work and accumulated learnings that may be relevant.

```bash
echo "=== Recent brainstorms (last 7 days) ==="
find docs/brainstorms -name "*.md" -mtime -7 -exec basename {} \; 2>/dev/null | sort -r || echo "(none)"

echo "=== Recent plans (last 7 days) ==="
find docs/plans -name "*.md" -mtime -7 -exec basename {} \; 2>/dev/null | sort -r || echo "(none)"

echo "=== Recent solutions (last 7 days) ==="
find docs/solutions -name "*.md" -mtime -7 -exec basename {} \; 2>/dev/null | sort -r || echo "(none)"
```

If any artifacts are found:
- **Brainstorms** — mention them as open explorations that may need `/ce:plan` next
- **Plans** — mention them as ready for `/ce:work` (or already in progress)
- **Solutions** — briefly note what was learned (read the `problem_type` and `module` from YAML frontmatter if present)

### Step 2c — VPS health snapshot (openclaw-prod projects)

Skip this step unless this project targets `openclaw-prod`. Detect via git remote:

```bash
git remote -v 2>/dev/null | grep -q "openclaw" || { echo "(not an openclaw-prod project — skipping VPS health snapshot)"; }
```

If the remote doesn't contain "openclaw", skip entirely. Other projects run on different infrastructure.

If it does match, **load `references/vps-health-snapshot.md`** for the full SSH probe and interpretation rules. The probe is kept out of this file to apply only when Step 2c actually fires.

If SSH fails inside the probe: note "VPS health snapshot unavailable" and continue; do not block pickup. Rationale: a down VPS is important information, but a Mac-side `/pickup` shouldn't stall on network problems.

### Step 3 — Orient and propose next action

Synthesize everything into a brief, confident session kickoff:

1. **2-3 sentence summary** of where things stand — what was completed, what's in flight
2. **VPS health headline** (if Step 2c ran) — one line: *"VPS clean"* if all checks passed, or the most urgent finding if not (critical audit finding, OOM regression, restart loop, perm drift)
3. **"Next up:"** — the single most important thing to tackle first, based on "What's Next" in the handoff; bump it below a VPS escalation if 2c surfaced one
4. **CE artifacts** — if any brainstorms, plans, or solutions were found, note them briefly (e.g., "There's an open brainstorm on X ready for planning" or "2 new solutions were compounded last session")
5. **Any gotchas to keep in mind** — surface the watch-outs from the handoff so they're top of mind before touching code
6. **A ready-to-go prompt** — end with something like: *"Ready when you are — just say go and I'll start on [specific task]."*

Keep the tone direct and energized. This is a fresh start, not a status report.

## Notes
- If HANDOFF.md is stale (date is old), flag it: "This handoff is from X days ago — things may have moved."
- If there are open PRs with pending review comments, surface them — they're likely blocking
- Don't re-read CLAUDE.md or project docs unless the handoff references something that requires it
- The goal is: oriented and working within 60 seconds
