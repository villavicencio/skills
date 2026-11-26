# dv 0.42.0

`dv:closeout` no longer asks "remove this worktree now?" once its note has been sent to a
Director its probe verified and the verdict is safe to delete (or a standing yes of David's
covers the losses he accepted, before the note was sent). From the turn the note is sent, in
that turn and every later one, whether or not the Director has replied, the reply says the
Director removes the worktree after the session ends if its checks pass (`dv:director-mode`,
"Take closeout notes" and "End a finished worktree session"), and names the removal command for
David, to run after the session ends. The skill names cases where the Director keeps the
worktree instead: anything under WAITING ON or REPLY NEEDED, or a message from David to the
session after the note.

The removal command itself keeps Step 5's guard. Closeout names one only when the worktree is
safe to delete, or is safe once David accepts losing and he has accepted its build-output lines
and reflog-only commits, and Step 4 confirmed the handoff archive. Otherwise it names none, says
why removal is blocked, and never says the Director removes it.

Step 4 now ends with an explicit success line, `archive complete: this session's handoff is in
<store>/_done`, beside the existing `(no handoff for this session — nothing to archive)`; only
those two confirm the archive. `ARCHIVE INCOMPLETE`, the uncommitted-changes and main-checkout
lines, no output, or Step 4 not run leave it not confirmed. A note closeout sends (by SendMessage
or `terminal send`) keeps a safe verdict only when Step 4 confirmed the archive after Steps 1
and 2 in the turn of the send; the SendMessage path reruns Step 4 before rewriting the note when
Step 2 allows it. Otherwise the sent note's Worktree line reads `not confirmed safe: handoff
archive incomplete or not confirmed (…)`, saved as a new copy under the usual time-stamped name,
and the Director's check on the note refuses it, so the Director does not ask David to close or
release that session on that note. Known limit: if the session ends by other means,
director-mode's later removal runs the global removal procedure's checks, which do not read the
note.

Step 4 also now reports as not confirmed a failed listing of the handoff store or of `_done`
(it used to read as "no handoff"), a store or worktree it cannot resolve, and a `HANDOFF.md` in
the worktree that does not name this branch and worktree. The question stays as before with
no verified Director (no note sent, the note waiting for the probe answers, an answer not
verified, or a note sent only by `terminal send`), when the losses were accepted only in the
session, and when the acceptance came after the note was sent, since the Director's checks then
fail.

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
- The final Step 4 block, run on its own in bash and zsh in a scratch repo: no handoff, a store
  handoff, a rerun after archiving, a matching and a non-matching `HANDOFF.md`, `_done` a plain
  file, and an unreadable store or `_done`. Only the first three and the matching `HANDOFF.md`
  ended in a success line; the rest printed `ARCHIVE INCOMPLETE`.
- Not exercised: a real Director session's checks and removal, a terminal send, "safe once you
  accept losing", and a yes given before the note was sent.

Refs VIL-932.
