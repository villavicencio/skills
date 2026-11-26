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
and reflog-only commits, and the handoff archive did not fail. Otherwise it names none, says why
removal is blocked, and never says the Director removes it. The question stays as before with
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
  the same outcome. The fix round after that review changed only the unsafe, accepted-losses
  and failed-archive cases, which these runs (a safe verdict) do not reach.
- Not exercised: a real Director session's removal, a terminal send, "safe once you accept
  losing", and a yes given before the note was sent.

Refs VIL-932.
