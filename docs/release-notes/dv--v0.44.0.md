# dv — v0.44.0

Minor release. With a department Head, every wait on one of his Orca items gets one independent,
one-time Orca wake, so a wait whose notice never comes still ends. Only `dv:director-mode`
changes. The other fifteen skills have no behaviour changes; their version moves to `0.44.0` only
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
    handoff acknowledgement, a merge), he arms exactly one wake with `orca automations create
    --bot <his name> --once --by <wake target> --item <n>`, with no `--on`, so it is independent
    of the notice he expects, after a trigger-options preflight in that turn: `orca automations
    trigger-options --bot <his name>` (does the event have an Orca event of its own, or reach him
    only as mail; recorded as the wait's event source) and `create --help` (the flags, which alone
    gate the arm). He sets two times for each wait: the deadline, the latest a wake may start and
    still count, and an earlier wake target that leaves room for dispatch. The text sets no
    default for either. A wake that starts after the deadline is recorded as a missed deadline.
  - **Verify in the same turn:** a one-time wake shows `nextRunAt: null`, so the check reads
    `enabled: true` and `once.by` equal to the wake target (epoch milliseconds), and the item's
    link reads `on`.
  - **Record:** the item's Waiting note names the wait key `W<k>`, the event, the owner, the wake
    and its deadline; a wait record comment adds the owner's and the waiting session's Orca
    session ids, the ticket, the question's original key (or the PR and its head, or the handoff),
    the original message id, the wake target, the deadline and the full automation id. A failed or
    unclear arm keeps the item In progress (actionable) with `Wake: UNARMED` on its record, and is
    said in that turn's first line, so the wait never reads as covered by a timer.
  - **On either trigger:** reread the item, the ticket or PR and the current owner. Before any
    send, disable or rearm, a current check confirms the item still waits on this W key, owner and
    question or PR head; a superseded wait (W1 once W2 exists) is skipped. Settled means the owner
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
  - **Retire:** a wake whose wait settled first is disabled (`orca automations edit --disabled`),
    never removed: `orca automations remove` deletes the run history too. Completed, canceled or
    snoozed items, and waits on a decision reserved for a person, get no follow-up.
  - **The Director's part:** a question the Head re-sends (`Re-sent by the Head`) under its
    original key is answered as that question, to the session that asked it; one that isn't the
    Director's to decide stays with the Head, with its way forward.
  - It grants no decision, merge or CEO's 1% authority.

## Not verified

In Orca 1.4.277: that two runs in one chat never overlap, and what a disabled one-time wake does
once its deadline passes. Nothing makes a disposition atomic. A live test run that ends with one
disposition shows that duplicates were suppressed that time, never that dispositions are atomic
or that runs never overlap.
