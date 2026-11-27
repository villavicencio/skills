# dv — v0.50.0

Minor release. `dv:closeout` now takes a standing yes David already wrote as his answer for the
losses of a "safe once you accept losing" verdict (build-output lines and reflog-only commits),
when that yes names each loss in its own words and every condition it states is shown in the
run (a condition that the session has ended is left for the removal instead). Its handoff archive (Step 4) then runs, the note is written under its case 1 with the
verdict word for word, no loss question is asked, and with a Head the losses are not an open
item. A loss no standing yes covers keeps today's path. Only `dv:closeout` changes. The other
fifteen skills have no behaviour changes; their version moves to `0.50.0` only because the suite
is released as one plugin.

Numbering: 0.50.0 follows 0.48.0, with 0.49.0 held for another open ticket; the version is picked
again at the merge if that changes.

Why: on 2026-11-27 two finished skills worktrees closed out as `not confirmed safe` only because
they would lose `.venv/`, `__pycache__/` and reflog-only superseded commits, which David's
standing yes (memory "Finished worktree removal: standing yes", 2026-11-21) already covers.
Closeout ran no archive until David said yes in that session, and with a Head it made the losses a
CEO's-1% item even when a standing yes covered them, so every finished worktree waited on a yes
he had already given (VIL-1255). David approved the change on 2026-11-27 (Head of Skills item 29),
on the condition that the note quotes his words, their source and their date for every loss and
that every condition they state matches.

## Changed

- **`dv:closeout`, Step 2, new "A standing yes for the losses".** A standing yes covers a listed
  loss (one build-output line, or the reflog-only commits as one) only when all three hold, judged
  in the run and never inferred:
  - **Where:** it is in the global instructions, the project's `AGENTS.md` or `CLAUDE.md` as the
    default branch has them, or memory, read from its file in the run; words that only the
    branch has, or that the session itself wrote or changed, don't count.
  - **What:** its own words name that kind of loss; words that leave it unclear don't cover it.
  - **Conditions:** every condition its words state is shown by Step 1's output or a command run
    in the closeout (for the reflog-only commits, for each commit); one nothing shows doesn't
    match. The one exception is a condition that the session has ended, which can't hold while it
    runs: it is still to be met, the yes covers only a removal after the session has ended, and
    the note names it.

  It gives David's answer only when every listed loss is covered; otherwise all of them wait on
  his yes as before. Each run judges it afresh against its own verdict, and the verdict itself
  does not change.
- **Step 4's gate** runs the archive on such a standing yes, as on David's yes in the session.
- **Step 3.** The note template has a new `Standing yes for <loss>: "<his words>" (<source
  file>, <date>); conditions: …; still to be met at removal: …` line, one per loss, written only
  under case 1 with a standing yes. Case 1 takes a covering standing yes as David's answer, keeps
  the Worktree line as Step 2's verdict word for word (the Director's recheck compares it), and
  puts the condition still to be met (the session has ended) before the removal command in
  CLEANUP. Case 3
  (the losses wait on David's yes) applies only when no standing yes covers every loss.
- **Step 5.** No loss question when a standing yes covers every loss. "Removal cleared" counts a
  covering standing yes, and says with the command when it is only for a removal after the
  session has ended. A loss that no standing yes covers still gets the question, as before. "The probe's peer has the note" and "When the probe's peer has the note, ask
  nothing" take the standing yes the sent note quotes, in place of an acceptance given before the
  note. The recheck lets Step 4 run on a changed verdict when a standing yes covers every loss it
  lists. The reply lists the note's `Standing yes for` lines. "Deliver the note" step 5's Step 4
  gate says the same as Step 4.
- **"Offer the removal"** is never asked when a covering standing yes requires the session to
  have ended: that removal would run inside the session, so the reply names the command instead,
  for a removal after the session has ended.
- **"With a Head".** The losses are a CEO's-1% open item only when no standing yes covers every
  one; "The losses" says there is no losses item then, and an item already open for those losses
  closes once Step 4 prints one of its two success lines.
- **README.** The version, and the `dv:closeout` entry.

## Unchanged

- The verdict, the Worktree line, the fingerprints and the recheck's word-for-word comparison.
- A nested git repository is never build output, and any file outside build output still makes
  the verdict "NOT safe to delete": no standing yes reaches either.
- A loss no standing yes covers keeps every step as it was: the archive waits, the note says
  `not confirmed safe: losing … waits on <name>'s yes`, and the question (with a Head, the losses
  item) is asked.
- `dv:director-mode` is not changed (only its version line moves): its check 1 already accepts
  `safe once you accept losing: …` when a standing yes covers every listed loss.

## Known limits

- **`dv:director-mode`'s "Take closeout notes" still describes the older rule.** Its bullet on
  the removal question says closeout skips it when "a standing yes of mine covers the losses I
  accepted before the note"; closeout now skips it when a standing yes covers every listed loss,
  with no acceptance in the session. That file is being changed under another open ticket, so
  this release leaves it alone.

- **Whether words name a loss, and whether a condition is shown, is the session's judgment.** The
  note quotes the words, their source and date, and how each condition was shown, so the
  Director's check 1 and David can check it; nothing else does.
- **David's standing yes in memory names the losses under its own older wording** (closeout
  called them "NOT safe to delete" when it was written). A session may read that wording as a
  condition the current verdict does not meet, and then the losses wait on his yes as before.
