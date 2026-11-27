# dv — v0.48.0

Minor release. `dv:director-mode` gains "Head's wake for a waiting item": when a department Head
puts one of his Orca items in Waiting on an event another session owes him, the wait gets one
independent one-time wake, and every Orca call that arms, checks, closes, retires or reconciles it
goes through a new script, `plugins/dv/skills/director-mode/scripts/head_wait.py`, with offline
tests in `tooling/evals/test_head_wait.py`. The section also tells the Director how to answer a
`Re-sent by the Head` question. Only `dv:director-mode` changes (with the README's entry for it);
the other fifteen skills have no behaviour changes, and their version moves to `0.48.0` only
because the suite is released as one plugin. Checked against Orca 1.4.277.

Why: on 2026-11-26 a Head of Skills item sat Waiting for 5 h 39 min with nothing to wake him
(VIL-1218). The first attempt (skills PR 124, held at `7bb4ad1`) used the item's status as its
lock and put free text into shell arguments; its review showed a stale handler could act twice,
overwrite a later wait or a Needs you, and run text from a wait.

## Added

Each line is one claim the section, the script and its tests establish.

- Each wait W<k> on one of the Head's items gets one one-time wake (`orca automations create
  --once --by <time>`, no event trigger, no `--item`) and two marker links on the item:
  `head-wait/item-<n>/W<k>` when the wait is armed and `head-wait/item-<n>/W<k>-closed` when it is
  closed.
- Orca adds a link only when the item lacks it, in one transaction, and answers `unchanged` to
  every later caller, so two runs can't both arm W<k>: the second gets `TAKEN`, writes nothing
  more and tries no other key.
- The item goes to Waiting only after the create's own output shows the wake enabled, at the
  recorded time, as the Head's bot and with no event trigger, after a fresh read finds the item's
  status and wait unchanged since the arm's first read and W<k> still open, and while the wake's
  time is at least a minute away.
- An arm step that fails after the reservation claims `W<k>-closed`, posts an `UNARMED` line
  naming the step and Orca's error, retires the wake when its id is known, writes no status, and
  says so in the first line. When the wake already holds W<k>, it writes nothing more.
- Only the run whose `W<k>-closed` link returns an event id acts on W<k>. Every other run whose
  claim Orca answers `unchanged`, a late, repeated or manually started wake included, gets
  `NOT CLAIMED` and writes and sends nothing. The exceptions never send: `FULL`, below, and a
  reconciliation's closing record for a wait whose winner stopped.
- A next wait arms only after every earlier wait has its closed marker and a closing record (a
  `Wake disposition` or `UNARMED` line) after it, so a winner that stopped after its claim blocks
  the next wait until its record lands or the Head reconciles it.
- No wake or notice writes the item's status, so a status set while a wait is open stays. Orca
  refuses the arm's Waiting write on a Needs you or closed item.
- A wake whose item is done or canceled stops at its first check, with nothing written. On a
  snoozed item (Orca's snooze, or a `Snoozed until` line whose time is ahead or can't be read) or
  one that reads Needs you, the wake records `no follow-up`, and the script itself refuses to
  re-send.
- `settled` needs the owner's acknowledgement under the original key and the waiting session's
  own turn after it. Every other disposition names its blocker and next check; the script refuses
  a disposition file without those lines.
- The one re-send happens only inside the `close` run that won the claim, after a fresh read of
  the item and of both sessions and after a `Re-send` line is posted. No other command sends.
- A re-send whose answer is an error or can't be read is not sent again: the first line starts
  `SEND UNCLEAR`, and the disposition records `not settled`, blocker `re-send unclear`, and, when
  Orca printed one, its request id with the outcome of one read-only `orca orchestration
  request-show`. A planned re-send that the fresh check stopped starts the first line `NOT SENT`.
- A claim winner starts no write, send or retire once 5 minutes have passed since it claimed, and
  `reconcile --final` (the only other closing record) is refused until 15 minutes after the
  claim, so a reconciliation writes no second disposition while the winner can still post. A
  reconcile note before then records evidence only and unblocks nothing.
- A notice never sends, and closes a wait only as `settled` (then retires its wake; a retire it
  can't confirm starts the first line `RETIRE UNVERIFIED`), or as `not settled` while the wake
  its `Armed` line names reads disabled or gone.
- `retire` reports `RETIRED` only when Orca's answer shows the wake disabled and `GONE` only on
  exactly `Automation not found.`. Any other answer is `UNVERIFIED`, posts a `Retire unverified`
  line and is said in the first line. Once the wait has its closing record, that old wake can
  only read `CLOSED` or get `NOT CLAIMED`, so it doesn't hold up the next wait.
- At Orca's 50-link cap a claim answers `FULL`: the script posts a `Wait blocked` line for the
  wait unless it finds one there, retires the wake, sends nothing, and completes or cancels
  nothing. `arm --carried-from
  <n>/W<k>` arms the work on a fresh item only when the old wait has that line (or is the next
  wait of an item at the cap) and the owner, sessions, ticket and key match its record; the new
  record names the old wait, and the old item gets a `Carried` line only after that arm is
  `ARMED`.
- `restart`, read-only, lists open waits with no record, past their deadline or whose wake is
  disabled or gone; closed waits with no closing record; waits blocked at the cap, carried or
  not; a Waiting note naming a spent or superseded wait; markers another bot linked; and items
  within two links of the cap.
- Free-form text reaches Orca only from files the Head writes, named for their item and wait. The
  wake's name and prompt, the Waiting note and every header line are built from checked values,
  and `orca` runs from an argument list, never through a shell. A value that fails its pattern
  stops the command before any Orca call.
- The Director answers a `Re-sent by the Head` question as the original, under its original key,
  to the session that asked it, and mints no new key.

## Tests

`tooling/evals/test_head_wait.py`, stdlib only and run by CI's harness-test step, runs the
script against a fake `orca` (Orca's JSON envelopes, a link added only when missing under a
lock, faults that fail a call, answer something that isn't Orca's JSON, land and then error,
time out, or pause until released). It checks the outcome words for each Orca answer to a
reservation and a claim; arm's `ARMED`, `TAKEN` and `BLOCKED` cases, two concurrent arms; each
create mismatch closing unarmed with the claim before the `UNARMED` line; the Waiting write
refused, overtaken, after a change, or too close to its target; two overlapping closes with one
send; the reasons the fresh check stops a send (both snooze kinds, Needs you, a closed and
reopened item, either session closed, a `Re-send` line already there or not posting, a failed
read); `NOT SENT`, `SEND UNCLEAR`, `RETIRE UNVERIFIED` and `STOPPED`; the winner's time window; the successor gate with
a winner paused before its disposition; a stale notice with W2 armed or Needs you set in between;
`close-unarmed`, `reconcile` (note, the 15-minute rule, `--final unarmed`); every retire outcome;
FULL, its one line, and carrying to a fresh item, checked and refused; restart reading only and
each finding; and free text with `$(...)`, backticks, both quotes, a backslash, newlines and
non-ASCII reaching Orca byte for byte with nothing run. Fifteen copies of the script, each with one
guard removed, each fail the tests.

## Not guaranteed

- A closing record for every wait: an unclear claim, or a winner that stopped, leaves a wait
  closed without one. The next wait stays blocked until the Head reconciles it from his reads;
  the restart list shows it.
- A check made apart from the send: the fresh read before a re-send and the send are separate
  calls, so a snooze, a Needs you or a session closing between them isn't seen.
- No repeated answer reaching a Manager: a re-send can cross a late answer. That a Manager treats
  an identical second answer as a repeat is assumed.
- A run stopped inside one Orca call (a stopped process, a sleeping machine) can land that call
  after its 5-minute window.
- The item's status after a disposition: the Head's next move is ordinary last-writer-wins, and
  the arm's Waiting write can overwrite a status set in the instant after its last read.
- A wake due while Orca is down should run when Orca returns (the one-time deadline path has no
  missed-run cutoff in Orca's source); not tested.
- Markers surviving a restore of Orca's items database from a snapshot.
- One `Wait blocked` line per wait: two runs that hit FULL at the same moment can each post one,
  since the check for an existing line and the post are separate calls.
- A marker another bot links: the script won't arm past one and the restart list names it, but a
  foreign `W<k>-closed` linked first takes the claim, and that wait then acts on nothing.
- Live behaviour. These lines rest on Orca's source, read-only Orca runs and the offline tests;
  the live tests on disposable items come next, with the Head, and four of them, which put
  scratch items in front of David, wait for his answer. Mail with `--type question` to a session
  address is among the untested.

## Not in this release

- The free-form `--subject` text in "Forward" (VIL-1232).
- Changes to Orca, the Head's SOUL.md or dotfiles.
