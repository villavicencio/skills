# dv — v0.44.0

Minor release. When a project names a department Head, `dv:closeout` asks David nothing. It sends
its note only to a Director its probe verified, waits up to 10 minutes for that Director's
acknowledgement, keeps each open item open, logged on the ticket where it can be, until what it
calls for is done and verified, and mails the Head each item no acknowledgement took. An item is
the closing session's until that acknowledgement or the session's own mail reads back; no ticket
record counts as delivery. With no Head, closeout behaves as at dv
0.42.1 and 0.43.0. `dv:closeout` and `dv:director-mode` change, and `dv:manager-mode`'s `worker_done` rule; the other thirteen skills have no behaviour changes, and their version moves to `0.44.0` only because the suite is released as one plugin.

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
    ID>/Qk`. An item that already has a key (a question asked earlier on the ticket, by this session or
    one before it) keeps it; a
    new item takes a Qk above every one the session has used and every one the note lists, and
    every later copy of the note keeps it.
    With no ticket, the branch takes the place of `VIL-N` in the key and the `Answer` line.
  - **Delivered.** An item is the closing session's until one of two things reads back: the
    verified Director's acknowledgement takes it, or the session's own mail to the Head, under a
    hop key of its own, returns a message id with no error. No record, pickup note or mention on
    the ticket, and no other session's mail, delivers it.
  - **The ticket log.** Before any probe or send, closeout posts a pickup note on the ticket, in
    `dv:director-mode`'s form, for each item that has none from this session, and reads it back.
    It is a log and the Head's Linear pickup if the session ends first; nothing waits on it or
    skips a send because of it, and a failed post is tried again later. An item stays open until a
    `Closed` reply under its pickup note, posted only after the action it calls for has been
    carried out and its result verified in the system it changed: by the closeout session while
    it runs, and after it has ended by the Director, which resumes its open items. A send, an
    acknowledgement or an answer closes nothing, and every copy of the note lists the items still
    open. When an item closes, closeout writes the note again and sends that copy. With no ticket,
    or comments that can't be written, an item has no pickup note: it stays in every copy of the
    note, and once its action is verified it closes by a `Closed` comment on the ticket, or, when
    none can be posted, in the reply.
  - **Delivery** takes only the chat path in "Deliver the note", as a supervised session already
    does: never a terminal. The message asks for an acknowledgement in a fixed form.
  - **The acknowledgement** is a message from the Director's `from-name` whose first line is
    `Closeout note received, <ticket>: <the saved copy's path>` (for a supervised session, the
    outcome "note sent and replied"), with one line per Qk:
    `Answer, VIL-N, Qk: …` (taken when it counts as `dv:manager-mode`'s "What counts as the
    answer" says) or `Forwarded to the Head, VIL-N, Qk: …` (which the Director sends only once its
    own mail of the item read back; not in a note with no ticket). A line whose Qk fits two listed
    items takes neither. A late acknowledgement still takes its items. The wait is closeout's existing
    10 minutes, with the probe's background timer.
  - **Mail to the Head when delivery fails**: no Director verified, the note not sent, or an item
    no acknowledgement took within the 10 minutes. Closeout mails him each item not yet delivered,
    one message per item, under a new hop key of its own (`VIL-N/<session ID>/Hk`). The mail's
    subject is only the ticket id, the Qk and the words `closeout item`, each identifier checked
    first (`closeout item` alone with no ticket or a failed check); the item's text goes only in
    the body file. No claim on the
    ticket comes first and no record stops it, so `dv:director-mode`'s record steps 1 to 4 don't
    apply. Only the session named in a hop key mails under it, so two sessions never mail under
    one key; the Head can still get one item more than once, each under its own key, all advice. A
    send that returns an error or a result that can't be read gets one more send, in a later turn
    that a background timer brings, under a new key; after that the item stays undelivered. Each
    send's key and result go on the item's entry in the note's saved copies (`Mail:`), which is
    what closeout reads before a send, and its record is posted on the ticket after the send, as a
    log. Then the note is written again, marking those items `Re-sent: yes`. No question card
    opens.
  - **Handed over.** An item's entry reads `Handed over: yes` only when three facts read back:
    the Director's acknowledgement took it with `Forwarded to the Head`, its pickup note is on the
    ticket, and the session owes nothing more on it (not the losses item, no undone action its way forward, an answer or his reply calls for). Such an item stays open but no longer holds the
    session. The session's own mail alone never hands an item over: it gives the item to no
    Director. A read that fails, or an item with no ticket, gives `no`.
  - **His answers are advice** (VIL-1193). The losses settle only on David's own yes to the exact
    list, which the session verifies itself as "An approval travels in its own field" says; then
    the recheck, Step 4 and a new note follow as before. A recheck that differs voids that yes.
  - Pointers in Step 3's template, Step 4's gate, Step 5's loss question and Needs you, "Deliver
    the note" and "Offer the removal" name the section. With no Head none of them changes what
    closeout does.
- **`dv:director-mode`.**
  - "A record on the ticket for each Qk": a new paragraph, "A closeout item". The item stays the
    closing session's until the Director's acknowledgement takes it or the session's own mail
    reads back. Its pickup note is a log and the Head's pickup, never a delivery. The Director
    forwards an item it doesn't decide by its own mail, with closeout's subject (the ticket id and
    the Qk, never the item's text), under its own hop key and outside its record steps, with its
    record posted after the send as a log, and replies `Forwarded to the
    Head` only once that mail returned a message id with no error; otherwise it leaves the line
    out and the session mails the item. The `Closed, VIL-N, Qk: …` reply under the pickup note
    closes it. An item with no ticket has no pickup note, so the Director decides it or leaves it
    for the session to mail. Steps 1 to 4 and the record forms are unchanged.
  - "Take closeout notes": with a Head, take each item as a question from the session (decide it
    when it is yours; otherwise forward it by its own mail), and reply with the acknowledgement
    form, `Forwarded to the Head` for each item its own mail delivered. Once the session
    has ended, the Director resumes its open items and closes those whose action it carried out
    and verified. With a Head, closeout asks no removal question.
  - "His answer": advice on a closeout item goes on the ticket as a reply under its pickup note.
  - "End a finished worktree session", check 1, and the supervised release: with a Head, an item
    marked `Handed over: yes` (and a REPLY NEEDED line naming it) passes only when the Director
    reads the three facts back itself at check time, apart from the Head's mail to the session,
    which only the session reads and for which its own mark stands; a failed or unreadable read
    fails the check, and an item with no ticket never passes.
  - "With a Head, nothing else is asked of me": closeout now follows it.
- **`dv:manager-mode`, "A supervised session"**: `worker_done` gets the same fail-closed exception
  for handed-over items, and with a Head it waits for the reply to the newest copy of the note.
  Its question protocol is unchanged.
- **`AGENTS.md`'s Head line and the README** (the `dv:manager-mode`, `dv:director-mode` and
  `dv:closeout` entries, and the plugin table, now `0.44.0`) describe the new behaviour in place
  of the interim "until VIL-1191" pointers. The dv 0.39.0 release note keeps them, as history.

## Known limits

- An item nothing has delivered when the closeout session ends gets no mail; its pickup note, if
  it landed, gives the Head the item as a Linear pickup, and the note's saved copies keep it.
- The Head can get one item more than once (its pickup note, an earlier send of the question, a
  Director's forward, the session's sends), each under its own key and each as advice.
- The Director's check on the note still accepts only a standing yes for losses, so after a yes
  verified through the Head, the removal stays David's: the reply names the command.
- An item that only the session's mail delivered, or that nothing delivered, is never handed
  over, so it keeps the session from being closed or released through the Director's checks
  until it closes or an acknowledgement takes it.
- A session that stops after a send but before its next saved copy loses that send's result, so
  a later run can mail the item again, even under the same key.

## Not tested

No live run yet. VIL-1191's live test on disposable sessions (a note acknowledged by a verified
Director; and with the Director absent or silent, the items reaching the Head with no question
card) runs before merge.

Refs VIL-1191.
