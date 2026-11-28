# dv — v0.55.0

Minor release. A PR that passed MergeWren now goes to the Director as a merge handoff that starts
with a record on the ticket. With a Head, his independent wake recovers a missed acknowledgement
through the same Director, or records the PR as held with a named holder and a bounded next check.
Before any merge the Director rechecks the PR's gates fresh, and after it sends the Manager one
report with the landed commit and version. `dv:director-mode` and `dv:manager-mode` change, with
`scripts/head_wait.py` and its tests; the other fourteen skills have no behaviour changes, and
their version moves to `0.55.0` only because the suite is released as one plugin.

Numbering: 0.55.0 follows 0.54.0 (PR 134, merged); no open PR claimed a version when this was
drafted.

Why: on 2026-11-26 skills PR 111 passed review at 12:57 AM PT and merged at 8:40 AM PT. The home
Director was blocked by an open Orca prompt and never acknowledged the worktree session's
handoff, nothing noticed for 7 h 43 min, and the releases behind it waited (VIL-1219).

## Added

- **The merge handoff record** (`dv:manager-mode`, "Highlights", "The merge handoff"). Before it
  hands the PR over, the Manager posts one comment on the ticket per reviewed head and Merger (a
  Merger is its Orca session address, or its name when that is unknown):
  `Merge handoff, VIL-N. Key: <owner/repo>#<N>@<reviewed head>. Repo: … PR: … Reviewed head: …
  Manager: <name>, <Orca session address>. Merger: <the verified Director's name>, <its Orca
  session address, or unknown>. Acknowledge by: <15 minutes later, UTC>.` The Merger is the one
  session that may merge the PR at that head. A later record for the same PR (a new head, or a new
  Director after an announcement) supersedes it; a Director that comes back in the same Orca chat
  keeps the record. The handoff itself goes by SendMessage, names the record's link and asks for
  one line back, `Merge handoff taken, VIL-N: <key>.`; a send that went through, or silence, is not
  that line. A hand-back from the Merger (a `Merge held` reply naming the Manager as holder) ends
  the Manager's wait: it fixes what is named and posts a new record for the new head.
- **The Director's Orca session address.** It outlives a restart of the Director's ListAgents
  name and `from` address, and it is how the Head reaches it. The Director's announcement now
  carries it (`Orca session: orca_session_id:<id>`), and with a Head a Manager that verified the
  Director by probe alone asks for it once (`Director address, VIL-N:`), which the Director
  answers with one line.
- **With a Head, the record is mailed to him** (`--type merge_ready`, once, with the handoff line;
  a failed mail edits the record to start with his `@Orca` mention instead). He arms a wait on the
  PR's open item with `head_wait.py`: key the PR key, owner the record's Merger, waiting session
  the Manager, the wake at the acknowledgement deadline (`dv:director-mode`, "Head's wake for a
  waiting item", "A merge handoff"). At the wake he reads the PR and the replies under the record
  and, after `no-follow-up` as before, takes:
  - `settled`: merged at the reviewed head, and the Manager's `Merge received` reply after it;
  - `re-sent`: the record still the PR's newest, the PR open and unmerged, no acknowledgement from
    the Merger, no `Merge held` reply but his own, both sessions open, and no earlier re-send under
    the key to this Merger. The re-send goes once per key and Merger, to the Merger's Orca session
    address;
  - `not-settled` otherwise (acknowledged but not merged, re-sent and still not acknowledged, a
    hold, merged with no receipt yet, closed or at another head), with the next wait armed as the
    bounded recheck, and his one `Merge held` reply under the record, edited each time, naming the
    holder (the one the Merger's own newest `Merge held` reply names, or else the record's Merger,
    the only session that may merge it), the reason and the next check.

  A later record for the same PR supersedes an earlier one. "Arm" allows one open wait per item,
  so the earlier wait closes `not-settled` ("superseded") at its own wake and the later record's
  wait arms in the same run; with no wait open, it arms at once.

  A re-send's receipt, and Orca's `recipient_delivery_held` warning in it ("Queued behind an open
  prompt"), mean only that the mail is queued in the Merger's chat. No wake, timeout, re-send or
  hold gives any other session the merge.
- **The Director's side** (`dv:director-mode`, "Merge and clean up"). On a handoff, or a `Re-sent
  by the Head` mail with a PR key, it reads the ticket first: the newest record for the PR decides,
  and the PR is its to merge only when that record has the handoff's key and names its own
  `$ORCA_AGENT_SESSION_ID` as Merger (or reads `unknown`, and the handoff the Manager sent it names
  that record's link). It reads the records again just before the merge command. It acknowledges
  once per key, under the record and to the Manager (at the `from` address of the Manager's own
  handoff, or the one ListAgents lists for the worktree session when only the Head's re-send
  reached it). A record that isn't its gets no merge and no acknowledgement. With no record (a PR
  it had updated with no live session, a pilot PR, a session on an older dv), it goes on as
  before, with the recheck; after a stale-PR repair of a PR that has a record, it posts the new
  head's record itself, as Merger, with `Manager: none`.
- **The recheck before every merge,** each gate read fresh just before the merge command: the
  head still the reviewed one (open, not a draft); every CI check `pass` or `skipping` (a pending
  one means not yet); `mergewren_review` exiting 0 with a verdict for that head that "Merging on a
  MergeWren review" allows (mergeable, or every finding fixed or declined as allowed); the
  unresolved-threads query printing nothing; and, in a repo that versions its releases, the
  version at that head still free (above the default branch's and the highest release, with its
  notes file). A gate that fails or can't be read leaves the PR unmerged, with a `Merge held` reply
  under the record naming it and its holder (the Manager, which gets it back, or David when no
  session is live). A timeout, `mergeStateStatus: CLEAN`, a send receipt or the PR's age never
  passes a gate. A Director that must make a handoff wait posts a `Merge held` reply with itself
  as holder and keeps the PR, and it acknowledges every merge handoff that is its own before it
  opens a question card.
- **One merge report per key,** `Merged, VIL-N: <key> landed as <merge commit>, <plugin and
  version, or no version>.`, by SendMessage to the Manager (under the record when neither address
  works). The Manager posts `Merge received, VIL-N. Key: … Landed: …` under the record, its
  receipt, and runs `dv:closeout` on one report per key.
- **`head_wait.py`:** under a PR key, any earlier `Re-send` line under the same key to the same
  owner session (on the item, or along its `Carried from` chain) stops a later re-send, receipt
  or not, so a merge handoff is re-sent once to each Merger (`NOT SENT`, recorded `not settled`).
  A wait under the same key with another owner session (a new Director at the same reviewed head)
  gets its own one. A question or message key keeps the old rule (only an earlier unclear send
  stops it). `unclear_send` is renamed `earlier_send`.

## Tests

`tooling/evals/test_head_wait.py` gains `test_merge_handoff`, run by CI's harness-test step: a
missed acknowledgement re-sent once to the record's Merger under the PR key; no second re-send to
that Merger under that key after a receipt, on the item or along a carry, while a new reviewed
head's key, or a new Merger at the same head, still gets its own one re-send; a re-send Orca
queued behind an open prompt, its `recipient_delivery_held` warning in the first line and the
disposition (the warning's shape read from Orca 1.4.277's `orcad-server.js`); a hold closing `not
settled` and the next wait arming; either session closed stopping the send; two overlapping wakes
sending once; no `gh`, `merge` or `pr` in the script; and the handoff's lines named alike in both
skills. The fake `orca` can now return send warnings. The once-per-key-and-Merger checks fail
against the 0.54.0 script.

## Not tested here

- The Director's recheck, acknowledgement and report are procedure text with no script; the
  disposable live exercise on an isolated target (VIL-1219's Done means) covers them, and has not
  run yet.
- That a `merge_ready` mail to a bot opens a chat as a `question` mail does (Orca 1.4.277 lists
  the type; not sent live).
- That an Orca re-send wakes a Director whose SendMessage handoff went unread: mail to a chat
  behind an open prompt queues until the prompt is answered, so that case stays held.

## Not in this release

- Any way for a session other than the record's Merger to merge a PR: this release allows none.
- The general wake cases for a PR key whose PR closed unmerged or merged at another head, and
  concurrent rewakes (VIL-1265); the merge handoff's own cases above say what a merge handoff's
  wait does with a closed or moved PR.
- Changes to Orca, the Head's SOUL.md or dotfiles.
