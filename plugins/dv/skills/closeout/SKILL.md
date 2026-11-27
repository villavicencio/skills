---
name: closeout
description: "Close out a finished worktree session and brief the parent session in the main checkout. Verifies from git, gh and the tracker (not from memory) the ticket, the session's PRs, what the worktree holds that is uncommitted, only here or not on the default branch, and the main checkout against its upstream; a check that cannot run makes the verdict 'not confirmed safe'. Archives the session's handoff when safe, then writes a plain-text note for the parent (what shipped, tickets filed or changed, things noticed and not filed, decisions waiting, cleanup, whether to reply), attempts to copy it to the clipboard and sends it to the parent once it can reach and verify it, and says whether the worktree is safe to delete and what would be lost if not. Never removes the worktree without a yes. Use when the user says \"close out this worktree\", \"is this worktree safe to delete\" or \"wrap up this worktree\". NOT for work that continues in a later session (that is dv:handoff), NOT for merging a PR or deleting a merged branch."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.46.0"
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
- **With a Head, ask me nothing.** When this project names a department Head, the section "With
  a Head" (below) changes the steps it names, and where it and a step differ, it wins. With no
  Head it does not apply, and every step runs as written.
- **Every block is self-contained.** Shell state does not survive between tool calls. The blocks
  take no positional parameters, and awk reads the whole line as `$(0)`: Claude Code replaces `$`
  followed by a digit everywhere in this file.

## Steps

Run the steps in this order: Step 1, Step 2, Step 4, Step 3, Step 5. They keep their numbers,
and the sections below are in that run order. Step 4 (the handoff archive) runs before Step 3
writes and saves the note, so the note is written once, after the archive, and its Worktree
verdict and CLEANUP carry this turn's Step 4 result. When Step 4 is skipped (Step 2 did not say
safe to delete, or the losses it lists wait on my yes), Step 3 follows Step 2 and the note
records that the archive has not run. Run the first block under "Optional: Orca delivery and
removal" before Step 3 as well (it only reads, and says when there is no Orca CLI): the removal
command Step 5 picks, which a cleared note names in CLEANUP, depends on it. Writing the note
again later (after my yes, after a recheck that found a change, or before the note's send) runs
Steps 1 and 2 again first, then Step 4 when its gate allows it, in the same order.

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
  # Each read is checked: one that fails makes the verdict "not confirmed safe".
  TOP=$(git rev-parse --show-toplevel) && [ -n "$TOP" ] || FAILS="$FAILS- git rev-parse --show-toplevel failed: the worktree's path is unknown$NL"
  HEAD_SHA=$(git rev-parse HEAD) && [ -n "$HEAD_SHA" ] || FAILS="$FAILS- git rev-parse HEAD failed: this worktree's commit is unknown$NL"
  if WTL=$(git worktree list --porcelain) && MAIN=$(printf '%s\n' "$WTL" | sed -n '/^worktree /{s/^worktree //p;q;}') && [ -n "$MAIN" ]; then :
  else MAIN=""; FAILS="$FAILS- reading the main checkout's path failed: every comparison with the main checkout is unknown$NL"; fi
  BOK=1; B=$(git branch --show-current) || { BOK=""; FAILS="$FAILS- git branch --show-current failed: the branch is unknown$NL"; }
  echo "=== Session ==="
  echo "worktree: ${TOP:-(unknown)}"
  if [ -n "$BOK" ]; then echo "branch: ${B:-(detached)} @ $(git rev-parse --short HEAD)"; else echo "branch: (unknown)"; fi
  echo "main checkout: ${MAIN:-(unknown)}"
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

    echo "=== Ignored entries and nested git repos (removing the worktree deletes them), by build-output name, then by top-level path ==="
    # A second status call with -z, read from a temp file: its paths arrive unquoted and
    # NUL-terminated, so a name with a space, tab, quote or non-ASCII character is compared and
    # matched as it is (the call above quotes such names). A newline in a name is shown as "?".
    IGNF=$(mktemp 2>/dev/null) || IGNF=""
    if [ -n "$IGNF" ] && git status --porcelain -z --ignored --untracked-files=all > "$IGNF"; then
      # Each entry: same (identical in the main checkout), different, only-here, nested-repo (a
      # directory holding a .git file or directory, or both objects/ and refs/: a git repository, which can hold unpushed
      # commits), or not-examined (anything else that is not a regular file or symlink).
      # Symlinks compare by target. In the main checkout itself entries are listed, not compared.
      # Build output: an entry inside a directory named .venv, venv, node_modules, __pycache__,
      # .pytest_cache, .mypy_cache or .ruff_cache, matched as a whole directory name at any depth
      # (myvenv/ and venv_notes/ are not build output, nor is a file named venv). An entry counts
      # once, under the outermost such directory on its path. Build output is grouped one line
      # per name, with its entry count and how many directories of that name hold the entries;
      # everything else is grouped by top-level path, and only it feeds the examples list. A
      # nested-repo entry is never build output: it goes on its top-level line even under a
      # build-output name, and every one is listed by path (the 10-example cap does not apply).
      # A repo git cannot open (a .git file pointing nowhere, a .git directory without HEAD) is
      # walked into and its files listed one by one, so every entry is also checked for a .git
      # in each directory above it, up to the worktree; the repo is then listed once, by path.
      # Git lists nothing at all for a repo it cannot open that holds only its .git folder,
      # ignored or not, so a find also looks for every .git (file or folder) below the worktree's
      # top, as well as candidate objects entries whose parent also holds refs/ (including
      # unopenable bare repos). Checking only those candidates avoids a process per directory.
      # Each one is listed as a nested repo, except an initialized submodule's (those have
      # their own checks below); one git already listed is listed once.
      # Each build-output line ends with a fingerprint: the first 12 hex digits of a hash over the
      # line's entries, one line each in the order git lists them (sorted by path, byte by byte):
      # the entry's path with the hash of its regular file's contents or of its symlink's target
      # (as readlink prints it, into a temp file; the link is never followed), or with neither for
      # an entry not examined. One xargs run of git hash-object --no-filters hashes them all. A
      # path with a newline, shown with "?", also adds all its bytes in hex (od -v, so repeated
      # rows are not shortened to "*"), so it never matches the same path written with "?". A file edited, replaced or renamed in place, or a symlink
      # pointed elsewhere, changes it even when every count stays the same; file modes and times
      # are not part of it. Every fingerprint is worked out before any line is printed: if anything
      # cannot be hashed, they all read "unknown" and the check is listed as not run.
      # The case patterns open with "(" (bash 3.2 needs that inside a command substitution).
      BOL=".venv/venv/node_modules/__pycache__/.pytest_cache/.mypy_cache/.ruff_cache"
      NRF=""; SUBP=""
      if [ "$TOP" != "$MAIN" ]; then
        if NRF=$(mktemp 2>/dev/null) && find "$TOP" -mindepth 1 \( -name .git -prune -print0 -o -name objects -print0 \) > "$NRF"; then :
        else FAILS="$FAILS- finding nested repositories below the worktree failed: a nested repo git does not list may be missed$NL"; fi
        if [ -f "$TOP/.gitmodules" ]; then
          SUBP=$(git -C "$TOP" submodule foreach --quiet --recursive 'printf "%s\n" "$displaypath"') \
            || FAILS="$FAILS- listing submodule paths failed: a submodule may be listed as a nested repo$NL"
        fi
      fi
      # One record per entry: kind, tab, what the fingerprint takes from it, tab, path. In build
      # output a regular file is marked F and a symlink L, and the file, or the temp file holding
      # the link's target, goes NUL-terminated to fd 3 in the same order, so the batch's hashes
      # line up with the F and L records. The "end" record is written only when the loop over
      # git's list ran, so a redirection that failed cannot pass as no entries.
      FPD=$(mktemp -d "${TMPDIR:-/tmp}/closeout-fp.XXXXXX" 2>/dev/null) || FPD=""
      ARC=1; FPOK=1; SLN=0
      if [ -n "$FPD" ]; then
        { { while IFS= read -r -d '' r; do
          case "$r" in ('!! '*) ;; (*) continue ;; esac
          p=${r#'!! '}; [ "$p" = HANDOFF.md ] && continue
          a="$TOP/$p"; m="$MAIN/$p"; t=-; bo=""
          if [ "$TOP" = "$MAIN" ]; then k=listed
          elif [ -L "$a" ]; then
            t=l
            if [ -L "$m" ] && [ "$(readlink "$a")" = "$(readlink "$m")" ]; then k=same
            elif [ -e "$m" ] || [ -L "$m" ]; then k=different; else k=only-here; fi
          elif [ -f "$a" ]; then
            t=f
            if [ -f "$m" ] && [ ! -L "$m" ]; then if cmp -s "$a" "$m"; then k=same; else k=different; fi
            elif [ -e "$m" ] || [ -L "$m" ]; then k=different; else k=only-here; fi
          elif [ -d "$a" ] && { [ -e "$a/.git" ] || [ -L "$a/.git" ] || { [ -d "$a/objects" ] && [ -d "$a/refs" ]; }; }; then k=nested-repo
          else k=not-examined; fi
          if [ "$k" != listed ] && [ "$k" != nested-repo ]; then
            d=${p%/}
            while :; do
              case "$d" in (*/*) d=${d%/*} ;; (*) break ;; esac
              if [ -e "$TOP/$d/.git" ] || [ -L "$TOP/$d/.git" ] || { [ -d "$TOP/$d/objects" ] && [ -d "$TOP/$d/refs" ]; }; then k=nested-repo; p="$d/"; break; fi
              case "/$BOL/" in (*"/${d##*/}/"*) bo=1 ;; esac
            done
          fi
          if [ -n "$bo" ] && [ "$k" != nested-repo ]; then
            case "$t" in
              (f) printf '%s\0' "$a" >&3; t=F ;;
              (l) SLN=$((SLN + 1))
                if readlink "$a" > "$FPD/link$SLN"; then printf '%s\0' "$FPD/link$SLN" >&3; t=L; else t=-; fi ;;
            esac
          fi
          case "$p" in (*"$NL"*) t="$t $(printf '%s' "$p" | od -v -An -tx1 | tr -d ' \n')"; p=$(printf '%s' "$p" | tr '\n' '?') ;; esac
          printf '%s\t%s\t%s\n' "$k" "$t" "$p"
        done; printf 'end\t-\t-\n'; } < "$IGNF" 3> "$FPD/paths"
        if [ -n "$NRF" ]; then while IFS= read -r -d '' g; do
          p=${g#"$TOP"/}
          case "$p" in
            (.git|objects) continue ;;
            (*/.git) p=${p%/.git} ;;
            (*/objects) [ -d "$g" ] && [ -d "${g%/objects}/refs" ] || continue; p=${p%/objects} ;;
          esac
          case "$p" in (*"$NL"*) ;; (*) [ -n "$SUBP" ] && printf '%s\n' "$SUBP" | grep -q -x -F -e "$p" && continue ;; esac
          case "$p" in (*"$NL"*) p=$(printf '%s' "$p" | tr '\n' '?') ;; esac
          printf 'nested-repo\t-\t%s/\n' "$p"
        done < "$NRF"; fi; } > "$FPD/recs"
        : > "$FPD/hashes"
        if [ -s "$FPD/paths" ]; then xargs -0 git hash-object --no-filters -- < "$FPD/paths" > "$FPD/hashes" || FPOK=""; fi
        # awk exits 2 when the loop did not run, and 3 when it printed the listing but a
        # fingerprint is unknown. LC_ALL=C keeps it reading bytes, so the fingerprint does not
        # depend on the locale.
        IGNOUT=$(BOL="$BOL" FPD="$FPD" FPOK="$FPOK" LC_ALL=C awk '
        BEGIN { nb=split(ENVIRON["BOL"], bn, "/")
                for (i=1; i<=nb; i++) { isb[bn[i]]=1; gi[bn[i]]=i }
                fpd=ENVIRON["FPD"]; hs=fpd "/hashes"; if (ENVIRON["FPOK"] == "") fpbad=1 }
        # The kind and the fingerprint part come before the first two tabs; the path is all of the
        # rest, tabs included.
        { j=index($(0), "\t"); k=substr($(0), 1, j - 1); rest=substr($(0), j + 1)
          j=index(rest, "\t"); t=substr(rest, 1, j - 1); path=substr(rest, j + 1)
          if (k == "end") { ended=1; next }
          nrec++
          tc=substr(t, 1, 1)
          if (tc == "F" || tc == "L") { h=""; if ((getline h < hs) <= 0 || length(h) < 40 || h ~ /[^0-9a-f]/) fpbad=1
            t=(tc == "F" ? "f " : "l ") h substr(t, 2) }
          if (k == "listed") { print "  " path; next }
          if (k == "nested-repo") { if (path in nr_seen) next; nr_seen[path]=1 }
          np=split(path, part, "/"); g=""; dir=""
          # Every component but the last is a directory; the last is the entry itself.
          for (i=1; i<np; i++) { dir=dir part[i] "/"; if (part[i] in isb) { g=part[i]; break } }
          if (g != "" && k != "nested-repo") { bn_n[g]++; bn_c[g, k]++; if (!((g, dir) in seen)) { seen[g, dir]=1; bn_d[g]++ }
            # A file or symlink here that the loop did not hash means the two build-output tests
            # disagree, or its link could not be read; a hex name part must be there in full.
            if (k == "not-examined") { if (t !~ /^-( [0-9a-f]+)?$/) fpbad=1 }
            else if (t !~ /^[fl] [0-9a-f]+( [0-9a-f]+)?$/) fpbad=1
            print t "\t" path > (fpd "/" gi[g]); next }
          top=path; if (index(top, "/")) top=substr(top, 1, index(top, "/")); n[top]++; c[top, k]++
          if (k == "nested-repo") ex[++shown]=k ": " path
          else if (k != "same" && k != "only-here" && capped < 10) { capped++; ex[++shown]=k ": " path } }
        END { if (!ended) exit 2
              if (!nrec) print "(none)"
              if ((getline h < hs) > 0) fpbad=1
              for (i=1; i<=nb; i++) { g=bn[i]; if (!(g in bn_n) || fpbad) continue
                close(fpd "/" i); fp=""; cmd="git hash-object --stdin < \"$FPD/" i "\""
                if ((cmd | getline fp) <= 0 || length(fp) < 40 || fp ~ /[^0-9a-f]/) fpbad=1
                else fps[g]=substr(fp, 1, 12)
                close(cmd) }
              for (i=1; i<=nb; i++) { g=bn[i]; if (!(g in bn_n)) continue
                printf "  %s/ (any depth): %d entr%s in %d director%s: %d same as the main checkout, %d only here, %d different, %d not examined; fingerprint %s\n",
                  g, bn_n[g], (bn_n[g] == 1 ? "y" : "ies"), bn_d[g], (bn_d[g] == 1 ? "y" : "ies"),
                  bn_c[g,"same"], bn_c[g,"only-here"], bn_c[g,"different"], bn_c[g,"not-examined"], (fpbad ? "unknown" : fps[g]) }
              for (t in n) printf "  %s  %d entries: %d same as the main checkout, %d only here, %d different, %d not examined, %d nested git repos\n",
                t, n[t], c[t,"same"], c[t,"only-here"], c[t,"different"], c[t,"not-examined"], c[t,"nested-repo"]
              for (i=1; i<=shown; i++) print "    " ex[i]
              exit (fpbad ? 3 : 0) }' < "$FPD/recs"); ARC=$?
      fi
      if [ "$ARC" = 0 ] || [ "$ARC" = 3 ]; then
        printf '%s\n' "$IGNOUT"
        [ "$ARC" = 3 ] && FAILS="$FAILS- fingerprinting the build output failed: a fingerprint is unknown, so a file edited in place may go unnoticed$NL"
      else
        FAILS="$FAILS- grouping the ignored entries failed: ignored files unknown$NL"
        echo "(not listed — see the checks that did not run)"
      fi
      # Remove only this run's own folder, named as mktemp made it above.
      if [ -n "$FPD" ]; then
        case "${FPD##*/}" in
          (closeout-fp.??????) command rm -rf -- "$FPD" || echo "!! could not remove the temp folder $FPD" ;;
          (*) echo "!! left the temp folder $FPD: it is not named as this run made it" ;;
        esac
      fi
    else
      FAILS="$FAILS- git status -z for the ignored entries failed: ignored files unknown$NL"
      echo "(not listed — see the checks that did not run)"
    fi
    [ -n "$IGNF" ] && rm -f "$IGNF"
    [ -n "$NRF" ] && rm -f "$NRF"
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
  [ -s "$WGD/config.worktree" ] && PRIV="$PRIV  per-worktree config: $WGD/config.worktree$NL"
  if [ -n "$PRIV" ]; then printf '%s' "$PRIV"; else echo "(none)"; fi

  # This worktree's HEAD reflog and ORIG_HEAD go with it. Commits reachable from them and from no
  # ref (a commit reset or amended away) lose their last recovery path when the worktree goes.
  echo "=== Commits reachable only from this worktree's HEAD reflog or ORIG_HEAD ==="
  RL=""; RLOK=1
  if git reflog exists HEAD; then RL=$(git rev-list --walk-reflogs HEAD) || RLOK=""; fi
  OH=$(git rev-parse -q --verify ORIG_HEAD)
  # Everything reachable from the reflog entries or ORIG_HEAD that no ref (or any worktree's HEAD) reaches.
  if [ -n "$RLOK" ] && ONLY=$(printf '%s\n%s\n' "$RL" "$OH" | grep . | sort -u | git rev-list --stdin --not --all); then
    ONLY=$(printf '%s\n' "$ONLY" | grep . | sort -u)
    if [ -n "$ONLY" ]; then
      NO=$(printf '%s\n' "$ONLY" | grep -c .)
      echo "$NO commit(s); list id $(printf '%s\n' "$ONLY" | git hash-object --stdin | cut -c1-12)$( [ "$NO" -gt 50 ] && echo "; the first 50:")"
      printf '%s\n' "$ONLY" | head -50 | while IFS= read -r c; do echo "  $(git log -1 --format='%h %s' "$c")"; done
    else echo "(none)"; fi
  else FAILS="$FAILS- reflog check failed: commits reachable only from this worktree's reflog are unknown$NL"; fi

  if [ -f "$TOP/.gitmodules" ]; then
    echo "=== Submodules ==="
    if SMST=$(git -C "$TOP" submodule status --recursive); then
      NINIT=$(printf '%s\n' "$SMST" | grep -c '^[^-]')
      echo "initialized submodules: $NINIT"
      [ "$NINIT" -gt 0 ] && echo "!! a plain worktree removal refuses a worktree with an initialized submodule (see Step 5)"
    else FAILS="$FAILS- git submodule status failed$NL"; fi
    echo "--- per submodule: uncommitted, untracked and ignored entries, stashes, commits on local branches that no remote-tracking branch has:"
    # Each git call must succeed, or the foreach fails and the check is listed as not run.
    if SUB=$(git -C "$TOP" submodule foreach --quiet --recursive \
        'a=$(git status --porcelain --ignored --untracked-files=all) && b=$(git stash list) && c=$(git log --oneline --branches --not --remotes) || exit 1; o="$a$b$c"; [ -z "$o" ] || printf "== %s\n%s\n%s\n%s\n" "$sm_path" "$a" "$b" "$c"'); then
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
        # merge-base --is-ancestor exits 1 for "no" and anything else for an error, so an error is
        # never read as "not on origin". The loops read here-docs, not pipes, so FAILS survives.
        RHOK=""
        if [ "$FETCH" != no-origin ] && LSR=$(git ls-remote --heads origin); then RHOK=1
        else FAILS="$FAILS- git ls-remote origin failed: whether each unmerged commit is on origin is unknown$NL"; fi
        RH=$(printf '%s\n' "$LSR" | cut -f1 | grep .)
        while IFS= read -r c; do
          where="origin unknown"
          if [ -n "$RHOK" ]; then
            where="NOT on any origin branch"
            while IFS= read -r h; do
              [ -n "$h" ] || continue
              if ! git cat-file -e "$h^{commit}" 2>/dev/null; then where="unknown: origin has a tip not fetched here"; continue; fi
              git merge-base --is-ancestor "$c" "$h"; rc=$?
              if [ "$rc" = 0 ]; then where="on an origin branch"; break
              elif [ "$rc" != 1 ]; then where="unknown: git merge-base failed"
                FAILS="$FAILS- git merge-base failed for $c: whether it is on origin is unknown$NL"; fi
            done <<RH_END
$RH
RH_END
          fi
          echo "  $(git log -1 --format='%h %s' "$c") [$where]"
        done <<UNMERGED_END
$UNMERGED
UNMERGED_END
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
  # An unknown main checkout path would make git -C "" read this worktree instead, so skip.
  if [ -z "$MAIN" ]; then echo "(not checked: the main checkout's path is unknown, see the checks that did not run)"
  else
    MB=$(git -C "$MAIN" branch --show-current)
    if MS=$(git -C "$MAIN" status --porcelain); then
      echo "branch: ${MB:-(detached)}; uncommitted entries: $(printf '%s' "$MS" | grep -c .)"
    else FAILS="$FAILS- git status in the main checkout failed$NL"; fi
    MR=""; [ -n "$MB" ] && MR=$(git -C "$MAIN" config "branch.$MB.remote")
    if [ -z "$MR" ] || [ "$MR" = "." ]; then
      FAILS="$FAILS- the main checkout's branch has no remote upstream: level with the remote is unknown$NL"
    else
      # Ask the remote for the upstream branch's tip itself, so a narrow fetch refspec or a stale
      # tracking ref cannot stand in for it. A missing object is fetched by name with an empty
      # --refmap, which turns off the configured mapping, so no remote-tracking ref is updated.
      # Both run in the main checkout, so its own remote configuration applies.
      MM=$(git -C "$MAIN" config "branch.$MB.merge"); RS=""
      if [ -n "$MM" ] && LSU=$(git -C "$MAIN" ls-remote "$MR" "$MM"); then RS=$(printf '%s\n' "$LSU" | awk -v r="$MM" '$(2)==r {print $(1)}')
      fi
      if [ -n "$RS" ] && { git cat-file -e "$RS^{commit}" 2>/dev/null || git -C "$MAIN" fetch --quiet --refmap= "$MR" "$MM" 2>/dev/null; } \
         && git cat-file -e "$RS^{commit}" 2>/dev/null && LR=$(git -C "$MAIN" rev-list --left-right --count "$RS...HEAD"); then
        echo "upstream: $MR $MM, tip $(git rev-parse --short "$RS") per the remote now; behind it: $(printf '%s' "$LR" | cut -f1); ahead of it: $(printf '%s' "$LR" | cut -f2)"
      else
        FAILS="$FAILS- the main checkout's upstream ($MR ${MM:-?}) could not be read from the remote or counted: level with the remote is unknown$NL"
      fi
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
  release PR. List every PR you opened in this repo since the session began, with the date the
  session started (or the date of this branch's oldest commit not on the default branch):
  `gh pr list --author @me --state all --search "created:>=<YYYY-MM-DD>" --limit 1000 --json number,title,headRefName,state,createdAt,url`.
  Pick out this session's and check each with `gh pr view <n> --json number,state,mergedAt,baseRefName,url`.
  This covers PRs opened under your account in this repo only. The note names the PRs you checked
  and does not call the list complete; a PR in another repo, or opened under another account, is
  named only if the session knows of it.
- **The ticket.** Find its id from the arguments, the branch name, the PR titles or the session.
  Read its state from the tracker now, with whatever access this session has (for Linear, the
  `get_issue` tool or a CLI). Read its acceptance checklist too and note each line that is not
  yet true. If the tracker can't be read, the ticket state is unverified: say so.
- **The ticket beside its PRs.** Show the ticket's Linear state beside the state of its linked PRs.
  Take the PRs from the ticket's Linear PR attachments (`get_issue`), and read each with
  `gh pr view <url> --json state,isDraft,mergedAt`; this comparison uses no GitHub search. Flag a
  mismatch, such as a ticket in Todo beside an open PR, in the reply's **Needs you:** and under
  WAITING ON in the note, recommending the move the Linear rules give.
  What to do about it is in the Linear rules in the global instructions (dotfiles `claude/CLAUDE.md`,
  "Linear"); this skill moves nothing.
- **Releases and tags** the session made, if any: `gh release view <tag>` or `git ls-remote --tags origin <tag>`.

### Step 2 — Decide whether the worktree is safe to delete

Every verdict here means "by these checks". Git keeps state in more places than any list of
checks covers, so the reply and the note always carry the **Not checked** list below with the
verdict, and never say "safe" without it.

**Safe to delete** only when all of these hold:

- This is a linked worktree, not the main checkout.
- Nothing is uncommitted or untracked, `HANDOFF.md` aside.
- No commit is listed under "Commits here that are not on" the default branch.
- Every ignored entry is the same as the main checkout's. No ignored entry is "only here",
  "different", "not examined" or a nested git repo, on a build-output line or a top-level line.
- "Worktree-private git state" says none: an operation in progress, a per-worktree ref or
  per-worktree config goes with the worktree.
- No commit is listed as reachable only from this worktree's HEAD reflog or ORIG_HEAD.
- No submodule was listed under a `==` header (when the repo has submodules): its uncommitted,
  untracked or ignored entries, stashes, and commits on local branches that no remote-tracking
  branch has. Remote-tracking refs can be stale, so for a worktree with
  initialized submodules also apply the checks in `dv:orca-setup` Step 5 before any removal.
- No stash is listed as made on this branch or detached HEAD. A stash survives the removal but
  nobody will look for it, so name it.
- "Checks that did not run" says none. Any line there makes the verdict not confirmed safe.

**Safe once you accept losing** the listed items: every rule above holds except two, and what
breaks them is only this. Ignored entries that are not the same as the main checkout's are all
build output, whatever their kind: "only here", "different" or "not examined" (a nested git repo
is never build output; see below). Build output is
an entry inside a directory named `.venv/`, `venv/`, `node_modules/`, `__pycache__/`,
`.pytest_cache/`, `.mypy_cache/` or `.ruff_cache/`, at any depth (a setup step or the next run
recreates it), and Step 1 lists it on that name's `<name>/ (any depth)` line, never on a
top-level line. A top-level line named after a build-output directory (`.venv/  1 entries: …`)
is not build output: it holds what Step 1 kept off the build-output line, such as a nested repo.
The name must be a whole directory name: `myvenv/`, `venv_notes/` and a file named `venv` are not
build output. An entry under two such names (`node_modules/pkg/__pycache__/x.pyc`)
counts once, under the outermost. A nested git repository (kind `nested-repo`: a folder below the
worktree's top holding a `.git` file or folder, or both `objects/` and `refs/` directories, ignored or not, such as a `pip install -e git+…`
clone in `.venv/src/<pkg>/`; an initialized submodule is not one) is never build output, even
under a build-output name: it can hold unpushed commits, Step 1 lists it on its
top-level line and by path, and any one of them rules this verdict out. And commits listed as
reachable only from this worktree's HEAD reflog or ORIG_HEAD (usually commits amended or reset away; removal ends their recovery path).
The verdict names every build-output line Step 1 printed in a short form: its name, entry count,
directory count and fingerprint word for word as printed, without the per-kind counts (for example
`__pycache__/ (any depth): 666 entries in 87 directories; fingerprint 3f9a0c1e2b7d`), and the
reflog-only commits with their count, list id and the commits as listed (all of them, or the
first 50 when there are more). It is not "safe" until I accept losing them: nothing in Steps 4
and 5 that needs "safe" runs before that yes, and the question that asks for it names the
build-output lines and the reflog-only commits.

Safe to delete is about data. Whether a given removal command can do it is separate: see the
initialized-submodule case in Step 5.

**Not checked** (a fixed list; copy it into the reply and the note under the verdict):

- Tags created inside a submodule. A tag-only commit there is lost with the clone; push such tags
  by hand.
- Whether a submodule's remote-tracking refs are current. They can be stale, so "on no
  remote-tracking branch" is a strong hint, not proof.
- Anything outside git's view of the worktree that refers to it: editor or tool state, running
  processes, paths written into other repos' configuration.
- An ignored file compared only by content with the main checkout's copy, not by whether either
  copy is the one that matters.

Otherwise it is **not safe to delete**, and the reply names exactly what would be lost: each
file outside build output (an edited `.env`, anything "different", "not examined" or "only here"
on a top-level line), each nested git repository by path (wherever it is, build-output names
included), and each commit by short sha and subject. Build output is named by its
per-name lines, as above. Say where a commit still lives. On a named branch
the commit stays on that branch after the worktree goes, and on the remote if it says pushed; on a
detached HEAD nothing refers to it once the worktree is gone. When a check could not run, the
verdict is **not confirmed safe**, with the check that is missing.

An open or unmerged PR, or a ticket that is not in a finished state, does not by itself put files
at risk, but the work is not finished. Say so first, and suggest `/handoff` if it will continue.

### Step 4 — Archive the handoff (only when safe to delete)

Run this right after Step 2, before Step 3 writes the note, and only when Step 2 said safe to
delete, or said safe once I accept losing the listed build-output lines and reflog-only commits
and I have said yes to that in this session (my answer to Step 5's question, which a standing yes
does not replace; with a Head, my yes verified as "With a Head" says, "The losses"), with Step
5's recheck matching the lines I accepted word for word. A changed
"safe once you accept losing" verdict waits on a new yes. It moves this session's handoff out of
the shared store into `handoffs/_done/`, the way `/pickup` does for a branch whose PR merged, so
`/pickup` in other worktrees stops listing a closed session. It also covers a detached worktree,
which `/pickup` never archives: the handoff is found by the worktree path it records, and archived
under the name `/pickup` looks for. Nothing is deleted and no earlier archive is overwritten.

```bash
# Fails closed: every command whose failure could look like success adds to PFAIL (before
# anything moves) or AFAIL (after), and either one prints ARCHIVE INCOMPLETE instead of a success
# line. Only the last line's two success forms confirm the archive. A symlink is never followed:
# -d and -f follow one and find does not, so a link at the store, _done, HANDOFF.md or a store
# .md entry could send a move or copy outside the store, or hide a handoff, and still end in a
# success line. Each of those fails the block instead.
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "!! ARCHIVE INCOMPLETE: not a git repository — nothing archived"
else
  PFAIL=""; TOP=""; MAIN=""; STORE=""; B=""; SLUG=""
  TOP=$(git rev-parse --show-toplevel) && [ -d "$TOP" ] || PFAIL="$PFAIL; the worktree's top could not be read"
  if WTL=$(git worktree list --porcelain) && MAIN=$(printf '%s\n' "$WTL" | sed -n '/^worktree /{s/^worktree //p;q;}') && [ -n "$MAIN" ]; then :
  else MAIN=""; PFAIL="$PFAIL; the main checkout could not be read"; fi
  # cd's own output (a shell hook that prints on cd) stays out of GA.
  if GCD=$(git rev-parse --git-common-dir) && GA=$(cd "$GCD" >/dev/null 2>&1 && pwd -P) && [ -d "$GA" ]; then STORE="$GA/handoffs"
  else PFAIL="$PFAIL; the handoff store could not be resolved"; fi
  B=$(git branch --show-current) || PFAIL="$PFAIL; git branch --show-current failed"
  if [ -n "$B" ]; then SLUG=$(printf '%s' "$B" | sed -e 's/%/%25/g' -e 's#/#%2F#g') || PFAIL="$PFAIL; encoding the branch name failed"
  elif HS=$(git rev-parse HEAD) && [ -n "$HS" ]; then SLUG="detached-$HS"
  else PFAIL="$PFAIL; HEAD could not be read"; fi
  [ -n "$SLUG" ] || PFAIL="$PFAIL; the handoff name could not be worked out"
  # Each path's own kind, symlink first. GA is a real path already (pwd -P); TOP is the worktree
  # itself, and only its HANDOFF.md entry is used.
  if [ -n "$STORE" ]; then
    if [ -L "$STORE" ]; then PFAIL="$PFAIL; $STORE is a symlink"
    elif [ -e "$STORE" ] && [ ! -d "$STORE" ]; then PFAIL="$PFAIL; $STORE is not a directory"
    elif [ -L "$STORE/_done" ]; then PFAIL="$PFAIL; $STORE/_done is a symlink"
    elif [ -e "$STORE/_done" ] && [ ! -d "$STORE/_done" ]; then PFAIL="$PFAIL; $STORE/_done is not a directory"; fi
  fi
  if [ -n "$TOP" ]; then
    if [ -L "$TOP/HANDOFF.md" ]; then PFAIL="$PFAIL; $TOP/HANDOFF.md is a symlink"
    elif [ -e "$TOP/HANDOFF.md" ] && [ ! -f "$TOP/HANDOFF.md" ]; then PFAIL="$PFAIL; $TOP/HANDOFF.md is not a regular file"; fi
  fi
  # The tree must be clean, HANDOFF.md aside. Filtered in the shell, not by grep, so a failing
  # filter cannot read as a clean tree. Each here-doc that decides a result ends with a sentinel
  # line: a here-doc that could not be written (zsh writes them to temp files) skips its loop,
  # and the missing sentinel then fails the block instead of reading as "nothing there".
  DIRTY=""; ST=""; SEEN=""
  if [ -z "$PFAIL" ] && [ "$TOP" != "$MAIN" ]; then
    if ST=$(git status --porcelain --untracked-files=all); then
      while IFS= read -r l; do case "$l" in __ST_END__) SEEN=1 ;; ""|??" HANDOFF.md") ;; *) DIRTY=1 ;; esac; done <<ST_END
$ST
__ST_END__
ST_END
      [ -n "$SEEN" ] || PFAIL="$PFAIL; the clean-tree check did not run"
    else PFAIL="$PFAIL; git status failed"; fi
  fi
  if [ -n "$PFAIL" ]; then
    echo "!! ARCHIVE INCOMPLETE: ${PFAIL#; } — nothing archived; offer no removal until this is fixed"
  elif [ "$TOP" = "$MAIN" ]; then
    echo "(this is the main checkout — nothing archived)"
  elif [ -n "$DIRTY" ]; then
    echo "!! uncommitted changes — not safe to delete, nothing archived"
  else
    AFAIL=""; LIST=""; ANAMES=""
    TS=$(date -u +%Y%m%dT%H%M%SZ) && [ -n "$TS" ] || AFAIL="$AFAIL; date failed"
    # find alone, then sort, each checked: a pipe reports only its last command's status.
    if [ -d "$STORE" ]; then
      if FL=$(find "$STORE" -maxdepth 1 -type f -name '*.md'); then
        LIST=$(printf '%s\n' "$FL" | sort) || AFAIL="$AFAIL; sorting the handoff store's listing failed"
        # That listing takes regular files only, so any other .md entry there (a symlink, say)
        # would be skipped unread, even one that is this session's handoff.
        if NREG=$(find "$STORE" -maxdepth 1 -name '*.md' ! -type f); then
          [ -z "$NREG" ] || AFAIL="$AFAIL; the handoff store holds a .md entry that is not a regular file: $(printf '%s' "$NREG" | tr '\n' ' ')"
        else AFAIL="$AFAIL; listing the handoff store's other entries failed"; fi
      else AFAIL="$AFAIL; listing the handoff store failed"; fi
    fi
    [ -f "$TOP/HANDOFF.md" ] && LIST=$(printf '%s\n%s\n' "$LIST" "$TOP/HANDOFF.md")
    # A here-doc, not a pipe, so AFAIL survives the loop in bash. An AFAIL set above stops every move.
    [ -n "$AFAIL" ] && LIST=""
    LSEEN=""
    while IFS= read -r f; do
      [ "$f" = __LIST_END__ ] && { LSEEN=1; continue; }
      [ -n "$f" ] || continue
      if ! fm=$(sed -n '2,/^---$/{/^---$/!p;}' "$f"); then AFAIL="$AFAIL; reading $f failed"; continue; fi
      if ! fb=$(printf '%s\n' "$fm" | sed -n '/^branch:/{s/^branch: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p;q;}') ||
         ! fw=$(printf '%s\n' "$fm" | sed -n '/^worktree:/{s/^worktree: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p;q;}'); then
        AFAIL="$AFAIL; reading the front matter of $f failed"; continue
      fi
      mine=""
      [ "$f" = "$STORE/$SLUG.md" ] && mine=1
      [ "$fw" = "$TOP" ] && [ "$fb" = "${B:-(detached)}" ] && mine=1
      # A HANDOFF.md in the worktree that does not name this branch and worktree would go with
      # the worktree unarchived, so it leaves the archive not confirmed.
      if [ -z "$mine" ] && [ "$f" = "$TOP/HANDOFF.md" ]; then AFAIL="$AFAIL; $TOP/HANDOFF.md does not name this branch and worktree, so it was not archived"; fi
      [ -n "$mine" ] || continue
      # The store file is always moved, so the active slot is cleared even on a rerun. HANDOFF.md is
      # copied only when no archived file already matches it byte for byte (it mirrors the store copy).
      if [ "$f" = "$TOP/HANDOFF.md" ] && [ -d "$STORE/_done" ]; then
        if ! DL=$(find "$STORE/_done" -maxdepth 1 -type f -name "$SLUG.*.md"); then AFAIL="$AFAIL; listing $STORE/_done failed"; continue; fi
        # cmp exits 0 for the same bytes, 1 for different ones, 2 or more for an error.
        dup=""; DSEEN=""; DERR=""
        while IFS= read -r a; do
          [ "$a" = __DL_END__ ] && { DSEEN=1; continue; }
          [ -n "$a" ] || continue
          cmp -s "$a" "$f"; rc=$?
          if [ "$rc" = 0 ]; then dup=1; elif [ "$rc" != 1 ]; then DERR=1; fi
        done <<DL_END
$DL
__DL_END__
DL_END
        [ -n "$DSEEN" ] || { AFAIL="$AFAIL; the duplicate check against $STORE/_done did not run"; continue; }
        [ -z "$DERR" ] || { AFAIL="$AFAIL; comparing HANDOFF.md with an archived copy failed"; continue; }
        [ -n "$dup" ] && continue
      fi
      n=0; dest="$STORE/_done/$SLUG.$TS.md"
      while [ -e "$dest" ] || [ -L "$dest" ]; do n=$((n+1)); dest="$STORE/_done/$SLUG.$TS-$n.md"; done
      if ! mkdir -p "$STORE/_done" || [ ! -d "$STORE/_done" ]; then AFAIL="$AFAIL; mkdir $STORE/_done failed"; continue; fi
      # The archived file must be a regular file at dest, not a link. ANAMES keeps each name
      # (no "/" in it: the slug encodes it) for the check at the end.
      if [ "$f" = "$TOP/HANDOFF.md" ]; then
        if [ -L "$f" ]; then AFAIL="$AFAIL; $f is a symlink"
        elif cp "$f" "$dest" && [ -f "$dest" ] && [ ! -L "$dest" ] && cmp -s "$f" "$dest"; then ANAMES="$ANAMES${dest##*/}/"; echo "archived a copy of HANDOFF.md: $dest"
        else AFAIL="$AFAIL; copying HANDOFF.md failed"; fi
      elif mv "$f" "$dest" && [ ! -e "$f" ] && [ -f "$dest" ] && [ ! -L "$dest" ]; then ANAMES="$ANAMES${dest##*/}/"; echo "archived: $f -> $dest"
      else AFAIL="$AFAIL; moving $f failed"; fi
    done <<LIST_END
$LIST
__LIST_END__
LIST_END
    [ -n "$LSEEN" ] || AFAIL="$AFAIL; the handoff list could not be read"
    { [ -e "$STORE/$SLUG.md" ] || [ -L "$STORE/$SLUG.md" ]; } && AFAIL="$AFAIL; $STORE/$SLUG.md is still in the store"
    # A failed listing of _done is not "no handoff": only a _done that is absent, or listed with
    # no match, counts as nothing archived. Each file archived in this run must still be a regular
    # file there, and the store, _done and HANDOFF.md are checked for a symlink once more, last, so
    # a success line speaks only for the store's own _done and the worktree's own HANDOFF.md.
    DONE=""
    if [ -d "$STORE/_done" ]; then
      DONE=$(find "$STORE/_done" -maxdepth 1 -type f -name "$SLUG.*.md") || AFAIL="$AFAIL; listing $STORE/_done failed"
    elif [ -e "$STORE/_done" ]; then AFAIL="$AFAIL; $STORE/_done is not a directory"; fi
    rest=$ANAMES
    while [ -n "$rest" ]; do
      a=${rest%%/*}; rest=${rest#*/}
      { [ -f "$STORE/_done/$a" ] && [ ! -L "$STORE/_done/$a" ]; } || AFAIL="$AFAIL; $STORE/_done/$a, archived in this run, is no longer a regular file there"
    done
    [ -L "$STORE" ] && AFAIL="$AFAIL; $STORE is a symlink"
    [ -L "$STORE/_done" ] && AFAIL="$AFAIL; $STORE/_done is a symlink"
    [ -L "$TOP/HANDOFF.md" ] && AFAIL="$AFAIL; $TOP/HANDOFF.md is a symlink"
    if [ -n "$AFAIL" ]; then echo "!! ARCHIVE INCOMPLETE: ${AFAIL#; } — offer no removal until this is fixed"
    elif [ -z "$DONE" ]; then echo "(no handoff for this session — nothing to archive)"
    else echo "archive complete: this session's handoff is in $STORE/_done"; fi
  fi
fi
```

The archive is confirmed only when the block's last line is one of its two success lines:
`archive complete: this session's handoff is in <store>/_done` or `(no handoff for this session —
nothing to archive)`. The `archived:` lines alone do not confirm it. Every other outcome leaves
the archive not confirmed: `ARCHIVE INCOMPLETE` (say what failed; the block prints it when a
command whose failure could look like success fails, when the store, `_done` or `HANDOFF.md` path
is a symlink or of the wrong kind (checked before anything moves, and for a symlink again at the
end, `HANDOFF.md` also right before its copy), when a `.md` entry at the store's top level is not a regular file (a symlink, say),
when a file it archived in this run is not a regular file in `_done` at the end, when a here-doc it reads could not be read to its end (each of the three
ends with a sentinel line), when `cmp` errors (exit 2 or more) in the duplicate check, when a `HANDOFF.md` in the
worktree does not name this branch and worktree, when this session's store file is still there
afterwards, and outside a git repository), `uncommitted changes`, `this is the main
checkout`, no output at all (the block stopped early), or Step 4 not run. A symlink at any of
those paths is rejected, not resolved: `/handoff` and `/pickup` make none there, so one means the
store is not as they left it. Only the git common directory is resolved (`pwd -P`), as `/handoff`
and `/pickup` resolve it, so the store is the same real directory they use. Step 1's recheck, not
this block, decides the verdict; the block's own `git status` only guards the archive. Then offer and name no removal: the session would stay listed by `/pickup`, and a
handoff copy that exists only in the worktree would go with it. The `HANDOFF.md` in the worktree is left in place; it goes with the worktree. When Step 2 did not
say safe (or I have not yet accepted the listed losses), skip this step and say the handoff was
left where it is. Either way, Step 3 comes next and writes this result into the note (Step 3,
"The note follows Step 4").

### Step 3 — Write the parent note and copy it

Run this after Step 4, in the same turn, or right after Step 2 when Step 4 is skipped. Write the
note as plain text, no markdown, for a reader who was not in this session. Include only what the
parent needs to act on or to avoid redoing. Every state in it comes from Steps 1, 2 and 4 as run
in this turn. Use these headings in this order, and write "none" under one with nothing to say:

```
CLOSEOUT NOTE from <branch or "detached"> at <worktree path>, <date and time with zone>
Worktree: <safe to delete | safe once you accept losing: <each build-output line as name, entry count, directory count and fingerprint; reflog-only commits with count and list id> | NOT safe to delete: what would be lost, each nested git repo by path | not confirmed safe: what is unverified>, by these checks
Not checked: <the fixed list from Step 2>

WHAT SHIPPED
<ticket id, title and state now; each PR with number, merge state and link; releases and tags>

TICKETS FILED OR CHANGED
<id, what changed>

NOTICED, NOT FILED
<things seen along the way that nobody has written down anywhere else>

WAITING ON <the user's name; with a Head, the Head's name ("With a Head")>
<decisions only they can make, each with a recommendation>

CLEANUP THE PARENT OWNS
<pull the main checkout if it is behind; the removal command only where "The note follows Step 4" allows it, otherwise "no removal command" and why; anything else>

REPLY NEEDED: <no | yes: the question; with a Head, its Qk>
```

**The note follows Step 4.** The Worktree line and CLEANUP say what Step 4 printed in this
turn. Only the first case names a removal command:

1. Step 2 said safe to delete, or said safe once you accept losing and I have said yes to those
   losses (the recheck matching, Step 5), and Step 4's last line in this turn is one of its two
   success lines: the Worktree line is Step 2's verdict word for word, with nothing added to it
   (the Director's recheck compares it word for word; say who accepted which losses elsewhere in
   the note), and CLEANUP names the removal command Step 5 gives (with an initialized submodule,
   the guarded procedure Step 5 names instead of a command).
2. Step 2 said either of those, but in this turn Step 4 printed anything else (`ARCHIVE
   INCOMPLETE`, `uncommitted changes`, the main-checkout line, or nothing) or did not run: the
   Worktree line is `not confirmed safe: handoff archive not confirmed (Step 4 printed "<its last
   line>", or "Step 4 has not run in this turn"), by these checks`.
3. Step 2 said safe once you accept losing and I have not said yes to those losses: Step 4 has
   not run, since it waits on that yes. The Worktree line is `not confirmed safe: losing <each
   build-output line and the reflog-only commits, as Step 2's verdict lists them> waits on <the
   user's name>'s yes, and the handoff archive (Step 4) has not run, by these checks`, and
   CLEANUP says there is no removal command until those losses are accepted and Step 4 confirms
   the archive. After my yes, the turn that acts on it rechecks (Step 5), runs Step 4 and writes
   the note again with this step, as a new copy that follows case 1 or case 2.
4. Step 2 said NOT safe to delete or not confirmed safe: Step 4 did not run, and the Worktree
   line is Step 2's verdict as it is.

Outside case 1 no removal command appears anywhere in the note: CLEANUP says `no removal command`
and why removal is blocked (what would be lost, the check that did not run, the archive not
confirmed, or the losses waiting on my yes), and, when Step 4 did not run, that the handoff was
left where it is. The Director's check on the note (`dv:director-mode`, "End a finished worktree
session", check 1) refuses `NOT safe to delete` and `not confirmed safe`, so it leaves the
worktree and tells me instead of asking me to close the session or releasing it. Known limit
(VIL-1209): if the session ends anyway, director-mode's later removal runs the global removal
procedure's checks, which do not read the note.

**One saved copy per run.** Each run of this step writes the note once and saves it once, with the
block below, which never overwrites a saved copy. Writing the note again later (after my yes,
after a recheck that found a change, and before every send of the note, "Deliver the note") first
runs Steps 1 and 2 again, and Step 4 when its gate allows it, then saves that note as a new copy
under a new `<branch slug>.<YYYYMMDDTHHMMSSZ>.txt` name (with `-<n>` on a clash). The newest copy
supersedes the earlier ones, and the reply shows it and names its path. A sent note is always the
copy saved for that send, in the send's own turn, after that turn's Steps 1, 2 and 4 (Step 4
when its gate allows it; by SendMessage, the copy its `Saved at:` line names): the Director reads that copy and takes the note's time from its
file name (`dv:director-mode`, "The note's header, time and sender"), and a copy from an earlier
turn would give it that turn's Step 4 result and time. An earlier copy stays in `closeouts/` as
the record of its own turn, written after that turn's Step 4.

Leave out secrets, credentials and tokens. Then save the note and attempt to copy it, with the note's text
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
    COPY_HELPER=""; COPY_ACCEPTED=""
    if command -v pbcopy >/dev/null 2>&1; then COPY_HELPER=pbcopy; pbcopy < "$NOTE" && COPY_ACCEPTED=1
    elif command -v wl-copy >/dev/null 2>&1; then COPY_HELPER=wl-copy; wl-copy < "$NOTE" && COPY_ACCEPTED=1
    elif command -v xclip >/dev/null 2>&1; then COPY_HELPER=xclip; xclip -selection clipboard < "$NOTE" && COPY_ACCEPTED=1
    elif command -v xsel >/dev/null 2>&1; then COPY_HELPER=xsel; xsel --clipboard --input < "$NOTE" && COPY_ACCEPTED=1
    elif command -v clip.exe >/dev/null 2>&1; then COPY_HELPER=clip.exe; clip.exe < "$NOTE" && COPY_ACCEPTED=1
    fi
    if [ -n "$COPY_ACCEPTED" ]; then
      echo "clipboard command accepted the note ($COPY_HELPER); clipboard copy unconfirmed — paste from the reply if needed"
    elif [ -n "$COPY_HELPER" ]; then
      echo "!! clipboard command failed ($COPY_HELPER); clipboard copy unconfirmed — paste from the reply"
    else
      echo "(no clipboard command found — copy not attempted; paste from the reply)"
    fi
  else
    echo "!! the note could NOT be saved to $NOTE — nothing was copied; paste it from the reply"
  fi
fi
```

The saved copy lives in the repo's shared git directory (`<git-common-dir>/closeouts/`), so it
survives the worktree's removal and the parent session can read it by path. A clipboard command's
exit status only shows whether it accepted the note, not whether it reached the clipboard I paste from. This
also applies outside Orca: the command may run on another machine or in a different clipboard
context. A same-shell readback (`pbpaste` or `osascript`) does not confirm my paste either.
Report command accepted / copy unconfirmed, command failed / copy unconfirmed, or no command /
copy not attempted, as the block printed. Only say the clipboard copy is confirmed if I have
verified pasting this note in my UI. Always include the full note in the reply's code block,
whatever the clipboard status.

### Step 5 — Reply, and leave the removal to me

When the removal is cleared (the bullet "Removal cleared", below), name the removal command for
the tool that made the worktree, to be run from the main checkout after this session has ended.
Do not run it.

- A worktree under `<main checkout>/.claude/worktrees/<topic>`, where `wt` is on PATH:
  `wt done <topic>`.
- Otherwise: `git -C <main checkout> worktree remove <worktree path>`. It keeps the branch;
  deleting a merged branch is a separate procedure and not this skill's.
- If the worktree lives in Orca and its CLI resolved (section below), the Orca removal offer
  replaces this command; otherwise keep the command above.
- While the note waits for the probe answers ("Deliver the note", below), say that removing the
  worktree ends this session, and the note is then not sent.
- **Removal cleared.** Name a removal command, in the reply or the note, only when Step 2 said
  safe to delete, or it said safe once I accept losing and I accepted those build-output lines and
  reflog-only commits (the recheck below still matching), and Step 4's latest run confirmed the
  archive (its two success lines, Step 4), before Step 3 wrote the latest note (Step 3, "The note
  follows Step 4"). Otherwise, whether or not the note went to the session the probe picked, name
  no command and don't leave the removal to a Director: say why removal is blocked (what would be
  lost, the check that did not run, or the archive not confirmed or not yet run), and for losses
  not yet accepted ask the question in the paragraph below.
- **The probe's peer has the note.** This bullet applies when the removal is cleared, the note
  has been sent to the session the probe picked ("Deliver the note", steps 4 and 5) with Step 4's
  archive confirmed in that send's turn (so the note sent says safe: Step 3, "The note follows
  Step 4", case 1), and either Step 2 said safe to delete or a standing yes of mine (in the global
  instructions, this project's instructions or memory) covers every accepted loss and my
  acceptance came before the note that was sent. Closeout then knows only that the session the
  probe picked answered it with the main checkout's path: the answer is that session's own
  claim, not proof that it runs `dv:director-mode` ("Deliver the note", step 4, known limit). "Offer the
  removal", below, asks no removal question, because a Director Mode session in the main checkout
  removes a finished worktree after its session ends if its checks pass (`dv:director-mode`,
  "Take closeout notes" and "End a finished worktree session"). Never say that the Director
  removes this worktree. Say that the note went to `<that session's name>`, which answered the
  probe from the main checkout; that no removal question is asked; and that if no Director removes
  the worktree after this session ends, I can run the removal command, which the reply always
  names (with an initialized submodule, the guarded procedure the bullet "Initialized
  submodules" names instead). Losses I accepted only in this session fail the Director's check on the note
  (`dv:director-mode`, "End a finished worktree session", check 1), and an acceptance after the
  note is a message from me after it (check 3), so in either case the removal stays mine and the
  question is asked, as when no note was sent. Those checks hold while a Director ends this
  session itself; if the session ends another way, its later removal does not read the note
  (known limit, VIL-1209).
- **Initialized submodules.** When the removal is cleared and Step 1 printed "initialized
  submodules" above 0, `wt done`, `git worktree remove` and a plain `orca worktree rm` all refuse
  this worktree. Say so, and point to the guarded procedure instead of a plain command:
  `dv:orca-setup` Step 5 (`orca worktree rm --force`, after its submodule checks) or dotfiles
  `docs/agents/code-review.md`, "Worktrees with submodules are detached, not removed". Do not
  offer `--force` yourself.

When the worktree is not safe, or not confirmed safe, name no removal command and offer none.
When Step 2 said safe once I accept losing (never while a nested git repo is listed: that is not
safe) and I have not said yes yet, the note says the losses wait on my yes (Step 3, "The note
follows Step 4", case 3). With a Head this question is not asked: it is an open item ("With a
Head", "The losses"). Otherwise end the reply with one plain question that names what would be lost:
each build-output line with its name, entry count, directory count and fingerprint (for example
`__pycache__/ (any depth): 666 entries in 87 directories; fingerprint 3f9a0c1e2b7d`), and the
reflog-only commits with their count and list id. Accept losing them? On my yes, recheck first
(below), then run Step 4, then write the note again with Step 3 (a new copy that follows this
Step 4), then, only if Step 4 confirmed the archive, name the removal command (or make the Orca
offer below); otherwise say why removal is blocked (the bullet "Removal cleared").

**Recheck in every later turn.** A yes arrives in a later turn, and the worktree may have changed
since the verdict. Before acting on any yes (accepting losses, archiving, removing), run the Step 1
block again and apply Step 2 to its output. Act only if the verdict is the same and, for "safe
once you accept losing", every build-output line is the same as printed, word for word: its
name, entry count, directory count, every per-kind count (same, only here, different, not
examined) and its fingerprint. The fingerprint covers each entry's path and a regular file's
contents or a symlink's target, so a build-output file edited, replaced or renamed in place, or a
symlink pointed elsewhere, changes it even when every count stays the same; file modes and times
are not part of it. A fingerprint that reads `unknown` comes with a check that did not run, so
the verdict is not the same. The reflog-only commit count and list id must be the same too, and
no nested git repo may be listed. If anything changed, act on nothing: report the new verdict,
write the note again with Step 3 if the saved one no longer holds (a new copy, after Step 4 only
when the new verdict is safe to delete; a changed "safe once you accept losing" verdict waits on
a new yes, Step 3's case 3), and ask again.

Reply in this order, short:

1. One line: the verdict as the note's Worktree line gives it (Step 3, "The note follows
   Step 4"): safe to delete; safe once you accept losing (each build-output line with its name,
   entry count, directory count and fingerprint, and the reflog-only commits); not safe to delete (and what
   would be lost, each nested git repo by path); or not confirmed safe (and which check is
   missing, that the handoff archive is not confirmed, or that the listed losses wait on my yes).
   Then the Not checked list from Step 2.
2. **Needs you:** decisions waiting on me, and anything still owed on the ticket that this
   session could not close. Leave it out if there is none. With a Head, it holds only what "With
   a Head" leaves there.
3. The verified facts, one line each: the ticket and its state; each PR and its merge state; what
   the worktree holds beyond the default branch; the main checkout against its remote (behind,
   ahead, dirty); where the handoff went, or that it was left; where this turn's copy of the note
   was saved (when an earlier turn saved one, that this copy supersedes it) and
   the clipboard attempt status from Step 3 (unconfirmed unless I verified pasting this note);
   what happened with the Director, as one of the outcomes in "Deliver the note" (not sent and why, probe sent and the note waiting for the answers, send
   failed and probe sent again with the note waiting for the answers, answered but not verified
   (a wrong path, or ambiguous), note sent with no reply yet, note sent and replied); the removal
   command only when the removal is cleared (Step 5's bullet "Removal cleared"; otherwise no
   command, and why removal is blocked), and, when Step 5's bullet "The probe's peer has the
   note" applies, the words that bullet gives: the note went to `<that session's name>`, which
   answered the probe from the main checkout; no removal question is asked; and if no Director
   removes the worktree after this session ends, I can run the removal command named here (with
   an initialized submodule, the guarded procedure Step 5 names instead).
4. The line the optional section below tells you to add, if any.
5. The full note itself in a fenced code block, whatever the clipboard status, so I can copy it.

## Optional: Orca delivery and removal

The terminal send and the removal offer in this section need the worktree to live in Orca and
its CLI to be on PATH. The worktree lives in Orca when `"<orca CLI>" worktree list --json` lists
its path. The chat path in "Deliver the note" (the "None" case) needs only
ListAgents, so it runs without Orca too. Everything above works without either. Resolve the CLI
and look for the parent's agent terminal:

```bash
C="${ORCA_CLI_COMMAND:-}"
if [ -z "$C" ]; then if [ "$(uname -s)" = Linux ]; then C=orca-ide; else C=orca; fi; fi
if ! command -v "$C" >/dev/null 2>&1; then
  echo "Orca steps skipped: no Orca CLI on PATH"
elif ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Orca steps skipped: not a git repository"
elif ! { WTL=$(git worktree list --porcelain) && MAIN=$(printf '%s\n' "$WTL" | sed -n '/^worktree /{s/^worktree //p;q;}') && [ -n "$MAIN" ]; }; then
  echo "Orca steps skipped: the main checkout's path could not be read"
else
  echo "Orca CLI: $C"
  echo "Main checkout: $MAIN"
  "$C" terminal list --worktree "path:$MAIN" --json
fi
```

If the block printed "Orca steps skipped", add that line as printed to the reply, skip the
terminal send and the removal offer, and go to the chat path in "Deliver the note" (the "None"
case, steps 1 to 5). (On Linux a bare `orca` is usually the GNOME screen reader, which is why the
block does not try it there.)

**Deliver the note.** A parent terminal qualifies only when its entry has an `agentIdentity`
field: that marks a running agent. A terminal without it is a plain shell, and a note sent there
would be run as commands, so never send to one.

A supervised session (`dv:manager-mode`, "A supervised session": its first message opened with
Orca's worker preamble, naming a task ID and a dispatch ID) skips both terminal bullets below and
takes the chat path (the "None" case, steps 1 to 5), even when the parent has exactly one
qualifying terminal. The Director releases that session's chat only on a note sent by
SendMessage, whose `from` address names this session's `claude` process, and only once it has
replied; a terminal input receipt (`input_accepted`, a turn seen to start) is neither, and never
authorizes a release or `worker_done`. Wait for the Director's reply (the outcome "note sent and
replied") before `dv:manager-mode` lets the session send `worker_done`. With a Head, every
session takes the chat path the same way, and that reply is the acknowledgement ("With a Head",
"Delivery" and "The acknowledgement"). Every other session
routes as the bullets say.

- Exactly one qualifying terminal (not for a supervised session): send the copy Step 3 saved in
  this turn (in a later turn, run Steps 1, 2, 4 and 3 again first, Step 3's "One saved copy per
  run"), once, with the CLI path the block printed in place of `<orca CLI>`, kept inside the quotes (no variable from that block survives to this call):
  `"<orca CLI>" terminal send --terminal <handle> --text "$(cat "<note path>")" --enter --wait-submit 20 --json`
  Report what the result says (`input_accepted`, and whether a turn was seen to start), not
  "delivered". Do not resend on a timeout. After a transport error, reissue the same command with
  the `--retry-request` id the error reports.
- More than one (not for a supervised session): ask me which, as a plain question, before sending.
- None, the Orca steps were skipped, or a supervised session: the parent may run as an Orca
  chat, which is not a terminal, or outside Orca, and a chat is never sent a note through `terminal send`. Look for
  the Director with ListAgents instead, and send the note only after it answers a probe with the
  main checkout's path:
  1. Candidates. A candidate is a peer session in ListAgents, other than this one, whose name is
     the main checkout folder's basename, then `-`, then a suffix (for example `skills-03` for
     `/Users/david/Projects/skills`). ListAgents shows no working directory, and sessions have
     been named this way so far without it being a Claude Code contract, so a name proves
     nothing; the probe does. With no candidate, or more than three, send nothing and name what
     ListAgents showed.
  2. The probe. Send each candidate this probe, once per round (a new round only after the note's
     send fails, step 5), with SendMessage. Nothing from the note goes in it:

     ```
     Director check, <ticket id, or the branch when there is none>: which directory are you running in? Reply with one line, its absolute path.
     ```

     A send that returns an error (such as "socket path is stale" or "No agent named ... is
     reachable") was not delivered: handle it as a failure, never as silence, a pending answer or
     a send. A probe with no answer 10 minutes after it was sent has failed too. A candidate
     whose probe failed leaves the candidates for this round, as if ListAgents had not listed it:
     it doesn't count toward the three and isn't probed again in this round. Step 1's rules apply
     to those left; with none left, send nothing. An answer that arrives after its probe failed
     changes nothing.

     Answers come back later as messages, often after this turn has ended. So that a turn comes
     back to notice the 10 minutes, start a background timer when the probes go out (a background
     shell command such as `sleep 600`), and stop it once every probe sent has an answer. When it
     ends, drop each candidate still silent and apply step 4 to those left. If every probe's send
     failed, the note is not sent: end this turn saying so, with each error. Otherwise end it with
     the reply, naming the candidates whose probe was sent and each failed send with its error,
     and saying the note waits for their answers.
  3. The answers. A probed candidate's answer passes when its `from-name` is that candidate and
     its path, with surrounding spaces and one trailing `/` removed, equals as text the main
     checkout's path as `git worktree list` prints it, or that path's real path (`pwd -P` run in
     the main checkout). Compare it as text; never run it in a shell. A passing answer shows
     where that session says it runs, not that it runs `dv:director-mode`.
  4. The Director. With one candidate, its passing answer makes it the Director. With two or
     three, the Director is the one whose answer passed, and only once every other probed
     candidate has answered with a different path. While a probed candidate is silent, wait: the
     note stays where it is, and silence never counts as a different path. Silence lasts at most
     10 minutes, and a probe whose send failed is not silence (step 2). If two or more
     answers pass, it is ambiguous: send nothing. In every case where no Director is found,
     report who answered what.

     Known limit: the answer is the session's own claim. A session that misstates its directory,
     or a non-Director session in the main checkout that is the only one to answer with its path,
     is taken for the Director. I accepted this on 2026-11-23: every session is one of my own
     agents on one machine, and the note holds nothing secret. So "the Director" in steps 4 and 5
     is the session the probe picked; whether it runs `dv:director-mode`, and so whether it will
     remove the worktree, is not checked (Step 5, "The probe's peer has the note").
  5. The note. Send the note once, with SendMessage to the Director's answer's `from` address.
     The answer arrives in a later turn, so first run Steps 1, 2 and 4 again in the run order
     (Step 4 when its own gate allows it: safe to delete, or safe once I accept losing with those
     very losses accepted and the recheck matching them), then Step 3, which writes the note from this turn's results, saves it once as
     a new copy and attempts to copy it to the clipboard (Step 3, "The note follows Step 4" and
     "One saved copy per run"). Send that copy; `<note path>` is the `note saved:` path Step 3
     printed in this turn. The receiver sees only the first line until it expands the
     message, so the first line must say what the message is:

     ```
     Closeout note, <ticket id, or the branch when there is none>: <the note's Worktree verdict line>
     Saved at: <note path>
     <the note, from its Worktree line to its REPLY NEEDED line>
     Please reply with one line to say you received it.
     ```

     With a Head, the last line differs ("With a Head", "Delivery").

     If the note's send fails (SendMessage returns an error, such as "socket path is stale" for
     a session that has ended, or "No agent named ... is reachable"), the Director may have
     restarted under a new name. Probe again from scratch, steps 1 to 4, with the candidates
     ListAgents lists now, and send the note to the Director that passes, by this step: in the
     turn of that send, Steps 1, 2 and 4 run again and Step 3 saves a new copy, which is the one
     sent. If that
     second note send fails too, send nothing more and report the note not sent. After a send that
     succeeded, resend neither the probe nor the note.

  Report one of these outcomes: not sent, naming what failed or could not run; probe sent, the
  note waits for the answers; send failed and probe sent again, the note waits for the answers;
  answered but not verified (a wrong path, or ambiguous), with who answered what, and nothing
  sent; note sent with no reply yet; or note sent and replied, quoting the reply. A
  message has no read receipt, so never write "delivered" without a reply. Until the note is
  sent, it stays at its saved path and in the reply; the clipboard copy stays unconfirmed unless
  I verified pasting it. Under Codex there is no ListAgents view of other sessions, so this path
  cannot run there.

What a test showed (VIL-836, 2026-11-18, from a worktree to the main checkout): the text arrived
in the main checkout's terminal. Not tested: whether a parent agent acts on a note, and whether
one that is mid-turn reads it. So for a terminal, say in the reply that the note was sent and that
the parent may still need it pasted. For a chat Director (VIL-918, 2026-11-23, on hal): this
step, run by hand from a worktree, found one candidate, `skills-03`. It answered the probe with
one line, the main checkout's absolute path, under that same `from-name`; SendMessage accepted
the answer's `from` address for the note, and the Director replied. Not tested: a Director that
is mid-turn when a message arrives (that one was idle), a wrong or ambiguous answer, several
candidates, and a full closeout run end to end with a real Director. Full runs in a throwaway lab
(dv 0.42.0, 2026-11-26), with a stub Orca CLI and a stub peer session standing in for the
Director, showed the probe, the note's send and the Director's reply over three turns, and a run
with no candidate sending nothing. A send to a stale address fails (VIL-1141,
2026-11-25): SendMessage returns `success: false` with "socket path is stale" for a session's old
socket path, and "No agent named ... is reachable" for a name ListAgents no longer lists. Not
tested: a socket file left behind by a session that crashed.

**Offer the removal.** Only when the worktree lives in Orca, the block printed an Orca CLI, and
the removal is cleared (Step 5's bullet "Removal cleared"), end the reply with one question
(with a Head, never: "With a Head"). Before running the removal on my yes,
recheck as Step 5 says and run Step 4 again; if the verdict changed, or Step 4 does not print one
of its two success lines, do not remove: report it and write the note again with Step 3. While the note waits for the
probe answers, say so before the question: the removal ends this session, and the note is
then not sent. The question is: remove this worktree now? Run the removal only after my yes, in a later turn, as the last action
of the session, because it stops this worktree's sessions:

`"<orca CLI>" worktree rm --worktree "path:<worktree path>" --json`

**When the probe's peer has the note, ask nothing.** This applies only where this question would
be asked (above) and Step 5's bullet "The probe's peer has the note" holds: the removal is cleared
(Step 4 confirmed the archive), the note has been sent to the session the probe picked ("Deliver
the note", steps 4 and 5) with a safe verdict, which Step 3 writes only after Step 4 confirmed the
archive in the send's turn ("The note follows Step 4", case 1), and Step 2 said safe to delete
or a standing yes of mine covers every accepted loss and my acceptance came before the note that
was sent. When the removal is not cleared there is no
question and no command: say why removal is blocked (Step 5). Where it applies, from the turn the
note is sent, in that turn and every later one, end the reply without this question, whether or
not that session has replied (the outcomes "note sent with no reply yet" and "note sent and
replied"). The probe shows only that the session answered from the main checkout's path, not that
it runs `dv:director-mode` (the known limit under "Deliver the note", step 4). The question is
skipped because a Director Mode session there removes a finished worktree after this session ends
if its checks pass (`dv:director-mode`, "Take closeout notes" and "End a finished worktree
session"); never say that the Director removes this worktree. Say instead what Step 5's bullet
gives: the note went to `<that session's name>`, which answered the probe from the main checkout;
no removal question is asked; and if no Director removes the worktree after this session ends, I
can run the command above from the main checkout (with an initialized submodule, the guarded
procedure Step 5 names instead), which the reply names. When a Director ends this
session itself, it keeps the worktree and tells me which check failed when, for example, the note
has anything under WAITING ON or a REPLY NEEDED question (with a Head, an item not handed over:
"With a Head", "Handed over"), or I message this session after the note. If the session ends another way, its later removal runs the global removal procedure's
checks, which do not read the note, so those items do not hold the worktree then (known limit,
VIL-1209). In every other case the question stays as above: no note sent to a session the probe
picked (no note sent, a second note send that failed included; the note waiting for the probe
answers, the outcome "send failed and probe sent again" included; an answer not verified; a note
sent only by `terminal send`), losses I accepted only in this session, or an acceptance after the
note was sent. Skipping
this question never stands in for my consent to losing data that exists nowhere else: while Step 2
says safe once you accept losing, Step 5's question still asks it, and nothing treats the worktree
as safe before my yes. A yes I already gave to this question, asked before the note was sent,
still counts: recheck, run Step 4 again and remove as above, as the session's last action,
without waiting for a reply to the note.

The command can return `ok: true` with `removing: true` before the removal has finished
(`dv:orca-setup` Step 5). Before reporting it done, check from the main checkout that the path is
gone from `git worktree list` and from `"<orca CLI>" worktree list --json`, and that the
directory no longer exists. If any of them still shows it, report the removal as pending or
failed, with what each check showed. (Orca's list hides worktrees under `.claude/worktrees/`, so
`git worktree list` is the one that settles it there.)

Use the `path:` selector (`current` and `active` are refused). Add no `--force` and no
`--delete-branch`: if the removal is refused, report the refusal and stop. With an initialized
submodule, do not offer this command at all (Step 5). When the removal is cleared but I have not
said yes, name this command in the reply instead and leave it to me.

## With a Head

This section applies only when this project names a department Head: a `Head:` line with a
`bot:` address in its `AGENTS.md` or `CLAUDE.md`, as `dv:director-mode`'s "The Head and the
CEO's 1%" defines it. With none, skip it. With a Head, every question these skills would put to
me goes to him, so closeout asks me nothing, in a dialog or in chat. It uses that section's
forms: the pickup note and the record ("A record on the ticket for each Qk"), the mail ("Forward"),
the approval ("An approval travels in its own field") and "What no default decides". Of its open
items, only the CEO's 1% reach me, and only through him. A Head's mailed answer is advisory
until verified Head decision delivery ships (VIL-1193): no answer from him settles an item or
counts as my yes.

**What changes in the steps:**

- Losing what Step 2 lists under "safe once you accept losing" is not asked of me (Step 5).
  Accepting it is one of the CEO's 1% (deleting my data): an open item that settles only on my
  own yes, verified ("The losses", below). It is one even when a standing yes of mine covers
  those losses, since Step 4's gate says a standing yes doesn't replace my answer.
- What the reply's **Needs you:** would hold (decisions waiting on me, and anything still owed
  on the ticket) goes under WAITING ON as open items instead, a ticket-state mismatch included
  (Step 1, "The ticket beside its PRs"). Needs you keeps only what no message can grant (a
  permission prompt, a harness approval, a barrier set for me) and what only my hands can do.
- No removal question is asked, whether or not a Director has the note ("Offer the removal"). When
  the removal is cleared, the reply still names the removal command (Step 5) and says the worktree
  stays until a Director removes it after this session ends, or I run that command, which ends
  this session, so an item not yet delivered then gets no mail. With no Director verified, nothing
  else removes it.
- The note goes only by the chat path ("Delivery", below), so neither terminal bullet runs, and
  no question about which terminal is asked.

**Open items** are the decisions under WAITING ON and the REPLY NEEDED question. In the note,
the heading reads `WAITING ON <the Head's name>`, the REPLY NEEDED question is listed there too,
and the REPLY NEEDED line names its Qk (`REPLY NEEDED: yes: Qk`). Each item is one entry in the
fields of `dv:manager-mode`'s question message: `Qk: <the item>. Key: <its original key>.
Re-sent: <yes or no>. Handed over: <yes or no> ("Handed over"). PR: <its link, or none>. Options: <numbered>. Recommended: <the option>,
because <why>. Reversible: <yes or no, and how>.`, with `CEO's 1%: yes` on one of the five, and `Mail: <each send's hop key and result>` once this session has mailed it ("Mail to him"). The
message's `Sent:`, guard and reply lines are left out: the note's time is in its saved copy's
name, and its message's last line ("Delivery") asks for the reply. With no ticket, every key and
line form in this section that names `VIL-N` takes the branch in its place, apart from the mail's
subject ("Mail to him").

- An item that already has a key keeps it: a question asked earlier on this ticket that is
  still open (`dv:manager-mode`, "With a Head"), by this session or by one before it.
- A new item takes the next Qk this session has not used: above every Qk in its written state, in
  the ticket's records under its session ID and in the note. Its original key is `VIL-N/<session
  ID>/Qk` (`dv:director-mode`, "A record on the ticket for each Qk"), and every later copy of the
  note keeps it.
- `Re-sent:` is yes for an item already sent, as a question or in a copy of the note, to a
  Director (a send that failed included) or to him, as `dv:manager-mode` marks a question.

**Delivered.** Each item is this session's until one of two things delivers it, each read back:
the verified Director's acknowledgement takes it ("The acknowledgement"), or this session's own
mail to him ("Mail to him"), under a hop key of its own, returns a message id with no error.
Nothing else delivers an item: no record or pickup note on the ticket, no mention, and no mail
another session sent. A delivered item stays open until it closes ("The ticket log").

**The ticket log.** The ticket's comments are a log, kept for people and for his pickup: no
delivery waits on one, and none stops a send. After Step 3 saves each copy of the note, before any
probe or send of it, read the ticket's comments (`list_comments`). For each item the copy lists
that has no pickup note posted by this session, post one (its form is in "A record on the ticket
for each Qk"), with the reason `it is a closeout item; any mail of it has its own record` and
`Resumes: this session while it runs, then the Director that takes the note`, and read the
comments back to see it there. Its mention wakes him through Orca's Linear trigger, so he can pick
the item up if this session ends before anything delivers it. A read or a post that fails or
doesn't read back is tried again in a later turn; the note still goes meanwhile, and until the
pickup note reads back, the reply says so and the item is not handed over. With no ticket there is
no log.

An item stays open until a `Closed` reply under its pickup note closes it (`dv:director-mode`, "A
closeout item"): a send, an acknowledgement, an answer or advice closes nothing. While this
session runs, it closes its items: only after the action an item calls for has been carried out,
by it or by the Director, and it has verified the result in the system that action changed, such
as the ticket's state read back with `get_issue`, or for the losses Step 4's success line. Before
each later copy, check again any action an answer called for. Until it closes, every copy of the
note lists it; a `Closed` reply that can't be posted or doesn't read back is posted in a later
turn, and until then the item stays open. An item with no pickup note closes by a `Closed` comment
on the ticket, or, when none can be posted, in the reply, with what was done and the check. Once
this session has ended, its open items are the Director's to resume (`dv:director-mode`, "Take
closeout notes"). When an item closes, write the note again (Step 3) and send that copy as
"Delivery" says, so the Director's check on the note reads the new WAITING ON.

**Delivery.** The note goes only to a Director its probe verified: the chat path in "Deliver the
note" (the "None" case, steps 1 to 5), as for a supervised session, even with exactly one
qualifying terminal. In the note's message (step 5), the last line reads instead:

```
Reply with "Closeout note received, <ticket id, or the branch>: <note path>", then one line for each Qk under WAITING ON, as dv:director-mode's "Take closeout notes" says.
```

A later copy is a new note, not a resend: it goes the same way, to the Director already
verified, and a send that fails is handled as step 5 says.

**The acknowledgement.** Once the note's send succeeds, start the background timer step 2 uses
and wait up to 10 minutes from the send. The acknowledgement is a message whose `from-name` is
the Director's, as step 3 checks the probe's answer, and whose first line is `Closeout note
received, <ticket id, or the branch>: <the path on the sent message's Saved at: line>`, compared
as text. Any other reply is not one, and the wait goes on. The sender check (the `from-name` and
the address are the verified Director's) applies to the whole acknowledgement. It takes an item
when its line for that Qk is one of these:

- `Answer, VIL-N, Qk: <option>`, when that line passes `dv:manager-mode`'s "What counts as the
  answer" checks other than the one that the reply starts with `Answer`: it names one of that
  item's options, and the decision is one the Director may make, with the same carve-outs (with no
  ticket, the branch in place of `VIL-N`).
  Carry out what it calls for when that is this session's to do; the item stays open until that is
  verified.
- `Forwarded to the Head, VIL-N, Qk: <the way forward>`, except in a note with no ticket. The
  Director sends it only once its own mail of the item has read back (`dv:director-mode`, "A
  closeout item"). Take the way forward.

A line whose Qk fits more than one item the copy lists takes none of them.

When the acknowledgement arrives, stop the timer and report "note sent and acknowledged", quoting
it; that is the outcome "note sent and replied". Each item not yet delivered that it doesn't take
goes to him by mail ("Mail to him") at once, and every such item does when the timer ends with no
acknowledgement, so the wait for a later copy covers only items not yet delivered. An
acknowledgement that comes after its timer ended still takes its items, and no mail already sent
is undone.

**Handed over.** An item's entry reads `Handed over: yes` only when all three of these read back
as the copy is written: an acknowledgement from the Director took it with `Forwarded to the
Head` (an `Answer` leaves an action to carry out, and this session's own mail gives the item to
no Director, so neither counts); `list_comments` on its ticket shows its pickup note; and nothing more is owed by this session (it is not the losses item, which needs Step 4; the way forward its `Forwarded` line names asks nothing of this session that is still undone; and no answer that counts, and no reply from him under its records or by mail, calls for an action of this session's still undone). Every other entry reads `Handed over: no`,
and so does every item with no ticket; a read that fails or can't be done gives
no. A handed-over item stays open, and every copy still lists it, but it no longer holds this
session: the Director's check on the note, and `dv:manager-mode`'s `worker_done`, let it pass
once they read the same three facts back themselves (`dv:director-mode`, "End a finished
worktree session", check 1); any other item still holds it. Every copy works each value out afresh. When an acknowledgement, an answer, his reply or a read of its pickup note changes an item's `Handed over:` value, write the note again (Step 3) and send that copy ("Delivery"); a later acknowledgement that changes no value needs no new copy.

**Mail to him.** Delivery fails for every item when the note can't reach a verified Director (the
outcomes "not sent" and "answered but not verified" in "Deliver the note", the probe's timer
ending with none verified, a second note send that failed, or Codex, where the chat path can't
run). It fails for one item when no acknowledgement takes it within the 10 minutes. Then send him
each item not yet delivered, by agent mail, one message per item, with this command, run with the
CLI path the block in "Optional: Orca delivery and removal" printed in place of `<orca CLI>` (if
it printed none, the send can't run and counts as one that returned an error):
`"<orca CLI>" orchestration send --to "<his bot: address>" --chat new --type question --subject "<VIL-N> <Qk>: closeout item" --body-file "<a file outside the repo>" --json`.
The subject holds none of the item's text: only the ticket id, the item's Qk and the words
`closeout item`. Before the send, check that the whole ticket id is ASCII letters, one hyphen and
ASCII digits, in that order, and the whole Qk is `Q` followed only by ASCII digits, with nothing
else in either. With no ticket, or when either check fails, the subject is `closeout item`.
The body is the item as "Forward" gives it, its keys on the first line, the CEO's 1% marked, an
`Approved by:` field asked for where an approval is needed, quotes in excerpts, and it asks him to
reply `Answer from the Head, VIL-N, Qk: <option>`. Each send takes a hop key of this session's own
that no send has used: `VIL-N/<session ID>/Hk`, with k above every k this session has sent under
(the `Mail:` lines of its saved copies, and this turn's sends), even for an item whose key is this
session's, rather than its original key, which an earlier send may have used. Only the session
whose ID is in a hop key mails under it, so two sessions never mail under one key. Nothing on the
ticket is claimed first and no record there stops a send: steps 1 to 4 of "A record on the ticket
for each Qk" don't apply. So he can get one item more than once, each time under its own key (an
earlier send of the question, a Director's forward, this session's own): each is advice, the keys
show it, and a second one changes nothing ("The limit" there).

A send whose result shows a message id and no error delivers the item. One that returns an error,
or whose result can't be read, doesn't: unless something delivers the item first, send it once
more in a later turn, under a new hop key (start the background timer step 2 uses, so that one
comes), and after a second such send mail it no more; it stays this session's, undelivered. Each
send's hop key and result go on the item's entry in the next saved copy (`Mail:`), which is what
this session reads before it sends. After each send, post its record on the ticket, when there is
one, in the form "A record on the ticket for each Qk" gives, under its hop key, at `sent` with the
message id, or else at `failed` or `unclear` with the error and, as the form says, his mention: a
log of the send, posted again in a later turn if the post fails. No question card opens, and I
click nothing. Then write the note again (Step 3), so the newest copy marks those items `Re-sent:
yes`, and report "items mailed to the Head", with each item's message id, or that its send failed
and whether it goes once more.

**His answers** come by mail to this session (`orca orchestration check --json`), as a reply
under a record, or relayed by the Director (`Answer from the Head`). Each is advice ("His
answer" there): take its option only for a decision this session's own rules already give it
(`dv:manager-mode`, "'Ask David' becomes this"). Every other item stays open on its way forward,
and an item under "What no default decides" settles only as that bullet says.

**The losses.** The item reads `Accept losing <each build-output line with its name, entry
count, directory count and fingerprint, and the reflog-only commits with their count and list
id>?`, with the options `1. Accept losing them` and `2. Keep them`, this session's
recommendation, `Reversible: no`, `CEO's 1%: yes` and a request for an `Approved by:` field. Its
way forward is option 2: Step 4 doesn't run, and no removal command is named. It settles only on
my own yes to that exact list, which this session verifies itself as "An approval travels in its
own field" says: my ticket comment (its Linear author my own account), or my message in a chat
this session can read, this one included. Neither his answer nor a quoted yes is mine; the field
only points to the evidence. A verified yes stands in for my answer to Step 5's question
wherever a step waits on it (Step 4's gate, Step 3's case 3). Then recheck (Step 5, "Recheck in
every later turn"): only if every line matches the item word for word, run Step 4, write the
note again (Step 3), and close the item once Step 4 printed one of its two success lines. A
recheck that differs voids that yes: close the item as superseded, and list any losses the new
verdict names as a new item. The Director's check on the note accepts only a standing yes for
losses (`dv:director-mode`, "End a finished worktree session", check 1), so after a yes verified
this way the removal stays mine, and the reply names the command.

**The reply.** In Step 5's reply, item 3 names the delivery outcome: one of those in "Deliver
the note", or note sent and waiting for the acknowledgement (until when), note sent and
acknowledged, or items mailed to the Head. It lists each open item by Qk, with where it is
(handed over or not; taken by the Director, mailed with its message id, a send that failed and
whether it goes once more, or not delivered and why) and whether its pickup note is on the
ticket.

Known limits: an item nothing has delivered when this session ends gets no mail; its pickup note,
if it landed, lets him pick it up, and the note's saved copies keep it. An item that only this
session's mail delivered, or that nothing delivered, is never handed over, so it keeps this
session from being closed or released through the Director's checks until it closes or an
acknowledgement takes it (with his answers advisory, that can be long). He can get one item more
than once (its pickup note, an earlier send of the question, a Director's forward, this session's
sends), each time as advice. A session that stops after a send but before the next saved copy
loses that send's result, so a later run can mail the item again, even under the same key. Two
earlier items that share a Qk (from two earlier sessions) are taken by no acknowledgement line, so
they are mailed and never handed over. Not yet tested live.

## Notes

- Closeout does not replace `/handoff`. If anything continues after this session, write a handoff
  too, before Step 4 moves it.
- The verdict is about what the worktree holds, not about whether the ticket is finished. Both
  are in the reply, and neither stands in for the other.
- When the handoff or the session's memory disagrees with what the commands returned, the
  commands win and the difference goes in the note.
