# dv — v0.44.0

Minor release. When a project names a department Head, `dv:closeout` asks David nothing. It sends
its note only to a Director its probe verified, waits up to 10 minutes for that Director's
acknowledgement, keeps each open item on the ticket until what it calls for is done and verified,
and mails the Head each item no acknowledgement took. With no Head, closeout behaves as at dv
0.42.1 and 0.43.0. `dv:closeout` and `dv:director-mode` change; the other fourteen skills have no behaviour
changes, and their version moves to `0.44.0` only because the suite is released as one plugin.

Why: with a Head, closeout's own reply still asked David its questions (accepting losses, the
removal question), and its terminal send reached any agent terminal on the main checkout, with
nothing checking that it was the Director or that the note was read. So a note's open items could
reach neither the Head nor David (VIL-1191; MergeWren's closeout findings on skills PR 111, which
moved this work out of VIL-1178).

## Changed

- **`dv:closeout`, new section "With a Head".** It applies only with a `Head:` line that names a
  `bot:` address, as `dv:director-mode`'s "The Head and the CEO's 1%" defines it, and where it
  and a step differ, it wins (a new rule under "Rules" says so).
  - **Nothing is asked of David.** Accepting the losses of a "safe once you accept losing" verdict
    becomes an open item, one of the CEO's 1%. What the reply's **Needs you:** would hold (a
    ticket-state mismatch included) becomes open items too. No removal question is asked: when
    the removal is cleared, the reply names the command, and the worktree stays until a Director
    removes it after the session ends, or David runs the command. Needs you keeps only what no
    message can grant and what only David's hands can do.
  - **Open items** are the decisions under WAITING ON, whose heading now names the Head, and the
    REPLY NEEDED question, listed there too (`REPLY NEEDED: yes: Qk`). Each is an entry in the
    fields of `dv:manager-mode`'s question message, with its original key `VIL-N/<session
    ID>/Qk`. An item that already has a key (a question the session asked earlier) keeps it; a
    new item takes the session's next unused Qk, and every later copy of the note keeps it.
  - **The record.** Before any probe or send, closeout posts each new item's record on the
    ticket, in `dv:director-mode`'s record form, at a new status, `in closeout note` (nothing
    mailed under its key). An item stays open until a `Closed` reply under one of its records,
    posted only after the action it calls for has been carried out and its result verified in
    the system it changed: by the closeout session while it runs, and after it has ended by the
    Director, which resumes its open items. A send, an acknowledgement or an answer closes
    nothing, and every copy of the note lists the items still open. When an item closes, closeout writes the note again
    and sends that copy. With no ticket, or comments that can't be read or written, an item has
    no record: it stays in every copy of the note (with a ticket, closeout tries again to post
    the record in each later turn), and when delivery fails it is mailed with `Record: none`,
    once, and once more after a send error. With no record there is no Linear fallback mention,
    so the reply says when its delivery is not confirmed. Such an item closes once its action is
    verified; the reply says so and the next copy leaves it out.
  - **Delivery** takes only the chat path in "Deliver the note", as a supervised session already
    does: never a terminal. The message asks for an acknowledgement in a fixed form.
  - **The acknowledgement** is a message from the Director's `from-name` whose first line is
    `Closeout note received, <ticket>: <the saved copy's path>` (for a supervised session, the
    outcome "note sent and replied"), with one line per Qk:
    `Answer, VIL-N, Qk: …` (taken when it counts as `dv:manager-mode`'s "What counts as the
    answer" says) or `Forwarded to the Head, VIL-N, Qk: …` (taken only when the ticket shows a
    record for that original at `sent` or carrying the mention). The wait is closeout's existing
    10 minutes, with the probe's background timer.
  - **Mail to the Head when delivery fails**: no Director verified, the note not sent, or an item
    no acknowledgement took within the 10 minutes. Closeout mails him each such item, one
    message per item, as `dv:manager-mode`'s "With no Director that can be verified" does, and
    keeps its record by the record rules, moving its own record from `in closeout note` to
    `sending` as its claim, then writes the note again so the newest copy marks them
    `Re-sent: yes`. An item an earlier acknowledgement took stays taken. No question card opens.
  - **His answers are advice** (VIL-1193). The losses settle only on David's own yes to the exact
    list, which the session verifies itself as "An approval travels in its own field" says; then
    the recheck, Step 4 and a new note follow as before. A recheck that differs voids that yes.
  - Pointers in Step 3's template, Step 4's gate, Step 5's loss question and Needs you, "Deliver
    the note" and "Offer the removal" name the section. With no Head none of them changes what
    closeout does.
- **`dv:director-mode`.**
  - "A record on the ticket for each Qk": the status `in closeout note`, and a new paragraph, "A
    closeout item": that record is the session's hand-over to the Director that takes the note,
    not a record for the original in step 1; its owner moves it to `sending` only when no
    Director took the item, and for that claim step 1's own-hop-key rule doesn't apply; and the
    `Closed, VIL-N, Qk: …` reply that closes it.
  - "Take closeout notes": with a Head, take each item as a question from the session (decide it
    when it is yours, otherwise forward it), and reply with the acknowledgement form, after the
    forwards. Once the session has ended, the Director resumes its open items and closes those
    whose action it carried out and verified. With a Head, closeout asks no removal question.
  - "His answer": advice on a closeout item goes on the ticket as a reply under its record.
  - "With a Head, nothing else is asked of me": closeout now follows it.
- **`AGENTS.md`'s Head line and the README** (the `dv:manager-mode`, `dv:director-mode` and
  `dv:closeout` entries, and the plugin table, now `0.44.0`) describe the new behaviour in place
  of the interim "until VIL-1191" pointers. The dv 0.39.0 release note keeps them, as history.

## Known limits

- If the closeout session ends during the acknowledgement wait, its records stay at `in closeout
  note`: the items are on the ticket, but no one has confirmed taking them, and nothing mails
  them.
- The Director's check on the note still accepts only a standing yes for losses, so after a yes
  verified through the Head, the removal stays David's: the reply names the command.
- An item with no record whose mail didn't go through is kept only in the note's saved copies
  and in the reply.

## Not tested

No live run yet. VIL-1191's live test on disposable sessions (a note acknowledged by a verified
Director; and with the Director absent or silent, the items reaching the Head with no question
card) runs before merge.

Refs VIL-1191.
