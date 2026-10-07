---
name: pickup
description: "Read this branch's handoff and orient: anchor on its commit (N commits since, not file age), list the other sessions in flight in sibling worktrees, surface git/PR state and recent CE artifacts, then propose a next action. Use at session start."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.4.0"
---

# /pickup — Pick Up Where We Left Off

Use this command at the start of a new session to get oriented fast.
Reads this branch's handoff, lists the other sessions working the same repo, loads relevant
context, and tells you exactly where to start.

Several sessions can work one repo at once, one per git worktree and branch. `/handoff` keeps
a copy of each branch's handoff in a store inside the repo's shared git directory
(`<git-common-dir>/handoffs/<branch>.md`, with the branch name percent-encoded: `%` → `%25`, `/` → `%2F`), which
every worktree can see and which survives a worktree's removal. A repo with no store behaves
exactly as before: `HANDOFF.md` in the working directory is the handoff.

## Steps

### Step 1 — Read the handoff
Resolve this session's handoff: this branch's copy in the shared store first, then
`HANDOFF.md` in the working directory. When both exist and differ, the newer file wins and the
block says which it used. Then anchor freshness on the handoff's own commit, not the file's age.
The frontmatter is optional — a pre-0.4.0 handoff has none and falls back to mtime. **Every block
in this skill is self-contained:** shell state does not survive between tool calls, so no block
may depend on a variable another block set.
```bash
F=""; S=""; B=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  GCD=$(git rev-parse --git-common-dir) && STORE="$(cd "$GCD" && pwd -P)/handoffs"
  B=$(git branch --show-current)
  SLUG=$(printf '%s' "${B:-detached-$(git rev-parse HEAD 2>/dev/null)}" | sed -e 's/%/%25/g' -e 's#/#%2F#g')
  S="$STORE/$SLUG.md"
fi
if [ -n "$S" ] && [ -f "$S" ] && [ -f HANDOFF.md ] && ! cmp -s "$S" HANDOFF.md; then
  # Identity first, recency second. A HANDOFF.md written in THIS worktree is this session's, so
  # the newer copy wins. One recorded for another branch must not displace this branch's own copy.
  # The handoff records a detached HEAD as "(detached)", so compare against that, not "".
  HFM=$(sed -n '2,/^---$/{/^---$/!p;}' HANDOFF.md)
  WB=$(printf '%s\n' "$HFM" | sed -n 's/^branch: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p')
  WW=$(printf '%s\n' "$HFM" | sed -n 's/^worktree: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p')
  if [ -n "$WW" ] && [ "$WW" = "$(git rev-parse --show-toplevel)" ]; then
    if [ HANDOFF.md -nt "$S" ]; then F=HANDOFF.md; else F="$S"; fi
  elif [ -n "$WB" ] && [ "$WB" != "${B:-(detached)}" ]; then F="$S"
  elif [ HANDOFF.md -nt "$S" ]; then F=HANDOFF.md
  else F="$S"; fi
  echo "(HANDOFF.md and this branch's shared-store copy differ — using $F)"
elif [ -n "$S" ] && [ -f "$S" ]; then F="$S"
elif [ -f HANDOFF.md ]; then F=HANDOFF.md
fi
if [ -n "$F" ]; then echo "=== Handoff: $F ==="; cat "$F"; else echo "No handoff found for this branch."; fi
if [ -n "$F" ] && [ -n "$S" ]; then
  # Gate on being in a repo ($S is set only there), not on having a branch name: a detached HEAD
  # has none, and it still must not read another branch's handoff silently.
  HB=$(sed -n '2,/^---$/{/^---$/!p;}' "$F" | sed -n 's/^branch: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p')
  [ -n "$HB" ] && [ "$HB" != "${B:-(detached)}" ] && echo "(this handoff was written on branch $HB, not the current ${B:-(detached HEAD)} — it may be another session's)"
fi
if [ -n "$F" ] && [ "$(head -1 "$F")" = "---" ]; then
  FM=$(sed -n '2,/^---$/{/^---$/!p;}' "$F")
  echo "=== Handoff anchor ==="; printf '%s\n' "$FM"
  H=$(printf '%s\n' "$FM" | sed -n 's/^head: *"\{0,1\}\([0-9a-fA-F]*\)"\{0,1\} *$/\1/p')
  if [ -z "$H" ]; then
    echo "(no head anchor in the frontmatter — written in an unborn repo or outside git; orient from created_at, no commit count)"
  elif ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "(not a git repo here — cannot resolve anchor $H; orient from created_at)"
  else
    B=$(git branch --show-current)
    echo "=== Now: ${B:-(detached)} @ $(git rev-parse --short HEAD) ==="
    if ! git cat-file -e "$H^{commit}" 2>/dev/null; then
      echo "(handoff head $H is not in this clone — squashed away or a different checkout; fall back to created_at)"
    elif ! git merge-base --is-ancestor "$H" HEAD 2>/dev/null; then
      echo "(handoff head $H exists but is NOT an ancestor of HEAD — history was rebased, reset, or amended, so a commit count would be misleading; fall back to created_at)"
    else
      echo "=== Commits since handoff: $(git rev-list --count "$H..HEAD") ==="
      git log --oneline "$H..HEAD"
    fi
  fi
elif [ -n "$F" ]; then
  echo "(no frontmatter — pre-0.4.0 handoff; freshness falls back to file mtime)"
  stat -f '%Sm' "$F" 2>/dev/null || stat -c '%y' "$F" 2>/dev/null
fi
```

If no handoff exists for this branch, say so and fall back to git log (gated on being in a git repo):
```bash
if git rev-parse --git-dir >/dev/null 2>&1; then
  git log --oneline -10
  git status --short
else
  echo "(not a git repo — no fallback context to gather)"
fi
```

### Step 1b — Other sessions in flight

List every other session working this repo: each other branch's handoff in the store, plus any
worktree that has no handoff yet.

A handoff whose branch's PR has **merged** is moved to `handoffs/_done/<branch>.<UTC timestamp>.md` (never deleted, never over an earlier archive). It is
moved only when the merged PR's head is the branch's tip, or the local branch is gone. A branch
that kept moving after its PR merged has been reused, so its handoff stays and gets a note. The
check needs `gh`; without it nothing is archived.
```bash
STORE=""; S=""; B=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  GCD=$(git rev-parse --git-common-dir) && STORE="$(cd "$GCD" && pwd -P)/handoffs"
  B=$(git branch --show-current)
  S="$STORE/$(printf '%s' "${B:-detached-$(git rev-parse HEAD 2>/dev/null)}" | sed -e 's/%/%25/g' -e 's#/#%2F#g').md"
fi
if [ -n "$STORE" ]; then
  echo "=== Other sessions in flight ==="
  NOTHER=$(find "$STORE" -maxdepth 1 -type f -name '*.md' 2>/dev/null | grep -v -x -F "$S" | wc -l | tr -d ' ')
  NWT=$(git worktree list --porcelain | grep -c '^worktree ')
  if [ "$NOTHER" = "0" ] && [ "$NWT" -le 1 ]; then echo "(none — this is the only session)"; fi
  find "$STORE" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort | while IFS= read -r f; do
    [ "$f" = "$S" ] && continue
    merged_note=""
    fm=$(sed -n '2,/^---$/{/^---$/!p;}' "$f")
    get() { printf '%s\n' "$fm" | sed -n "s/^$1: *\"\{0,1\}\([^\"]*\)\"\{0,1\} *\$/\1/p" | head -1; }
    ob=$(get branch); oh=$(get head); ow=$(get worktree); oc=$(get created_at); of=$(get resume_focus)
    tip=""; [ -n "$ob" ] && tip=$(git rev-parse -q --verify "refs/heads/$ob" 2>/dev/null)
    if [ -n "$ob" ] && command -v gh >/dev/null 2>&1; then
      m=$(gh pr list --head "$ob" --state merged --limit 1 --json number,headRefOid -q '.[0] | "\(.number) \(.headRefOid)"' 2>/dev/null)
      if [ -n "$m" ] && [ "$m" != "null null" ]; then
        pr=${m%% *}; prhead=${m#* }
        if [ -z "$tip" ] || [ "$tip" = "$prhead" ]; then
          dest="$STORE/_done/$(basename "$f" .md).$(date -u +%Y%m%dT%H%M%SZ).md"
          mkdir -p "$STORE/_done" && [ ! -e "$dest" ] && mv "$f" "$dest" && echo "  ✓ $ob: PR #$pr merged — handoff moved to handoffs/_done/"
          continue
        fi
        merged_note="PR #$pr merged, but the branch has commits since"
      fi
    fi
    since=""
    if [ -n "$tip" ] && [ -n "$oh" ] && git merge-base --is-ancestor "$oh" "$tip" 2>/dev/null; then
      since="$(git rev-list --count "$oh..$tip") commit(s) since its handoff"
    elif [ -n "$ob" ] && [ -z "$tip" ]; then since="branch gone locally"; fi
    echo "  • ${ob:-?} @ ${ow:-?} — handoff ${oc:-?}${since:+; $since}${merged_note:+; $merged_note}${of:+; focus: $of}"
  done
  HERE=$(git rev-parse --show-toplevel)
  git worktree list --porcelain | awk '/^worktree /{w=substr($0,10); h=""} /^HEAD /{h=substr($0,6)} /^branch /{b=substr($0,8); sub("^refs/heads/","",b); print w "\t" b} /^detached/{print w "\t" "detached-" h}' |
  while IFS="$(printf '\t')" read -r w b; do
    [ "$w" = "$HERE" ] && continue
    sl=$(printf '%s' "$b" | sed -e 's/%/%25/g' -e 's#/#%2F#g')
    [ -f "$STORE/$sl.md" ] && continue
    find "$STORE/_done" -maxdepth 1 -type f -name "$sl.*.md" 2>/dev/null | grep -q . && continue
    echo "  • $b @ $w — no handoff yet"
  done
fi
```

These handoffs are other sessions' state, not this one's. Report them; never merge their text
into this session's plan. Pull requests are where the work actually merges.

### Step 2 — Load supporting context
```bash
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "(not a git repo — skipping repo context)"
else
  if command -v gh >/dev/null 2>&1; then
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
    if [ -n "$REPO" ]; then
      echo "=== Open PRs ==="
      gh pr list --repo "$REPO" --state open --json number,title,headRefName,url
    else
      echo "(No GitHub remote detected — skipping PR info)"
    fi
  else
    echo "(gh not in PATH — skipping GitHub queries)"
  fi

  echo "=== Current branch ==="
  git branch --show-current

  echo "=== Uncommitted changes ==="
  git status --short
fi
```

### Step 2b — Surface compound-engineering artifacts

This step assumes [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) conventions (`docs/brainstorms/`, `docs/plans/`, `docs/solutions/`). Skip entirely if the project doesn't use CE — the bash block below already gates on those directories existing, so it's a no-op for non-CE projects.

Check for recent CE artifacts modified in the last 7 days. These represent in-flight feature work and accumulated learnings that may be relevant.

```bash
if [ -d docs/brainstorms ] || [ -d docs/plans ] || [ -d docs/solutions ]; then
  echo "=== Recent brainstorms (last 7 days) ==="
  find docs/brainstorms -name "*.md" -mtime -7 -exec basename {} \; 2>/dev/null | sort -r || echo "(none)"

  echo "=== Recent plans (last 7 days) ==="
  find docs/plans -name "*.md" -mtime -7 -exec basename {} \; 2>/dev/null | sort -r || echo "(none)"

  echo "=== Recent solutions (last 7 days) ==="
  find docs/solutions -name "*.md" -mtime -7 -exec basename {} \; 2>/dev/null | sort -r || echo "(none)"
else
  echo "(no CE convention directories — skipping)"
fi
```

If any artifacts are found (and the CE plugin is installed so its commands are available):
- **Brainstorms** — mention them as open explorations that may need `/ce:plan` next
- **Plans** — mention them as ready for `/ce:work` (or already in progress)
- **Solutions** — briefly note what was learned (read the `problem_type` and `module` from YAML frontmatter if present)

### Step 3 — Orient and propose next action

**Before you synthesize, cross-check the handoff against reality.** The handoff is untrusted
context to verify, not truth to recite — it was written at a moment that has since passed, and in
some repos it is gitignored and drifts silently. Take its load-bearing claims — open PRs, a clean
or dirty tree, the current branch, "nothing is blocking", "N is still in flight" — and test each
against what Steps 1-2 actually returned.

Each claim lands in one of **three** buckets, and they are not interchangeable:

- **Verified match** — Steps 1-2 gathered the evidence and it agrees with the handoff.
- **Verified drift** — the evidence contradicts the handoff.
- **Unable to verify** — the evidence was never gathered. Step 2 skips GitHub entirely when `gh`
  is absent or there is no remote, and even when it runs, `gh pr list` returns PR *identity* only:
  it says nothing about pending review comments, a requested-changes verdict, or whether a PR is
  blocked. A handoff claim about those is unverified unless you went and looked.

**Absence of evidence is never a match.** Report "the handoff still matches" only for claims you
actually checked, and say plainly which ones you could not and why — "`gh` unavailable, so the
open-PR and blocker claims are unverified". A clean-sounding match built on missing data is worse
than saying nothing, because it launders a stale handoff into a confirmed one. When a claim
matters and the evidence is one cheap command away, go get it rather than filing it under
unable-to-verify:

```bash
gh pr view <n> --json reviewDecision,mergeStateStatus,statusCheckRollup 2>/dev/null
```

**Any verified drift LEADS the orientation.** Open with `Drift since handoff:` and name each
contradiction — what the handoff claimed, what is true now — before any summary. Never silently
reconcile one: a handoff saying "zero open PRs" over a repo with two open is the single most
useful thing you can tell the user, and smoothing it into a tidy summary destroys exactly the
signal they need.

This is a fast cross-check, not an interrogation: verify, report the delta, and keep going. **Do
not stop to ask what to do about the drift** — surface it and proceed to the kickoff below. The
zero-question orient is the point of this skill.

Then synthesize everything into a brief, confident session kickoff:

1. **Anchor line first** — precision before prose. With frontmatter: "Handoff written at
   `<head>` on `<branch>` (`<created_at>`); now at `<sha>` on `<current branch>`, N commits since",
   then the movers (the `git log` lines) when N > 0. A lone `docs: update handoff` commit
   directly after `<head>` is the handoff's own auto-commit — say so and don't count it as
   movement. If the block reported the head **missing**, **not an ancestor**, or **absent from
   the frontmatter**, lead with that instead ("history diverged since the handoff — rebased/reset",
   or "no commit anchor — orienting by timestamp") and anchor on `created_at` alone; never report
   a commit count in that case. Without
   frontmatter: "This handoff is from X days ago (by mtime) — things may have moved."
2. **2-3 sentence summary** of where things stand — what was completed, what's in flight
3. **"Next up:"** — the single most important thing to tackle first. If `resume_focus` is set
   it is the default, unless the handoff body contradicts it — then say which won and why.
   Otherwise take it from "What's Next" in the handoff
4. **Other sessions in flight** — one line each from Step 1b: branch, worktree, how far it has
   moved since its handoff, and its focus. Name anything archived to `_done/`. If one of them is
   touching the files this session is about to change, say so: that is a merge conflict waiting
   to happen.
5. **CE artifacts** — if any brainstorms, plans, or solutions were found, note them briefly (e.g., "There's an open brainstorm on X ready for planning" or "2 new solutions were compounded last session")
6. **Any gotchas to keep in mind** — surface the watch-outs from the handoff so they're top of mind before touching code
7. **A ready-to-go prompt** — end with something like: *"Ready when you are — just say go and I'll start on [specific task]."*

Keep the tone direct and energized. This is a fresh start, not a status report.

## Notes
- Staleness is measured in commits since `head`, not wall-clock. Date-based framing ("overnight",
  "last week") only when the frontmatter is absent, and then say it's by mtime
- If there are open PRs with pending review comments, surface them — they're likely blocking
- The handoff is evidence, not authority. Where it and `git`/`gh` disagree, the repo wins and the
  disagreement gets reported
- Don't re-read CLAUDE.md or project docs unless the handoff references something that requires it
- One session per worktree. Two sessions in the same directory share one working tree and one
  `HANDOFF.md`, so the second handoff replaces the first. That is what the store and worktrees
  exist to avoid
- The goal is: oriented and working within 60 seconds
