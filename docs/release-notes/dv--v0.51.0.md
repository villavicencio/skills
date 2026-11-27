# dv — v0.51.0

Minor release. `dv:director-mode` gains "Head's wake for a waiting item": when a department Head
puts one of his Orca items in Waiting on an event another session owes him, the wait gets an
independent one-time wake (a `rewake` replaces one that is lost), and every Orca call that arms,
checks, closes, retires, reconciles or rewakes it goes through a new script,
`plugins/dv/skills/director-mode/scripts/head_wait.py`, with offline tests in
`tooling/evals/test_head_wait.py`. The section also tells the Director how to answer a `Re-sent by
the Head` question. Only `dv:director-mode` changes (with the README's entry for it); the other
fifteen skills have no behaviour changes, and their version moves to `0.51.0` only because the suite
is released as one plugin. Checked against Orca 1.4.277.

Numbering: 0.51.0 follows 0.50.0. 0.49.0, which this work held, stays unreleased: 0.50.0
merged first, and a release can't go below the highest one.

Why: on 2026-11-26 a Head of Skills item sat Waiting for 5 h 39 min with nothing to wake him
(VIL-1218). The first attempt (skills PR 124, held at `7bb4ad1`) used the item's status as its
lock and put free text into shell arguments; its review showed a stale handler could act twice,
overwrite a later wait or a Needs you, and run text from a wait.

## Added

Each line is one claim the section, the script and its tests establish.

- Each wait W<k> on one of the Head's items gets a one-time wake (`orca automations create --once
  --by <time>`, no event trigger, no `--item`; `rewake` adds another only when it is lost) and two
  marker links on the item: `head-wait/item-<n>/W<k>` when the wait is armed and
  `head-wait/item-<n>/W<k>-closed` when it is closed.
- Orca adds a link only when the item lacks it, in one transaction, and answers `unchanged` to
  every later caller, so two runs can't both arm W<k>: the second gets `TAKEN`, writes nothing
  more and tries no other key.
- An arm needs the wake's time at least 2 minutes ahead and the deadline at least 5 minutes after
  it. An owner address `orca_session_id:<id>` must name the `--owner-session`.
- The item goes to Waiting only after the create's own output shows the wake enabled, at the
  recorded time, as the Head's bot and with no event trigger, after a fresh read finds the item's
  status and wait unchanged since the arm's first read and W<k> still open, and while the wake's
  time is at least a minute away. A Waiting write whose answer can't be read is read back; when that
  read fails too, the first line starts `ARM UNCLEAR`, the script posts an `Arm unclear` line naming
  the wake (the first line says so if it doesn't post) and writes nothing more: no claim, no
  `UNARMED` line, no retire (with `--carried-from`, the old item still gets its `Carried` line).
  Check, rewake, restart, retire and a notice's close count that line's wake as the wait's wake, as
  they do an `Armed` line's. The wake stays armed, and its own run's `check` and `close` handle the
  wait whether or not the item went Waiting. After a Waiting write that landed, a read that fails
  starts the first line `UNCHECKED`; one that finds `W<k>-closed` already linked starts it `SPENT`.
- Any other arm step that fails after the reservation, a Waiting write that a read-back shows didn't
  land included, claims `W<k>-closed` and, once it wins that claim, posts an `UNARMED` line naming
  the step and Orca's error, retires the wake when its id is known, writes no status, and says so in
  the first line. A claim it doesn't win posts no `UNARMED` line: `NOT CLAIMED` (the wake or another
  run holds W<k>) writes nothing more; `FULL` posts the `Wait blocked` line and `CLOSED` (the item
  closed meanwhile) nothing, and each then retires a wake whose id it knows (one it can't confirm
  gets a `Retire unverified` line); any other answer says to reconcile. A won claim whose `UNARMED`
  line doesn't post, or whose run is past its 5-minute window before that line, starts the first
  line `UNCLEAR`.
- Only the run whose `W<k>-closed` link returns an event id sends for W<k> or posts its closing
  record. Every other run whose claim Orca answers `unchanged`, a late, repeated or manually started
  wake included, gets `NOT CLAIMED` and writes and sends nothing. The exceptions never send: `FULL`,
  below, a reconciliation's closing record for a wait whose winner stopped, and `rewake`.
- A next wait arms only after every earlier wait has its closed marker and a closing record (a
  `Wake disposition` or `UNARMED` line) after it, so a winner that stopped after its claim blocks
  the next wait until its record lands or the Head reconciles it.
- No wake or notice writes the item's status, so a status set while a wait is open stays. Orca
  refuses the arm's Waiting write on a Needs you or closed item.
- A wake whose item is done or canceled stops at its first check, with nothing written. On a
  snoozed item or one that reads Needs you, the wake records `no follow-up`, and the script
  itself refuses to re-send. Snoozed means Orca's snooze, or the latest `Snoozed until` comment
  on the item, by anyone and of any age, while its time is ahead, has no time zone or can't be
  read, and no `Unsnoozed` comment from the Head's bot or the item's owner follows it.
- `settled` needs the owner's acknowledgement under the original key and the waiting session's
  own turn after it. Every other disposition names its blocker and next check; the script refuses
  a disposition file without those lines.
- The one re-send happens only inside the `close` run that won the claim, after a fresh read of
  the item and of both sessions and after a `Re-send` line is posted. No other command sends.
- No re-send goes out under a key while an earlier wait under that key, on the item or along
  its `Carried from` chain (up to 5 items), has a `Re-send` line and no `Sent: msg_` receipt in
  its closing record.
- A re-send whose answer is an error or can't be read is not sent again: the first line starts
  `SEND UNCLEAR`, and the disposition records `not settled`, blocker `re-send unclear`, and, when
  Orca printed one, its request id with the outcome of one read-only `orca orchestration
  request-show`. A planned re-send that the fresh check stopped starts the first line `NOT SENT`.
- A claim winner starts no write, send or retire once 5 minutes have passed since it claimed, and
  `reconcile --final` (the only other closing record) is refused until 15 minutes after the
  claim, so a reconciliation writes no second disposition while the winner can still post. A
  reconcile note before then records evidence only and unblocks nothing. Two `--final` runs at
  once can each post; the later prints `DUPLICATE`, and the first record counts.
- The script lets a notice or a look close only as `settled` (then retires the wait's wake; a
  retire it can't confirm starts the first line `RETIRE UNVERIFIED`), or as `not settled` while
  the wait's latest wake reads disabled or gone, and never send. The Head passes `--trigger wake`
  only in the wake's own run; the script can't tell the two turns apart.
- `retire` edits only a wake that one of the wait's own lines names (`Armed`, `Arm unclear`,
  `Rewake`, `UNARMED` or `Retire unverified`); any other id is `REFUSED`, and an item it can't read
  `UNREADABLE`, with nothing edited. It reports `RETIRED` only when Orca's answer shows the wake
  disabled and `GONE` only on exactly `Automation not found.`. Any other answer is `UNVERIFIED`,
  posts a `Retire unverified` line and is said in the first line. Once the wait has its closing
  record, that old wake can only read `CLOSED` or get `NOT CLAIMED`, so it doesn't hold up the next
  wait.
- `rewake` gives a wait with no closing record and no wake still due one new one-time wake 16
  minutes out, checked as an arm checks its wake, and posts a `Rewake` line naming it; it links
  nothing. A wait reserved with no record is refused and goes to `close-unarmed`. The wake's run
  uses it when its first check can't read the item, and the Head uses it after any `UNREADABLE`
  or `UNCLEAR` first line. When it can't make or record one, its first line starts `UNCOVERED` or
  `UNRECORDED`.
- `rewake` makes nothing while the item holds the wait and no wake is due, by the fresh check's
  item rules that end (Needs you, Orca's snooze, a `Snoozed until` line); its first line starts
  `HELD` and says why. It doesn't hold on the send-only rules (an earlier unclear send under the
  key, a `Re-send` line, a closed session) or on an item closed and reopened after the record,
  which never ends and which the wake itself closes as `no follow-up`.
- A wait gets at most 8 rewakes, even when runs overlap or a create's answer is uncertain. Each run
  posts a `Rewake claim` line before it creates anything and creates only when fewer than 8 claims
  came before it in Orca's event order, and only when its read of the item after the claim shows no
  hold (a hold seen there prints `HELD`, a closed item or a closing record `CLOSED`, and either
  spends the claim); the loser prints `NOT CLAIMED`, and a claim counts whether or not its create
  succeeded. Orca writes each comment in its own serialized transaction with an increasing event id,
  so a run that reads the item after its own claim lands sees every earlier claim. Claims are
  comments, not links, so the 50-link budget and the waits an item holds are unchanged.
- An Orca call stops after 60 s and starts only while those 60 s fit in the command's first 9
  minutes, so a 10-minute tool timeout covers every command. A command's first read of the item is
  tried up to 3 times, 15 s and then 45 s apart, when Orca's error can pass, and a read that shows a
  marker link without its `linked` event (Orca's show reads the events before the item) is read
  again at once, twice at most; a third such read counts as a failed read that can pass.
- At Orca's 50-link cap a claim answers `FULL`: the script posts a `Wait blocked` line for the
  wait unless it finds one there, retires the wake, sends nothing, and completes or cancels
  nothing. `arm --carried-from <n>/W<k>` arms the work on a fresh item only when the old item is
  the same bot's, the old wait has that line (or is the next wait of an item at the cap), and, when
  the old wait has a record, the owner, sessions, ticket and key match it; a wait with no record is
  matched against nothing. The new record names the old wait, and the old item gets a `Carried`
  line once the new item is set Waiting or its arm ends `ARM UNCLEAR`.
- `restart`, read-only, reads every open item and each done or canceled item whose listed links
  show one of its markers. On an open item it lists waits reserved with no record; open waits past
  their deadline or whose wake isn't enabled (disabled, gone, unreadable or none recorded); closed
  waits with no closing record; waits blocked at the cap, carried or not; a stray `W<k>-closed`; a
  Waiting note naming a spent, superseded or unmarked wait; and, on an item with waits, two or
  fewer free links. On a done or canceled item it lists each wait with no closing record, claimed
  or not, and a stray `W<k>-closed`. An item it can't read, or an item list cut at its page limit,
  starts the first line `INCOMPLETE RESTART`.
- Free-form text reaches Orca only through files, never a command line: the Head's, named for
  their item and wait, and the script's own lines, which quote Orca's error text. The wake's name
  and prompt, the Waiting note and every header line are built from checked values, and `orca`
  runs from an argument list, never through a shell. A value that fails its pattern stops the
  command before any Orca call.
- The Director answers a `Re-sent by the Head` question as the original, under its original key,
  to the session that asked it, and mints no new key.

## Tests

`tooling/evals/test_head_wait.py`, stdlib only and run by CI's harness-test step, runs the script
against a fake `orca` (Orca's JSON envelopes, a link added only when missing under a lock, events
paged 50 at a time, faults that fail a call, answer something that isn't Orca's JSON, land and then
error, time out, hide a link's event from one read, or pause until released). It checks the outcome
words for each Orca answer to a reservation and a claim; arm's `ARMED`, `TAKEN`, `BLOCKED`,
`UNREADABLE`, `UNCHECKED`, `SPENT` and `OVERTAKEN` cases and two concurrent arms; the values refused
before any call, the deadline gap and the owner's session among them; each create mismatch closing
unarmed with the claim before the `UNARMED` line; the Waiting write refused, after a change, or too
close to its target, or unclear with a failed read-back (`ARM UNCLEAR`, landed or not, then the
wake's own check and close, its wake counted as the wait's, and a carry's `Carried` line); two
overlapping closes with one send; each reason the fresh check stops a send (both snooze kinds, an
old undated snooze line, a person's snooze line, `Unsnoozed`, Needs you, a closed and reopened item,
either session closed, a `Re-send` line already there or not posting, an earlier wait's unclear send
under the same key here or on the item it was carried from, a failed read); `NOT SENT`,
`SEND UNCLEAR`, `RETIRE UNVERIFIED` and `STOPPED`; the winner's time window; the successor gate with
a winner paused before its disposition; a stale notice with W2 armed or Needs you set in between;
`close-unarmed` and its second read; `reconcile` (note, the 15-minute rule, `--final unarmed`, two
at once, a failed read after); every retire and rewake outcome, a retire or
`close-unarmed --wake-id` of a wake that isn't the wait's refused with nothing edited, each rewake
hold with no create call, a hold that lands while the claim posts (a snooze line, Needs you)
spending the claim with no create call, and two rewakes that each read seven claims, of which
exactly one creates; the first read's three tries and the spent budget; items with more than 50
events; a marker link missing its event in three reads; FULL, its one line, and carrying to a fresh
item, checked and refused; restart reading only, each finding, done and canceled items, and a list
cut at its page limit; a cleanup failure after a send; and free text with `$(...)`, backticks, both
quotes, a backslash, newlines and non-ASCII reaching Orca byte for byte with nothing run.

## Not guaranteed

- A closing record for every wait: an unclear claim, or a winner that stopped, leaves a wait
  closed without one. The next wait stays blocked until the Head reconciles it from his reads;
  the restart list shows it.
- A wake for every wait: a run killed before it can rewake, or Orca's items unreadable for longer
  than a command's three tries and then the rewake's, leaves a wait with no wake; the restart list
  shows it. A rewake that a hold stopped (`HELD`) leaves the wait with no wake until the Head
  rewakes it after the hold ends.
- No wake made after a hold: Orca's snooze, a `Snoozed until` line or Needs you arriving after
  rewake's read after its claim can still race the create.
- One closing record per wait: two `reconcile --final` runs at once can each post one; the
  later prints `DUPLICATE`, and the first counts.
- The per-key check beyond the item's `Carried from` chain: the same key armed again on an
  unrelated item isn't checked.
- A check made apart from the send: the fresh read before a re-send and the send are separate
  calls, so a snooze, a Needs you or a session closing between them isn't seen.
- That an open session reads its mail: open means Orca on this host lists a place for it. A
  session on another host reads as not open (assumed, not tested), so nothing is re-sent across
  hosts. An owner address of another kind than `orca_session_id:<id>` isn't checked against the
  owner's session.
- No repeated answer reaching a Manager: a re-send can cross a late answer. That a Manager treats
  an identical second answer as a repeat is assumed.
- A run stopped inside one Orca call (a stopped process, a sleeping machine) can land that call
  after its 5-minute window.
- The item's status after a disposition: the Head's next move is ordinary last-writer-wins, and
  the arm's Waiting write can overwrite a status set in the instant after its last read.
- A wake due while Orca is down should run when Orca returns (the one-time deadline path has no
  missed-run cutoff in Orca's source); not tested.
- Markers surviving a restore of Orca's items database from a snapshot.
- A complete restart list on a bot with many items: `restart` reads every open item and every
  done or canceled item with a marker on each run, so it can run out of its 9 minutes and print
  `INCOMPLETE RESTART`.
- One `Wait blocked` line per wait: two runs that hit FULL at the same moment can each post one,
  since the check for an existing line and the post are separate calls.
- A marker linked by hand: the script trusts any marker it finds, so a `W<k>-closed` linked
  first by anyone takes the claim.
- Live overlap. The live cases ran on disposable items at `07e2d0f` and passed, some only in part
  (skills PR 130 lists each), but no two runs overlapped live: T10, T16(a), T20 and T23 rest on the
  offline tests, as do T5 and T22's hold landing after the claim, and T12(c), Orca's own snooze, was
  excluded. What changed after `07e2d0f` other than the 5-minute deadline gap (the own-wake checks
  on `retire` and `close-unarmed --wake-id`, `restart` on closed items, `ARM UNCLEAR`) is tested
  offline only.

## Not in this release

- The free-form `--subject` text in "Forward" (VIL-1232).
- Changes to Orca, the Head's SOUL.md or dotfiles.
