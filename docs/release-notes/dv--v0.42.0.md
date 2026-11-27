# dv 0.42.0

`dv:closeout` no longer asks "remove this worktree now?" once its note has been sent to the
peer session that answered its probe with the main checkout's path and the verdict is safe to
delete (or a standing yes of David's covers the losses he accepted, before the note was sent).
The probe proves only the directory that peer claims, not that it runs `dv:director-mode`
(closeout's existing known limit: the answer is the session's own claim). Closeout skips the
question because a Director Mode session in the main checkout removes a finished worktree after
the session ends if its checks pass (`dv:director-mode`, "Take closeout notes" and "End a
finished worktree session"); it does not claim that one will. From the turn the note is sent, in
that turn and every later one, whether or not the peer has replied, the reply says that the note
went to that peer, which answered from the main checkout, that no removal question is asked, and
that if no Director removes the worktree after the session ends, David can run the removal
command, which the reply always names. It never says the Director removes the worktree. The skill
names cases where a Director keeps the worktree instead when it ends the session itself: anything
under WAITING ON or REPLY NEEDED, or a message from David to the session after the note. If the
session ends another way, a Director's later removal runs the global removal procedure's
checks, which do not read the note, so those items do not hold the worktree then (known limit,
VIL-1209).

The removal command itself keeps Step 5's guard. Closeout names one, in its reply or its note,
only when the worktree is safe to delete, or is safe once David accepts losing and he has
accepted its build-output lines and reflog-only commits, and Step 4 confirmed the handoff
archive in its latest run, before the note was written. Otherwise it names none, says why
removal is blocked, and never leaves the removal to a Director. On a yes to the removal question it
runs Step 4 again along with the recheck, and removes nothing unless Step 4 prints one of its
two success lines. Step 4 runs for "safe once you accept losing" only after David's yes in the
session (a standing yes does not replace that question), with the recheck matching the lines he
accepted. The question stays as before when no peer the probe picked has the note (no note sent, the note waiting
for the probe answers, an answer not verified, or a note sent only by `terminal send`), when the
losses were accepted only in the session, and when the acceptance came after the note was sent,
since the Director's checks on the note then fail while it ends the session itself (if the
session ends another way, its later removal does not read the note; known limit, VIL-1209).

Step 4 now ends with an explicit success line, `archive complete: this session's handoff is in
<store>/_done`, beside the existing `(no handoff for this session — nothing to archive)`; only
those two confirm the archive. The block fails closed: it prints `!! ARCHIVE INCOMPLETE: <what
failed>` instead of either success line when a command whose failure could look like success
fails (`git rev-parse`, `git worktree list`, `git branch --show-current`, `git status`, `date`,
`find` of the store or of `_done`, `sort`, the `sed` calls (status-checked) that read the main
checkout, the handoff name and a handoff's front matter, `mkdir`, `cp` with the copy a regular
file (not a symlink) checked byte for byte, `mv` with the source gone and the destination a
regular file (not a symlink), `cd` into the common git directory
(its output, such as a shell hook's, kept out of the path), and `cmp` in the duplicate check,
where exit 1 means different and exit 2 or more fails the block; the clean-tree filter is done
in the shell, not by `grep`, and all three here-docs that decide a result (the clean-tree check,
the handoff list and the duplicate check against `_done`) end with a sentinel line, so one that
could not be read to its end, such as one zsh could not write, fails the block), when the store,
`_done` or `HANDOFF.md` is a symlink, when the store or `_done` exists but is not a directory or
`HANDOFF.md` exists but is not a regular file, when a `.md` entry at the store's top level is not
a regular file (a symlink, say), when a file archived in the run is no longer a regular file in
`_done` at the end (where the store, `_done` and `HANDOFF.md` are checked for a symlink again,
and `HANDOFF.md` also right before its copy), when a `HANDOFF.md` in the worktree does not name
this branch and worktree, when outside a git repository, and when this session's store file is
still there afterwards. A symlink at those paths is rejected, never followed: `-d` and `-f`
follow one and `find` does not. Before this release a `_done` linked to another directory let a handoff move through the link, the final
listing miss it, and the block print the no-handoff line; with a linked store or `HANDOFF.md`,
or a linked `.md` entry in the store, a handoff could likewise be archived outside the store,
copied from a link's target, or skipped unread. Only the git common directory is resolved
(`pwd -P`), as `dv:handoff` and `dv:pickup` resolve it. Before this release a failed listing of
the store or of `_done` also read as "no handoff". The uncommitted-changes and main-checkout
lines, no output, or Step 4 not run also leave the archive not confirmed. Step 1's recheck
stays the source of the verdict; Step 4's own `git status` only guards the archive.

Step 1 and the Orca block also status-check their reads of the main checkout's path (and Step 1
its reads of the worktree's path, HEAD and branch): a failure makes the verdict `not confirmed
safe` in Step 1 and skips the Orca steps in that block.

Closeout now runs its steps in the order 1, 2, 4, 3, 5, keeping their numbers: the handoff
archive (Step 4) runs before Step 3 writes and saves the note, so the note carries Step 4's
result from the same turn. Where the verdict would otherwise be safe, the note says so, and
names the removal command in its CLEANUP, only when Step 4 printed one of its two success lines.
Where the verdict would otherwise be safe and Step 4 printed anything else, or did not run in
that turn, the note's Worktree line reads `not confirmed safe: handoff archive not confirmed
(…)`; a `NOT safe to delete` or `not confirmed safe` verdict from the checks stays as it is.
When the verdict is "safe once you accept losing" and David has not yet said yes, Step 4 waits
on that yes and the note reads `not confirmed safe: losing … waits on David's yes, and the
handoff archive (Step 4) has not run`; the turn that acts on the yes rechecks, runs Step 4 and
writes the note again. Outside the confirmed case no removal command appears anywhere in the
note. Each run of Step 3 writes the note once and saves one copy, never overwriting an earlier
one. Writing the note again (after a yes, after a recheck that found a change when the saved
note no longer holds, and before every send of the note, a re-send after a failed send included)
reruns Steps 1 and 2 first, and Step 4 where its own gate allows it, and saves a new copy, and
the note sent is the copy saved for that send, in its own turn, named on the message's `Saved
at:` line, since the Director takes the note's time from that file's name. The Director's check
on the note refuses `not confirmed safe`, so it does not ask David to close or release that
session on that note. Known limit, VIL-1209: if the session ends by other means, director-mode's
later removal runs the global removal procedure's checks, which do not read the note.

Skipping the question never stands in for consent to losing data: while the verdict is "safe
once you accept losing", Step 5's question still asks it, and nothing treats the worktree as
safe before that yes. A yes David already gave to a removal question asked before the note was
sent still counts. The README's closeout entry states the new rule, and director-mode's
description of closeout's reply says the same.

## Verification

Live runs used a throwaway clone with linked worktrees and a stub Orca CLI that lists the
worktrees and refuses every removal and send.

- On the final run order (Step 4 before Step 3), 2026-11-26, with a stub `pbcopy` as well, and
  Step 4 as it was before its symlink checks (in these states the final block prints the same
  lines: its first 50 block cases below match the earlier block's line for line):
  - With a stub Director (an interactive closeout session and a stub peer in the clone's main
    checkout that answered the probe with that path) and a handoff in the store, run twice, the
    second time after the pre-push review fixes: Step 4 printed `archive complete: …` before
    each of the two saved copies (the first, saved before the probe, and the one saved for the
    send after Steps 1, 2 and 4 ran again). Both copies say `safe to delete` and name the
    removal command; the copy sent is the second, named on the message's `Saved at:` line. While
    the note waited for the probe's answer, the reply still asked "Remove this worktree now?"
    (in the first run the answer arrived before that turn ended, so there was no such reply).
    The replies after the send ("note sent with no reply yet", "note sent and replied") asked no
    removal question and named the command. They used the wording of that run, which said the
    Director removes the worktree; the reply now says instead that the note went to the peer that
    answered from the main checkout, and that David can run the command if no Director removes
    the worktree (that wording has not been run live).
  - The same with the archive made to fail (`_done` a plain file), also run twice: Step 4
    printed `ARCHIVE INCOMPLETE` before each copy, every copy says `not confirmed safe: handoff
    archive not confirmed (Step 4 printed "…")`, and no note or reply names a removal command,
    says the Director removes the worktree, or asks the removal question (the first run's
    replies asked whether to move `_done` aside; the second asked nothing).
  - With no Director (headless): a safe worktree (run twice, the second time after the pre-push
    review fixes) archived its handoff, saved one copy saying `safe to delete` with the command, and
    ended with "Remove this worktree now?". A worktree with an untracked file saved one copy
    saying `NOT safe to delete`, with no command and the handoff left in the store. A "safe once
    you accept losing" worktree saved one copy saying `not confirmed safe: losing … waits on
    David's yes, and the handoff archive (Step 4) has not run`, with no command, and asked
    "Accept losing …?". After the yes, the recheck matched; in that turn the lab's headless
    permission check refused the Step 4 block, and the copy saved said `not confirmed safe:
    handoff archive not confirmed (Step 4 has not run in this turn)` with no command. In the
    next turn Step 4, run unchanged from a file, printed `archive complete: …`, and the copy
    saved then gave the "safe once you accept losing" verdict and named the command. Each pass
    through the steps saved exactly one copy.
- Earlier wordings were run the same way (the removal question with a stub Director and with no
  Director, twice each; then, after the archive change, a handoff in the store, no handoff, and
  the archive made to fail), with the same removal-question outcomes.
- The final Step 4 block, run on its own in bash and in zsh (`-f`) in a scratch repo, 82 cases
  each, with PATH shims that make one command fail (or, in eight race cases, change a path
  mid-run), with BSD `find`, GNU `find` and bfs (the `find` in Claude Code's shell), and with GNU
  and BSD `mv`, `cp` and `mkdir`, each with the same results: no handoff, a store handoff, a
  rerun after archiving, a matching `HANDOFF.md`, a store handoff with an identical `HANDOFF.md` (and its
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
  the Orca steps. Symlinks: the store, `_done` and `HANDOFF.md` each as a symlink to a directory,
  to a file and dangling (`HANDOFF.md` also to the store's copy), and a `.md` entry in the store
  as a symlink, under the slot's name or another, dangling, or a directory, each printed
  `ARCHIVE INCOMPLETE` with nothing moved or copied; a store symlink not named `.md`, dangling
  symlinks at the destination names, a symlink in `_done` named as an archive (with a matching
  `HANDOFF.md`, and alone), and the common directory given through a symlinked path ended in a
  success line with nothing written through a link; an archive replaced by a symlink right after
  its move or copy, an archive gone from `_done` before the final listing, `_done` swapped for a
  symlink after the move or before the final listing, and `HANDOFF.md` swapped for a symlink
  before its copy, right after it or before the duplicate check each printed `ARCHIVE
  INCOMPLETE`. On the block before these checks, 17 of the 27 cases that now print `ARCHIVE
  INCOMPLETE` ended in a success line instead.
- The Step 3 save block, run on its own in bash and zsh: one run saves exactly one copy; a second
  run adds a new copy and leaves the first unchanged; a name clash in the same second takes a
  `-<n>` name and overwrites nothing.
- Not exercised: a real Director session's checks and removal, a terminal send, a "safe once you
  accept losing" note sent to a Director, a yes given before the note was sent, and the reply's
  final wording after the note's send (the probe proves only the directory).

Refs VIL-932.
