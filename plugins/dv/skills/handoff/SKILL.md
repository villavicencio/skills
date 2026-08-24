---
name: handoff
description: "Write a HANDOFF.md serializing this session — what shipped, decisions, what's next, gotchas — under commit-anchored frontmatter (created_at, branch, head); `focus: <text>` records what the next session should pick up first. Use at session end; pairs with `dv:pickup`."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.3.0"
---

# /handoff — Generate Session Handoff Doc

Use this command at the end of any working session to write `HANDOFF.md` at the repo root.
Captures what was built, decisions made, what's next, and gotchas — so the next session
(yours or a teammate's) can `/pickup` and resume cold.

<handoff_args>
#$ARGUMENTS
</handoff_args>

## Arguments

Parse the block above. Bare invocation takes no arguments.

| Arg | Effect |
|---|---|
| `focus: <text>` | Sets `resume_focus` in the frontmatter — the one thing the next session should pick up first. `/pickup` treats it as the default "Next up" unless the handoff body contradicts it. Omitted → the field is omitted. Escape it as YAML (see Frontmatter rules). |

Anything else in the block is free-text context for the handoff body.

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

  echo "=== Anchor (copy verbatim into the frontmatter) ==="
  if SHA=$(git rev-parse --short HEAD 2>/dev/null); then
    echo "head: $SHA"
  else
    echo "(unborn HEAD — no commits yet; OMIT the head field entirely)"
  fi
  BRANCH=$(git branch --show-current); echo "branch: ${BRANCH:-(detached)}"
fi
echo "created_at: $(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\([0-9][0-9]\)$/:\1/')"
```

### Step 2 — Write HANDOFF.md

**First `Read` the existing `HANDOFF.md` (if one exists), then overwrite it.** The file-write tool
refuses to overwrite a file you have not `Read` in the current session — and `/pickup`'s `cat
HANDOFF.md` does NOT satisfy that guard (it is a shell command, not a tool `Read`). Skipping this
makes the first write fail with "Error writing file," then succeed only on the retry after a `Read`.
Reading it first makes the overwrite succeed cleanly on the first try.

Then, using everything from this session plus the gathered context, write `HANDOFF.md`:

```markdown
---
created_at: "[ISO-8601 with TZ offset — the created_at line from Step 1's anchor block]"
branch: "[branch from the anchor block]"
head: "[short sha from the anchor block]"
resume_focus: "[the focus: argument — include this line ONLY when focus: was passed]"
---
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

**Frontmatter rules:**

- Copy `head`, `branch`, and `created_at` **verbatim** from the anchor block — never from memory,
  never re-derived. Quote every value.
- **Omit `head`** when the anchor block reports an unborn HEAD, and omit both `branch` and `head`
  outside a git repo. An omitted field is correct; a placeholder like `unborn` is not — `/pickup`
  parses `head` as a hex sha and a non-hex value silently disables the anchor path.
- **`resume_focus` must be valid YAML.** In the double-quoted value escape `\` as `\\` and `"` as
  `\"`, and collapse any newline to a space — a raw quote in the focus text ends the scalar early
  and makes the whole block unparseable.
- `/pickup` parses this block to compute commits-since-handoff, so `head` must be the HEAD *at
  write time*. Where the auto-commit in Notes actually runs, it lands one commit after `head`, and
  `/pickup` names that lone `docs: update handoff` as the handoff's own commit rather than drift —
  but it is skipped when `HANDOFF.md` is gitignored or other changes are pending, in which case
  there is no offset at all.

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
- Overwrites existing HANDOFF.md — it's always current-session state, not a history log. A
  pre-0.4.0 file without frontmatter is overwritten the same way; nothing is parsed from it
- Commits the file automatically if there are no other uncommitted changes:
  ```bash
  if git check-ignore -q HANDOFF.md; then
    echo "(HANDOFF.md is gitignored in this repo — local-only by design; skipping commit)"
  elif [ -n "$(git status --porcelain | grep -v '^.. HANDOFF\.md$')" ]; then
    echo "(other uncommitted changes present — skipping the handoff commit; say so in the confirmation)"
  elif git add HANDOFF.md && git commit -m "docs: update handoff"; then
    if git remote | grep -q .; then
      git push
    else
      echo "(no remote — skipping push)"
    fi
  else
    echo "!! HANDOFF.md could not be staged or committed — report this, do not continue silently"
  fi
  ```
  **Never `git add -f` a gitignored `HANDOFF.md`** — repos that ignore it (this one does) keep it
  local-only deliberately, and force-adding would commit session state the repo has opted out of.
  A skipped commit is a normal outcome there, not a failure. The porcelain guard enforces the
  other-uncommitted-changes rule in the block itself rather than leaving it to prose — staged
  changes would otherwise ride along in the handoff commit. If the commit or push fails, surface
  the failure rather than continuing silently.
- Pairs with `/pickup` — the next session starts there
