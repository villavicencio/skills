# dv — v0.45.0

Minor release. With a department Head, every wait on one of his Orca items gets one independent,
one-time Orca wake, so a wait whose notice never comes is still looked at again, provided the
wake and its record were both saved. A wait missing either is unarmed: it is posted UNARMED with
any wake disabled, the item stays actionable, and the Head says so at once (or, for an arm cut
off part way, when its wake runs). Only `dv:director-mode` changes. The other fifteen skills have no behaviour changes; their version moves to `0.45.0` only
because the suite is released as one plugin.

Numbering: 0.45.0 follows 0.44.0 (skills PRs 121, 122, 123 and 126 carry 0.42.0, 0.42.1, 0.43.0 and
0.44.0 and merged first). It adds a new procedure, not a fix to an existing one, so it is a minor release.

Why: on 2026-11-26 a Director decision (VIL-932 Q5) sat for 5 h 39 min. The Head's item waited on
progress from a chain that had gone quiet, and nothing woke him until David checked in. Nothing
in the skills told the Head to arm a wake when an item goes to Waiting; he had armed them by hand
(VIL-1218).

## Added

- **`dv:director-mode`, new "Head's wake for a waiting item"**, right after "The Head and the
  CEO's 1%". One rule runs through it: visible, not self-healing. A wait is closed (its
  disposition written, then its wake retired) before another is armed, every wait is armed the
  same way, and no step repairs another: a failure is posted on the item, as UNARMED or as the
  blocker, and in the first line of that turn's reply, and the Head decides what comes next.
  - **Arm:** when the Head puts an item in Waiting on an event someone else owes (an answer, a
    handoff acknowledgement, a merge), he arms exactly one wake with `orca automations create`,
    using `--once`, `--by <wake target>` and `--item <n>` and no `--on`, so it is independent of
    the notice he expects (the full command, with its name and prompt, is in the skill). An item
    has one open wait at a time. Before the create, in that turn, a preflight runs
    `orca automations trigger-options --bot "<his name>" --json` (does the event have an Orca
    event of its own, or reach him only as mail; recorded as the wait's event source) and
    `orca automations create --help` (the flags, which alone gate the arm). He sets two times
    for each wait: the deadline, the latest a wake may start and still count, and an earlier wake
    target that leaves room for dispatch. The text sets no default for either. A wake that starts
    after the deadline is recorded as a missed deadline.
  - **Verify in the same turn:** a one-time wake shows `nextRunAt: null`, so the check reads
    `enabled: true` and `once.by` equal to the wake target (epoch milliseconds), and the item's
    link reads `on`.
  - **Record:** the item's Waiting note names the wait key `W<k>`, the event, the owner, the wake
    and its deadline; a wait record comment adds the owner's and the waiting session's Orca
    session ids, the ticket, the question's original key (or the PR and its head, or the handoff),
    the original message id, the wake target, the deadline, the full automation id and the
    item's prior note, which the new note replaces. This write is the only one that sets Waiting, so
    an item is set to Waiting only after its wake is verified; a reread of the item confirms it.
  - **Unarmed:** a failed or unclear flag check, create, verify or record keeps the item In
    progress (actionable) with `Wake: UNARMED` on its record, then disables any wake it made, and
    is said in that turn's first line, so the wait never reads as covered by a timer. Nothing
    creates a second wake for it. What comes next is the Head's call; arming again means closing
    this wait first and arming the next the same way.
  - **On either trigger:** reread the item, the ticket or the PR (in the repository the record
    names) and the owner's session. A notice that finds no record of its wait changes nothing; a
    wake that finds none sends nothing and adds one line: `UNARMED`, also said in the first line,
    on an open item, or `Late wake` on a done, canceled or snoozed one. With no recorded wait
    there is nothing to close, so that item gets no disposition. A wait that already has a
    disposition is left alone, apart from one `Repeat trigger` line that keeps any later evidence.
    A done, canceled or snoozed item whose latest wait is open gets a `no follow-up` disposition
    and is never reopened. A wake that finds its wait open on a Waiting item first moves the item
    to In progress with a `Wake run` line, since nothing armed covers the wait once its wake runs; a
    run cut off before that line can still leave a Waiting item with no wake covering it, which the
    restart list catches.
    A current check (this wait is the item's latest and has no disposition) runs again before each
    send and disposition; a re-send another run adds meanwhile stops this run, while one already
    there when it started leads to `not settled`. Then the first case that fits: settled (the
    event happened and the waiting work acknowledged it and resumed, shown by that session's own
    reply or a harness notice; a send receipt is not enough) closes as `settled`; a changed owner
    or PR head closes as `moved`; a snooze on the ticket, a wait on a decision reserved for a
    person, or an armed wait whose item left Waiting for another reason closes as `no follow-up`,
    said in the first line; an unarmed wait is said in the first line and left to the Head; a
    notice that comes while the wait's wake hasn't started, still verifies and has its deadline
    ahead changes nothing. If the event hasn't happened and the owner and the waiting session are
    live, the run re-sends once under the original key to the same owner and session (noted on the
    item first; the Head never relays the Director's answer himself), and the wait closes as
    `recovered` if that settles it. Anything else closes as `not settled`, naming the exact
    blocker.
  - **Close, then arm:** the disposition comes first and names the blocker and the Head's next
    step (`Next:`); on a Waiting item it also moves the item to In progress, so Waiting always
    means an open, armed wait. Then a wake still enabled is disabled
    (`orca automations edit --id <id> --disabled --json`), never removed:
    `orca automations remove` deletes the run history too. A failed disposition or disable arms
    nothing and is said in the first line. A next wait, only when the Head names one, is armed
    like the first once the disposition is on the item.
  - **Restart:** one disposition per wait, as a rule each run follows, not a guarantee. After a
    restart the Head lists, in the first line, his Waiting and In progress items whose latest wait
    is open or whose `Next:` names a wait with no record, and Waiting items with no open wait. The
    list repairs nothing.
  - **The Director's part:** a question the Head re-sends (`Re-sent by the Head`) under its
    original key is answered as that question, to the session that asked it; one that isn't the
    Director's to decide stays with the Head, with its way forward, and one the Director already
    answered is sent again unchanged under the same key, unless the asking session's chat shows it
    got it.
  - It grants no decision, merge or CEO's 1% authority.

## Live test

The Head ran it on disposable Orca items, with scratch Manager chats, in Orca 1.4.277 (evidence
on VIL-1218). Seen:

- A disabled one-time wake whose deadline passed was still disabled with no runs.
- After a one-time wake ran and Orca retired it, the lookup of its runs returned `Automation not
  found`, so that lookup can't confirm the run afterward; the item's records have to.
- A malformed `--by` was rejected with `invalid_argument` and made no automation and no link. A
  wake that failed the verify was disabled and read back disabled. Both items stayed In progress
  with UNARMED records, said in the first line of that turn.
- One event and wake on one wait, about 20 s apart, ended with one disposition, no re-send and no
  next wake. Whether the two runs overlapped could not be seen; no duplicate came that time, which
  is not atomicity.

## Not verified

That two runs in one chat never overlap, a `--by` in the past, and a real runtime restart (the
restart check was only rehearsed read-only on disposable items, and found no overdue armed wait
to catch). Nothing makes a disposition atomic. A longer outage, or a wake's run cut off part way,
leaves the wait open with no wake (on a Waiting item if cut off before its `Wake run` line); it
is seen again only on the event's notice, when the Head looks at the item, or in the restart
list.

The live test ran on the text before review. These were changed after it and not live-tested:
the reread that confirms a wait record; disposition before disable; an unarmed wait posted
before its wake is disabled; no second create after a create error; how the wait key is counted; the one line for a wake that
finds no record; the `Wake run` move to In progress; the order of the trigger's cases, with the
`moved` and `not settled` dispositions, a snooze on the ticket, and a notice that leaves the
check to a wake still ahead; one re-send per wait, only before the event has happened, and the
Director's re-send of an answer already given; close, then arm, with a next wait only when the
Head names one (the live test's unavailable-owner case armed W2 before W1's disposition); a
disposition moving a Waiting item to In progress; the `Stopped`, `Retire failed` and
evidence-keeping `Repeat trigger` lines; and a restart check that only lists.
