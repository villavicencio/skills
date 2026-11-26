# dv 0.42.0

`dv:closeout` no longer asks "remove this worktree now?" once its note has been sent to a
Director its probe verified and the verdict is safe to delete (or a standing yes of David's
covers the losses he accepted, before the note was sent). From the turn the note is sent, in
that turn and every later one, whether or not the Director has replied, the reply says the
Director removes the worktree after the session ends if its checks pass (`dv:director-mode`,
"Take closeout notes" and "End a finished worktree session"), and names the removal command for
David, to run after the session ends. The skill names cases where the Director keeps the
worktree instead when it ends the session itself: anything under WAITING ON or REPLY NEEDED, or
a message from David to the session after the note. If the session ends another way, the
Director's later removal runs the global removal procedure's checks, which do not read the note,
so those items do not hold the worktree then (known limit, VIL-1209).

The removal command itself keeps Step 5's guard. Closeout names one only when the worktree is
safe to delete, or is safe once David accepts losing and he has accepted its build-output lines
and reflog-only commits, and Step 4 confirmed the handoff archive. Otherwise it names none, says
why removal is blocked, and never says the Director removes it. The question stays as before
with no verified Director (no note sent, the note waiting for the probe answers, an answer not
verified, or a note sent only by `terminal send`), when the losses were accepted only in the
session, and when the acceptance came after the note was sent, since the Director's checks on
the note then fail while it ends the session itself (if the session ends another way, its later
removal does not read the note; known limit, VIL-1209).

Step 4 now ends with an explicit success line, `archive complete: this session's handoff is in
<store>/_done`, beside the existing `(no handoff for this session — nothing to archive)`; only
those two confirm the archive. The block fails closed: it prints `!! ARCHIVE INCOMPLETE: <what
failed>` instead of either success line when a command whose failure could look like success
fails (`git rev-parse`, `git worktree list`, `git branch --show-current`, `git status`, `date`,
`find` of the store or of `_done`, `sort`, the `sed` calls (status-checked) that read the main
checkout, the handoff name and a handoff's front matter, `mkdir`, `cp` with a byte-for-byte
check, `mv` with the source gone and the destination present, `cd` into the common git directory
(its output, such as a shell hook's, kept out of the path), and `cmp` in the duplicate check,
where exit 1 means different and exit 2 or more fails the block; the clean-tree filter is done
in the shell, not by `grep`, and all three here-docs that decide a result (the clean-tree check,
the handoff list and the duplicate check against `_done`) end with a sentinel line, so one that
could not be read to its end, such as one zsh could not write, fails the block), when the store
or `_done` exists but is not a directory or `HANDOFF.md` exists but is not a regular file, when
a `HANDOFF.md` in the worktree does not name this branch and worktree, when outside a git
repository, and when this session's store file is still there afterwards. Before this release a
failed listing of the store or of `_done` read as "no handoff". The uncommitted-changes and
main-checkout lines, no output, or Step 4 not run also leave the archive not confirmed. Step 1's
recheck stays the source of the verdict; Step 4's own `git status` only guards the archive.

Step 1 and the Orca block also status-check their reads of the main checkout's path (and Step 1
its reads of the worktree's path, HEAD and branch): a failure makes the verdict `not confirmed
safe` in Step 1 and skips the Orca steps in that block.

A note closeout sends (by SendMessage or `terminal send`) keeps a safe verdict only when Step 4
confirmed the archive after Steps 1 and 2 in the turn of the send; the SendMessage path reruns
Step 4 before rewriting the note when Step 2 allows it. Otherwise the sent note's Worktree line
reads `not confirmed safe: handoff archive incomplete or not confirmed (…)`, saved as a new copy
under the usual time-stamped name, and the Director's check on the note refuses it, so the
Director does not ask David to close or release that session on that note. Known limit,
VIL-1209: if the session ends by other means, director-mode's later removal runs the global
removal procedure's checks, which do not read the note.

Skipping the question never stands in for consent to losing data: while the verdict is "safe
once you accept losing", Step 5's question still asks it, and nothing treats the worktree as
safe before that yes. A yes David already gave to a removal question asked before the note was
sent still counts. The README's closeout entry states the new rule, and director-mode's
description of closeout's reply says the same.

## Verification

- With a stub Director: an interactive closeout session in a linked worktree of a throwaway
  clone, with a stub Orca CLI that lists the worktree and refuses every removal and send, and a
  stub peer session in the clone's main checkout that answered the probe with that path. Turn 1
  (probe sent, note waiting) still asked "Remove this worktree now?"; turn 2 (note sent, no
  reply yet) and turn 3 (note sent and replied) asked nothing and said the Director removes the
  worktree after the session ends, naming the command.
- With no Director: a headless closeout in the same lab found no candidate, sent nothing, and
  ended with "Remove this worktree now?".
- Both checks ran twice before MergeWren's review, on the first wording and on the second, with
  the same outcome.
- After the archive change, the Director check ran three more times. With a handoff in the store,
  Step 4 printed `archive complete: …` in turn 1 and again when rerun before the note's send,
  and the note went out as `safe to delete` with no question after it. With no handoff, Step 4
  printed the no-handoff line, with the same outcome. With the archive made to fail (`_done` a
  plain file), Step 4 printed `ARCHIVE INCOMPLETE` twice, the note went out as `not confirmed
  safe: handoff archive incomplete or not confirmed (…)` from a new saved copy, and no turn named
  a removal command or said the Director removes the worktree.
- The final Step 4 block, run on its own in bash and in zsh (`-f`) in a scratch repo, 50 cases
  each, with PATH shims that make one command fail: no handoff, a store handoff, a rerun after
  archiving, a matching `HANDOFF.md`, a store handoff with an identical `HANDOFF.md` (and its
  rerun), a store handoff under another name with quoted front matter, and a detached HEAD's
  store handoff ended in a success line, with the store emptied. Every failure case printed
  `ARCHIVE INCOMPLETE`: a non-matching `HANDOFF.md`; `_done` a plain file, with and without a
  handoff; the store a plain file, with and without `HANDOFF.md`; `HANDOFF.md` a directory; an
  unreadable store, `_done` or store handoff; a failing `git status`, `git branch
  --show-current`, `git worktree list`, `git rev-parse --git-common-dir`, `--show-toplevel` or
  `HEAD` (detached), `date`, `sort`, `find` of the store or `_done`, `sed` on a handoff, the
  handoff name or the main checkout, `mkdir`, `cp`, `cmp` after `cp`, and `mv`; and outside a
  git repository. An uncommitted file (also with `grep` failing) and the main checkout printed
  their own lines. With here-docs made unwritable, zsh printed `ARCHIVE INCOMPLETE` and bash,
  which falls back, archived for real. Each result-deciding here-doc made unreadable on its own,
  and `cmp` exiting 2 in the duplicate check, printed `ARCHIVE INCOMPLETE`; `cmp` forced to exit
  1 there led to a new verified copy and a success line, and a zsh `chpwd` hook that prints on
  `cd` no longer bends the store path. The main-checkout `sed` printing the path and then
  failing printed `ARCHIVE INCOMPLETE`; the same failure in Step 1 listed the read under the
  checks that did not run (so the verdict is not confirmed safe), and in the Orca block skipped
  the Orca steps.
- Not exercised: a real Director session's checks and removal, a terminal send, "safe once you
  accept losing", and a yes given before the note was sent.

Refs VIL-932.
