---
name: closeout
description: "Close out a finished worktree session and brief the parent session in the main checkout. Verifies from git, gh and the tracker (not from memory) the ticket, the session's PRs, what the worktree holds that is uncommitted, only here or not on the default branch, and the main checkout against its upstream; a check that cannot run makes the verdict 'not confirmed safe'. Writes a plain-text note for the parent (what shipped, tickets filed or changed, things noticed and not filed, decisions waiting, cleanup the parent owns, whether a reply is needed) and copies it to the clipboard, says whether the worktree is safe to delete and what would be lost if not, and when it is safe archives the session's handoff. Never removes the worktree without a yes. Use when the user says \"close out this worktree\", \"is this worktree safe to delete\" or \"wrap up this worktree\". NOT for work that continues in a later session (that is dv:handoff), NOT for merging a PR or deleting a merged branch."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.10.0"
---

# /closeout — close out a finished worktree session

Use this when a session in a linked git worktree has finished its work. The parent session, the
one in the main checkout, knows nothing about this session. Closeout checks what is true, writes
the parent a note it can act on, and says whether the worktree can be deleted.

A handoff (`/handoff`) is for work that continues. A closeout is for work that is finished. If
the work is not finished, say so and suggest `/handoff` instead.

<closeout_args>
#$ARGUMENTS
</closeout_args>

## Arguments

Anything in the block above is context: a ticket id, a PR number, or something the note must
mention. Bare invocation takes none. "I" and "me" in this skill mean the user.

## Rules

- **Verify, don't recall.** Every state in the reply and the note (ticket, PR, merge, clean tree)
  comes from a command run in this closeout, not from what the session remembers doing.
- **Unable to verify is not a pass.** If `gh` is missing, the fetch failed or the tracker can't be
  read, say which fact is unverified. The worktree is then "not confirmed safe", never "safe".
- **Nothing is removed without my yes.** This skill never merges a PR, never deletes a branch and
  never removes the worktree on its own.
- **Every block is self-contained.** Shell state does not survive between tool calls. The blocks
  take no positional parameters, and awk reads the whole line as `$(0)`: Claude Code replaces `$`
  followed by a digit everywhere in this file.

## Steps

### Step 1 — Verify the worktree, its PRs and the main checkout

```bash
# FAILS collects every check that did not run. It is only ever changed at the top level of
# this block, never inside a pipeline, so the change survives in both bash and zsh.
FAILS=""
NL='
'
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "(not a git repo — nothing to close out)"
else
  TOP=$(git rev-parse --show-toplevel); HEAD_SHA=$(git rev-parse HEAD)
  MAIN=$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)
  B=$(git branch --show-current)
  echo "=== Session ==="
  echo "worktree: $TOP"
  echo "branch: ${B:-(detached)} @ $(git rev-parse --short HEAD)"
  echo "main checkout: $MAIN"
  [ "$TOP" = "$MAIN" ] && echo "!! this IS the main checkout, not a linked worktree: never report it safe to delete"
  [ -n "$B" ] && echo "ticket id in the branch name (a hint, confirm it): $(printf '%s' "$B" | grep -o -i -E '[a-z]{2,10}-[0-9]+' | head -1 | tr '[:lower:]' '[:upper:]')"

  # No --prune: the remote-tracking refs are shared with every worktree and are not this skill's
  # to delete. Where a commit lives on origin is asked of origin directly (ls-remote) further down.
  FETCH=ok
  if git remote | grep -q -x origin; then git fetch --quiet origin 2>/dev/null || FETCH=FAILED; else FETCH=no-origin; fi
  echo "fetch from origin: $FETCH"
  [ "$FETCH" = ok ] || FAILS="$FAILS- fetch from origin ($FETCH): remote state is the last fetched copy$NL"
  DEFAULT=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
  [ -z "$DEFAULT" ] && git rev-parse -q --verify refs/heads/main >/dev/null && DEFAULT=main
  [ -z "$DEFAULT" ] && git rev-parse -q --verify refs/heads/master >/dev/null && DEFAULT=master
  BASE=""
  if [ -n "$DEFAULT" ]; then
    if git rev-parse -q --verify "refs/remotes/origin/$DEFAULT" >/dev/null; then BASE="origin/$DEFAULT"; else BASE="$DEFAULT"; fi
  fi
  echo "default branch: ${DEFAULT:-UNKNOWN}; comparing against: ${BASE:-NOTHING}"
  [ -n "$BASE" ] || FAILS="$FAILS- no default branch found: unmerged commits cannot be checked$NL"

  # One status call, every entry listed on its own line (-uall stops git collapsing a directory).
  if STATUS=$(git status --porcelain --ignored --untracked-files=all); then
    echo "=== Uncommitted or untracked (HANDOFF.md aside) ==="
    DIRTY=$(printf '%s\n' "$STATUS" | grep -v '^!! ' | grep -v '^.. HANDOFF\.md$' | grep .)
    if [ -n "$DIRTY" ]; then printf '%s\n' "$DIRTY"; else echo "(none)"; fi

    echo "=== Ignored entries (removing the worktree deletes them), by top-level path ==="
    IGN=$(printf '%s\n' "$STATUS" | sed -n 's/^!! //p' | grep -v -x 'HANDOFF\.md')
    if [ -z "$IGN" ]; then echo "(none)"
    elif [ "$TOP" = "$MAIN" ]; then printf '%s\n' "$IGN" | sed 's/^/  /'
    else
      # Each entry: same (identical in the main checkout), different, only-here, or
      # not-examined (not a regular file or symlink). Symlinks compare by target.
      printf '%s\n' "$IGN" | while IFS= read -r p; do
        a="$TOP/$p"; m="$MAIN/$p"
        if [ -L "$a" ]; then
          if [ -L "$m" ] && [ "$(readlink "$a")" = "$(readlink "$m")" ]; then k=same
          elif [ -e "$m" ] || [ -L "$m" ]; then k=different; else k=only-here; fi
        elif [ -f "$a" ]; then
          if [ -f "$m" ] && [ ! -L "$m" ]; then if cmp -s "$a" "$m"; then k=same; else k=different; fi
          elif [ -e "$m" ] || [ -L "$m" ]; then k=different; else k=only-here; fi
        else k=not-examined; fi
        printf '%s\t%s\n' "$k" "$p"
      done | awk -F '\t' '
        { top=$(2); if (index(top, "/")) top=substr(top, 1, index(top, "/")); n[top]++; c[top, $(1)]++
          if ($(1) != "same" && $(1) != "only-here" && shown < 10) { ex[++shown]=$(1) ": " $(2) } }
        END { for (t in n) printf "  %s  %d entries: %d same as the main checkout, %d only here, %d different, %d not examined\n",
                t, n[t], c[t,"same"], c[t,"only-here"], c[t,"different"], c[t,"not-examined"]
              for (i=1; i<=shown; i++) print "    " ex[i] }'
    fi
  else
    FAILS="$FAILS- git status in the worktree failed: uncommitted and ignored files unknown$NL"
  fi

  # State that lives in this worktree's own git dir and goes with it: an operation in progress,
  # per-worktree refs, a lock.
  echo "=== Worktree-private git state ==="
  WGD=$(git rev-parse --absolute-git-dir); PRIV=""
  for x in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    [ -e "$WGD/$x" ] && PRIV="$PRIV  in progress: $x$NL"
  done
  if WREFS=$(git for-each-ref --format='%(refname)' refs/worktree/); then
    [ -n "$WREFS" ] && PRIV="$PRIV$(printf '%s\n' "$WREFS" | sed 's/^/  per-worktree ref: /')$NL"
  else FAILS="$FAILS- listing per-worktree refs failed$NL"; fi
  [ -e "$WGD/locked" ] && PRIV="$PRIV  worktree is locked: $(cat "$WGD/locked" 2>/dev/null)$NL"
  if [ -n "$PRIV" ]; then printf '%s' "$PRIV"; else echo "(none)"; fi

  if [ -f "$TOP/.gitmodules" ]; then
    echo "=== Submodules ==="
    if SMST=$(git -C "$TOP" submodule status --recursive); then
      NINIT=$(printf '%s\n' "$SMST" | grep -c '^[^-]')
      echo "initialized submodules: $NINIT"
      [ "$NINIT" -gt 0 ] && echo "!! a plain worktree removal refuses a worktree with an initialized submodule (see Step 5)"
    else FAILS="$FAILS- git submodule status failed$NL"; fi
    echo "--- uncommitted changes, stashes, commits on no remote-tracking branch, per submodule:"
    # Each git call must succeed, or the foreach fails and the check is listed as not run.
    if SUB=$(git -C "$TOP" submodule foreach --quiet --recursive \
        'a=$(git status --porcelain) && b=$(git stash list) && c=$(git log --oneline --branches --not --remotes) || exit 1; o="$a$b$c"; [ -z "$o" ] || printf "== %s\n%s\n%s\n%s\n" "$sm_path" "$a" "$b" "$c"'); then
      if [ -n "$SUB" ]; then printf '%s\n' "$SUB" | grep .; else echo "(none)"; fi
    else FAILS="$FAILS- submodule check failed: work inside a submodule clone is unknown$NL"; fi
  fi

  echo "=== PRs with this branch as head (or, detached, containing this commit) ==="
  PRS=""; REPO=""; PRFAIL=""
  if command -v gh >/dev/null 2>&1; then REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null); fi
  if [ -z "$REPO" ]; then
    PRFAIL=1; FAILS="$FAILS- gh missing or no GitHub remote: PR and merge state unknown$NL"
  elif [ -n "$B" ]; then
    PRS=$(gh pr list --repo "$REPO" --head "$B" --state all --limit 1000 --json number,state,headRefOid,baseRefName,url,title \
      -q '.[]|[.number,.state,.headRefOid,.baseRefName,.url,.title]|@tsv' 2>/dev/null) || { PRFAIL=1; FAILS="$FAILS- gh pr list failed: PR state unknown$NL"; }
  else
    PRS=$(gh api --paginate "repos/$REPO/commits/$HEAD_SHA/pulls" \
      -q '.[]|[.number,(if .merged_at then "MERGED" else (.state|ascii_upcase) end),.head.sha,.base.ref,.html_url,.title]|@tsv' 2>/dev/null) || { PRFAIL=1; FAILS="$FAILS- PR lookup by commit failed: PR state unknown$NL"; }
  fi
  TAB=$(printf '\t')
  if [ -n "$PRFAIL" ]; then echo "(lookup did not run — see the checks that did not run)"
  elif [ -n "$PRS" ]; then printf '%s\n' "$PRS" | while IFS="$TAB" read -r n st h base url title; do echo "  #$n $st (into $base) $url — $title"; done
  else echo "(none found for ${B:-this commit})"; fi

  if [ -n "$BASE" ]; then
    echo "=== Commits here that are not on $BASE ==="
    # A squash merge leaves the branch's commits off the default branch, so a merged PR's head
    # counts as merged work too, when that PR went into the default branch.
    NOTS="^$BASE"; UPS="$BASE"
    if [ -n "$PRS" ]; then
      HEADS=$(printf '%s\n' "$PRS" | while IFS="$TAB" read -r n st h base url title; do
        [ "$st" = "MERGED" ] && [ "$base" = "$DEFAULT" ] || continue
        git cat-file -e "$h^{commit}" 2>/dev/null || git fetch --quiet origin "refs/pull/$n/head" 2>/dev/null
        if git cat-file -e "$h^{commit}" 2>/dev/null; then echo "$h"; else echo "(head of merged PR #$n could not be fetched — its commits count as unmerged)" >&2; fi
      done)
      if [ -n "$HEADS" ]; then
        NOTS=$(printf '%s\n%s\n' "$NOTS" "$(printf '%s\n' "$HEADS" | sed 's/^/^/')")
        UPS=$(printf '%s\n%s\n' "$UPS" "$HEADS")
      fi
    fi
    # Drop a commit whose patch is already in the default branch or a merged head (a rebase on
    # GitHub rewrites the shas). git cherry never matches a merge commit, so those stay listed.
    UNMERGED=""; CHOK=1
    if CAND=$(printf '%s\n' "$NOTS" | git rev-list HEAD --stdin); then
      SAME=""
      while IFS= read -r u; do
        if OUT=$(git cherry "$u" HEAD); then SAME="$SAME$(printf '%s\n' "$OUT" | sed -n 's/^- //p')$NL"; else CHOK=""; fi
      done <<UPS_END
$UPS
UPS_END
      [ -n "$CHOK" ] || FAILS="$FAILS- git cherry failed: commits already merged by patch may be listed as unmerged$NL"
      UNMERGED=$(printf '%s\n' "$CAND" | grep . | grep -v -x -F -e "$(printf '%s' "$SAME" | grep . || echo NONE)")
      if [ -z "$UNMERGED" ]; then echo "(none)"; else
        # Ask origin which branch tips exist now, then test each commit against those tips.
        RH=""; RHOK=""
        if [ "$FETCH" != no-origin ] && RH=$(git ls-remote --heads origin | cut -f1); then RHOK=1
        else FAILS="$FAILS- git ls-remote origin failed: whether each unmerged commit is on origin is unknown$NL"; fi
        printf '%s\n' "$UNMERGED" | while IFS= read -r c; do
          where="origin unknown"
          if [ -n "$RHOK" ]; then
            where="NOT on any origin branch"
            for h in $(printf '%s\n' "$RH"); do
              if ! git cat-file -e "$h^{commit}" 2>/dev/null; then where="origin has a tip not fetched here: unknown"
              elif git merge-base --is-ancestor "$c" "$h"; then where="on an origin branch"; break; fi
            done
          fi
          echo "  $(git log -1 --format='%h %s' "$c") [$where]"
        done
      fi
      echo "this worktree is $(git rev-list --count "HEAD..$BASE") commit(s) behind $BASE"
    else
      FAILS="$FAILS- git rev-list failed: commits not on the default branch are unknown$NL"
    fi
  fi
  if SL=$(git stash list); then
    ST=$(printf '%s\n' "$SL" | grep -F -e " on ${B:-(no branch)}:" -e " On ${B:-(no branch)}:")
    [ -n "$ST" ] && { echo "=== Stashes made on ${B:-a detached HEAD} (they outlive the worktree, but nobody will look for them) ==="; printf '%s\n' "$ST"; }
  else FAILS="$FAILS- git stash list failed$NL"; fi

  echo "=== Main checkout vs its own upstream ==="
  MB=$(git -C "$MAIN" branch --show-current)
  if MS=$(git -C "$MAIN" status --porcelain); then
    echo "branch: ${MB:-(detached)}; uncommitted entries: $(printf '%s' "$MS" | grep -c .)"
  else FAILS="$FAILS- git status in the main checkout failed$NL"; fi
  MR=""; [ -n "$MB" ] && MR=$(git -C "$MAIN" config "branch.$MB.remote")
  if [ -z "$MR" ] || [ "$MR" = "." ]; then
    FAILS="$FAILS- the main checkout's branch has no remote upstream: level with the remote is unknown$NL"
  else
    MFETCH=ok
    if [ "$MR" != origin ] || [ "$FETCH" != ok ]; then git -C "$MAIN" fetch --quiet "$MR" 2>/dev/null || MFETCH=FAILED; fi
    if [ "$MFETCH" = ok ] && UP=$(git -C "$MAIN" rev-parse --abbrev-ref --symbolic-full-name '@{u}') && LR=$(git -C "$MAIN" rev-list --left-right --count "$UP...HEAD"); then
      echo "upstream: $UP (remote $MR, fetched now); behind it: $(printf '%s' "$LR" | cut -f1); ahead of it: $(printf '%s' "$LR" | cut -f2)"
    else
      FAILS="$FAILS- the main checkout's upstream on remote $MR could not be fetched or counted: level with the remote is unknown$NL"
    fi
  fi

  echo "=== Checks that did not run ==="
  if [ -n "$FAILS" ]; then printf '%s' "$FAILS"; else echo "(none — every check ran)"; fi
fi
```

Outside a git repo, stop here and say there is nothing to close out.

Then complete the picture from the systems, not from memory:

- **Other PRs.** The block finds only PRs whose head is this branch (or, on a detached HEAD, PRs
  containing this commit). A session may have opened others from another branch, such as a
  release PR. List your recent PRs and pick out this session's:
  `gh pr list --author @me --state all --limit 30 --json number,title,headRefName,state,createdAt,url`.
  Check each one with `gh pr view <n> --json number,state,mergedAt,baseRefName,url`. The note
  names the PRs you checked; it does not claim the list is complete when you could not tell.
- **The ticket.** Find its id from the arguments, the branch name, the PR titles or the session.
  Read its state from the tracker now, with whatever access this session has (for Linear, the
  `get_issue` tool or a CLI). Read its acceptance checklist too and note each line that is not
  yet true. If the tracker can't be read, the ticket state is unverified: say so.
- **Releases and tags** the session made, if any: `gh release view <tag>` or `git ls-remote --tags origin <tag>`.

### Step 2 — Decide whether the worktree is safe to delete

**Safe to delete** only when all of these hold:

- This is a linked worktree, not the main checkout.
- Nothing is uncommitted or untracked, `HANDOFF.md` aside.
- No commit is listed under "Commits here that are not on" the default branch.
- No ignored entry holds something that exists only here. Entries the same as the main
  checkout's, and rebuildable output (a virtualenv, `node_modules`, caches), lose nothing. Any
  other "only here" entry, a "different" one (an edited `.env`) or a "not examined" one is a loss
  until you have looked at it: name it.
- "Worktree-private git state" says none: an operation in progress or a per-worktree ref goes
  with the worktree.
- No submodule was listed under a `==` header (when the repo has submodules).
- No stash is listed as made on this branch or detached HEAD. A stash survives the removal but
  nobody will look for it, so name it.
- "Checks that did not run" says none. Any line there makes the verdict not confirmed safe.

Safe to delete is about data. Whether a given removal command can do it is separate: see the
initialized-submodule case in Step 5.

Otherwise it is **not safe to delete**, and the reply names exactly what would be lost: each
file, and each commit by short sha and subject. Say where a commit still lives. On a named branch
the commit stays on that branch after the worktree goes, and on the remote if it says pushed; on a
detached HEAD nothing refers to it once the worktree is gone. When a check could not run, the
verdict is **not confirmed safe**, with the check that is missing.

An open or unmerged PR, or a ticket that is not in a finished state, does not by itself put files
at risk, but the work is not finished. Say so first, and suggest `/handoff` if it will continue.

### Step 3 — Write the parent note and copy it

Write the note as plain text, no markdown, for a reader who was not in this session. Include only
what the parent needs to act on or to avoid redoing. Every state in it comes from Steps 1 and 2.
Use these headings in this order, and write "none" under one with nothing to say:

```
CLOSEOUT NOTE from <branch or "detached"> at <worktree path>, <date and time with zone>
Worktree: <safe to delete | NOT safe to delete: what would be lost | not confirmed safe: what is unverified>

WHAT SHIPPED
<ticket id, title and state now; each PR with number, merge state and link; releases and tags>

TICKETS FILED OR CHANGED
<id, what changed>

NOTICED, NOT FILED
<things seen along the way that nobody has written down anywhere else>

WAITING ON <the user's name>
<decisions only they can make, each with a recommendation>

CLEANUP THE PARENT OWNS
<pull the main checkout if it is behind; remove this worktree with the command from Step 5; anything else>

REPLY NEEDED: <no | yes: the question>
```

Leave out secrets, credentials and tokens. Then save the note and copy it, with the note's text
in place of the placeholder line:

```bash
if git rev-parse --git-dir >/dev/null 2>&1; then
  GCD=$(git rev-parse --git-common-dir) && D="$(cd "$GCD" && pwd -P)/closeouts"
  B=$(git branch --show-current)
  SLUG=$(printf '%s' "${B:-detached-$(git rev-parse HEAD 2>/dev/null)}" | sed -e 's/%/%25/g' -e 's#/#%2F#g')
  BASEN="$D/$SLUG.$(date -u +%Y%m%dT%H%M%SZ)"; NOTE="$BASEN.txt"; n=0
  while [ -e "$NOTE" ]; do n=$((n+1)); NOTE="$BASEN-$n.txt"; done
  # set -C refuses to overwrite a file that appeared after the check above.
  if mkdir -p "$D" && ( set -C; cat > "$NOTE" ) <<'CLOSEOUT_NOTE_END'
[the note]
CLOSEOUT_NOTE_END
  then
    echo "note saved: $NOTE"
    if command -v pbcopy >/dev/null 2>&1; then pbcopy < "$NOTE" && echo "copied to the clipboard (pbcopy)"
    elif command -v wl-copy >/dev/null 2>&1; then wl-copy < "$NOTE" && echo "copied to the clipboard (wl-copy)"
    elif command -v xclip >/dev/null 2>&1; then xclip -selection clipboard < "$NOTE" && echo "copied to the clipboard (xclip)"
    elif command -v xsel >/dev/null 2>&1; then xsel --clipboard --input < "$NOTE" && echo "copied to the clipboard (xsel)"
    elif command -v clip.exe >/dev/null 2>&1; then clip.exe < "$NOTE" && echo "copied to the clipboard (clip.exe)"
    else echo "(no clipboard command found — note NOT copied)"; fi
  else
    echo "!! the note could NOT be saved to $NOTE — nothing was copied; paste it from the reply"
  fi
fi
```

The saved copy lives in the repo's shared git directory (`<git-common-dir>/closeouts/`), so it
survives the worktree's removal and the parent session can read it by path. The clipboard is the
one on the machine this session runs on, which may not be the machine I am typing at. If the copy
failed or no command was found, say so.

### Step 4 — Archive the handoff (only when safe to delete)

Run this only when Step 2 said safe to delete. It moves this session's handoff out of the shared
store into `handoffs/_done/`, the way `/pickup` does for a branch whose PR merged, so `/pickup` in
other worktrees stops listing a closed session. It also covers a detached worktree, which
`/pickup` never archives: the handoff is found by the worktree path it records, and archived
under the name `/pickup` looks for. Nothing is deleted and no earlier archive is overwritten.

```bash
if git rev-parse --git-dir >/dev/null 2>&1; then
  TOP=$(git rev-parse --show-toplevel)
  MAIN=$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)
  GCD=$(git rev-parse --git-common-dir) && STORE="$(cd "$GCD" && pwd -P)/handoffs"
  B=$(git branch --show-current)
  SLUG=$(printf '%s' "${B:-detached-$(git rev-parse HEAD 2>/dev/null)}" | sed -e 's/%/%25/g' -e 's#/#%2F#g')
  if [ "$TOP" = "$MAIN" ]; then
    echo "(this is the main checkout — nothing archived)"
  elif [ -n "$(git status --porcelain --untracked-files=all | grep -v '^.. HANDOFF\.md$')" ]; then
    echo "!! uncommitted changes — not safe to delete, nothing archived"
  else
    TS=$(date -u +%Y%m%dT%H%M%SZ)
    { find "$STORE" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort; [ -f "$TOP/HANDOFF.md" ] && echo "$TOP/HANDOFF.md"; } |
    while IFS= read -r f; do
      fm=$(sed -n '2,/^---$/{/^---$/!p;}' "$f")
      fb=$(printf '%s\n' "$fm" | sed -n 's/^branch: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' | head -1)
      fw=$(printf '%s\n' "$fm" | sed -n 's/^worktree: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' | head -1)
      mine=""
      [ "$f" = "$STORE/$SLUG.md" ] && mine=1
      [ "$fw" = "$TOP" ] && [ "$fb" = "${B:-(detached)}" ] && mine=1
      [ -n "$mine" ] || continue
      # The store file is always moved, so the active slot is cleared even on a rerun. HANDOFF.md is
      # copied only when no archived file already matches it byte for byte (it mirrors the store copy).
      if [ "$f" = "$TOP/HANDOFF.md" ]; then
        dup=$(find "$STORE/_done" -maxdepth 1 -type f -name "$SLUG.*.md" 2>/dev/null | while IFS= read -r a; do cmp -s "$a" "$f" && echo 1; done)
        [ -n "$dup" ] && continue
      fi
      n=0; dest="$STORE/_done/$SLUG.$TS.md"
      while [ -e "$dest" ]; do n=$((n+1)); dest="$STORE/_done/$SLUG.$TS-$n.md"; done
      mkdir -p "$STORE/_done" || continue
      if [ "$f" = "$TOP/HANDOFF.md" ]; then cp "$f" "$dest" && echo "archived a copy of HANDOFF.md: $dest"
      else mv "$f" "$dest" && echo "archived: $f -> $dest"; fi
    done
    find "$STORE/_done" -maxdepth 1 -type f -name "$SLUG.*.md" 2>/dev/null | grep -q . || echo "(no handoff for this session — nothing to archive)"
  fi
fi
```

The `HANDOFF.md` in the worktree is left in place; it goes with the worktree. When Step 2 did not
say safe, skip this step and say the handoff was left where it is.

### Step 5 — Reply, and leave the removal to me

Name the removal command for the tool that made the worktree, to be run from the main checkout
after this session has ended. Do not run it.

- A worktree under `<main checkout>/.claude/worktrees/<topic>`, where `wt` is on PATH:
  `wt done <topic>`.
- Otherwise: `git -C <main checkout> worktree remove <worktree path>`. It keeps the branch;
  deleting a merged branch is a separate procedure and not this skill's.
- If the optional section below applies, it replaces this command with its own offer.
- **Initialized submodules.** If Step 1 printed "initialized submodules" above 0, `wt done`,
  `git worktree remove` and a plain `orca worktree rm` all refuse this worktree. Say so, and point
  to the guarded procedure instead of a plain command: `dv:orca-setup` Step 5 (`orca worktree rm
  --force`, after its submodule checks) or dotfiles `docs/agents/code-review.md`, "Worktrees with
  submodules are detached, not removed". Do not offer `--force` yourself.

When the worktree is not safe, or not confirmed safe, name no removal command and offer none.

Reply in this order, short:

1. One line: safe to delete, not safe to delete (and what would be lost), or not confirmed safe
   (and which check is missing).
2. **Needs you:** decisions waiting on me, and anything still owed on the ticket that this
   session could not close. Leave it out if there is none.
3. The verified facts, one line each: the ticket and its state; each PR and its merge state; what
   the worktree holds beyond the default branch; the main checkout against its remote (behind,
   ahead, dirty); where the handoff went, or that it was left; where the note was saved and
   whether it reached the clipboard; the removal command, when safe.
4. The line the optional section below tells you to add, if any.
5. The note itself in a code block, so I can copy it if the clipboard missed.

## Optional: Orca delivery and removal

Use this section only when the worktree lives in Orca and its CLI is on PATH. Everything above
works without it. Resolve the CLI and look for the parent's agent terminal:

```bash
C="${ORCA_CLI_COMMAND:-}"
if [ -z "$C" ]; then if [ "$(uname -s)" = Linux ]; then C=orca-ide; else C=orca; fi; fi
if ! command -v "$C" >/dev/null 2>&1; then
  echo "Orca steps skipped: no Orca CLI on PATH"
elif git rev-parse --git-dir >/dev/null 2>&1; then
  MAIN=$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)
  echo "Orca CLI: $C"
  "$C" terminal list --worktree "path:$MAIN" --json
fi
```

If the block printed "Orca steps skipped", add the line "Orca steps skipped: no Orca CLI on PATH"
to the reply and do nothing else in this section. (On Linux a bare `orca` is usually the GNOME
screen reader, which is why the block does not try it there.)

**Deliver the note.** A parent terminal qualifies only when its entry has an `agentIdentity`
field: that marks a running agent. A terminal without it is a plain shell, and a note sent there
would be run as commands, so never send to one.

- Exactly one qualifying terminal: send the saved note from Step 3, once, with the CLI path the
  block printed in place of `<orca CLI>`, kept inside the quotes (no variable from that block survives to this call):
  `"<orca CLI>" terminal send --terminal <handle> --text "$(cat "<note path>")" --enter --wait-submit 20 --json`
  Report what the result says (`input_accepted`, and whether a turn was seen to start), not
  "delivered". Do not resend on a timeout. After a transport error, reissue the same command with
  the `--retry-request` id the error reports.
- More than one: ask me which, as a plain question, before sending.
- None: say the parent has no agent terminal open, and that the note is on the clipboard and at
  its saved path. A parent that runs as an Orca chat is not a terminal and cannot be reached this
  way.

What a test showed (VIL-836, 2026-11-18, from a worktree to the main checkout): the text arrived
in the main checkout's terminal. Not tested: whether a parent agent acts on a note, and whether
one that is mid-turn reads it. So say in the reply that the note was sent and that the parent may
still need it pasted.

**Offer the removal.** Only when Step 2 said safe to delete, end the reply with one question:
remove this worktree now? Run the removal only after my yes, in a later turn, as the last action
of the session, because it stops this worktree's sessions:

`"<orca CLI>" worktree rm --worktree "path:<worktree path>" --json`

Use the `path:` selector (`current` and `active` are refused). Add no `--force` and no
`--delete-branch`: if the removal is refused, report the refusal and stop. With an initialized
submodule, do not offer this command at all (Step 5). Without my yes, name
this command in the reply instead and leave it to me.

## Notes

- Closeout does not replace `/handoff`. If anything continues after this session, write a handoff
  too, before Step 4 moves it.
- The verdict is about what the worktree holds, not about whether the ticket is finished. Both
  are in the reply, and neither stands in for the other.
- When the handoff or the session's memory disagrees with what the commands returned, the
  commands win and the difference goes in the note.
