# dv — v0.44.0

Minor release. With a department Head, every wait on one of his Orca items gets one independent,
one-time Orca wake, so a wait whose notice never comes is still looked at again, provided the
wake and its record were both saved. A wait missing either is unarmed: the wake is disabled, the
item stays actionable and the Head says so at once. Only `dv:director-mode` changes. The other fifteen skills have no behaviour changes; their version moves to `0.44.0` only
because the suite is released as one plugin.

Numbering: 0.44.0 follows 0.43.0 (skills PRs 121, 122 and 123 carry 0.42.0, 0.42.1 and 0.43.0 and
merge first). It adds a new procedure, not a fix to an existing one, so it is a minor release.

Why: on 2026-11-26 a Director decision (VIL-932 Q5) sat for 5 h 39 min. The Head's item waited on
progress from a chain that had gone quiet, and nothing woke him until David checked in. Nothing
in the skills told the Head to arm a wake when an item goes to Waiting; he had armed them by hand
(VIL-1218).

## Added

- **`dv:director-mode`, new "Head's wake for a waiting item"**, right after "The Head and the
  CEO's 1%".
  - **Arm:** when the Head puts an item in Waiting on an event someone else owes (an answer, a
    handoff acknowledgement, a merge), he arms exactly one wake with `orca automations create`,
    using `--once`, `--by <wake target>` and `--item <n>` and no `--on`, so it is independent of
    the notice he expects (the full command, with its name and prompt, is in the skill). Before
    it, in that turn, a preflight runs `orca automations trigger-options --bot "<his name>" --json`
    (does the event have an Orca event of its own, or reach him only as mail; recorded as the
    wait's event source) and `orca automations create --help` (the flags, which alone gate the
    arm). He sets two times for each wait: the deadline, the latest a wake may start and
    still count, and an earlier wake target that leaves room for dispatch. The text sets no
    default for either. A wake that starts after the deadline is recorded as a missed deadline.
  - **Verify in the same turn:** a one-time wake shows `nextRunAt: null`, so the check reads
    `enabled: true` and `once.by` equal to the wake target (epoch milliseconds), and the item's
    link reads `on`.
  - **Record:** the item's Waiting note names the wait key `W<k>`, the event, the owner, the wake
    and its deadline; a wait record comment adds the owner's and the waiting session's Orca
    session ids, the ticket, the question's original key (or the PR and its head, or the handoff),
    the original message id, the wake target, the deadline, the full automation id and the
    item's prior note, which the new note replaces. A reread of the item confirms the record. A
    failed or unclear arm or record disables any wake it made, keeps the item In progress
    (actionable) with `Wake: UNARMED` on its record, and is said in that turn's first line, so the
    wait never reads as covered by a timer. Arming again is a new wait, W<k+1>.
  - **On either trigger:** reread the item, the ticket or the PR (in the repository the record
    names) and the current owner. A wake that finds no record of its wait posts the wait as
    unarmed. Before any send, disable or rearm, a current check confirms this W key is the item's
    latest wait and has no disposition; a superseded wait (W1 once W2 exists) is skipped. A send
    or rearm also needs the item still Waiting on the same owner and question or PR head. An item
    that has left Waiting, or whose owner or head changed, gets its pending wake retired and a
    disposition, and no send; an unarmed wait stays In progress and its trigger can arm it again.
    A done, canceled or snoozed item gets a `no follow-up` disposition. Settled means the owner
    acknowledged and the waiting work resumed, shown by the owner's reply or a harness notice (a
    send receipt is not enough). Otherwise re-send under the original key to the same owner and
    session (each re-send noted on the item first; the Head never relays the Director's answer
    himself), after reconciling the original message and any acknowledgement when overlap or a
    restart leaves delivery unclear, or record the exact blocker, owner and next check and arm the
    next wake by the same rules.
  - **Reconcile:** one disposition per wait, as a rule each run follows, not a guarantee. A late
    wake, a repeated notice or a run after a restart is judged against the same record and does
    nothing once a disposition exists. After a restart he takes overdue and unarmed waits as
    triggers.
  - **Retire:** a wake whose wait settled first is disabled
    (`orca automations edit --id <id> --disabled --json`), never removed: `orca automations remove` deletes the run history too. Completed, canceled or
    snoozed items, and waits on a decision reserved for a person, get no follow-up.
  - **The Director's part:** a question the Head re-sends (`Re-sent by the Head`) under its
    original key is answered as that question, to the session that asked it; one that isn't the
    Director's to decide stays with the Head, with its way forward.
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
to catch). Nothing makes a disposition atomic.
