# dv — v0.36.0

Minor release. The Director decides routine calls for David instead of relaying them one at a
time, holds the few that are his until the end of the work without stopping it, and every ask that
does reach him stands on its own. Three skills change: `dv:director-mode`, `dv:manager-mode` and
`dv:groom`. The other thirteen skills have no behaviour changes; their version moves to `0.36.0`
only because the suite is released as one plugin.

Numbering: 0.36.0 follows 0.35.0, which had the Director sweep stale ticket states at session
start.

Why: on 2026-11-24 the dotfiles Director relayed about a dozen decisions to David, most of them
whether to run a third, fourth or fifth MergeWren fix round or to decline a finding. He agreed with
the Director's recommendation in nearly every case. The clear-cut grant of 2026-11-23 ruled those
out ("never one about a merge, a delete or a MergeWren gate"), so every one reached him, often after
he had stepped away, and several asks didn't say which option to pick (VIL-1034).

## Changed

- **`dv:director-mode`, "Answer a worktree session's question"** (was "Answer a clear-cut
  question"). The one copy of the split David set on 2026-11-24:
  - **The Director decides, without asking:** fix rounds (another round, or declining a finding
    with a reason, once it has read the finding and its code at the PR's head; past the two-round
    budget in dotfiles `docs/agents/code-review.md`, the open list comes to the Director, not
    David); merges (after MergeWren and the unresolved-threads check, as before); deletes (only
    the kinds the global standing approvals cover, by their guarded procedures; no new kind of
    delete); cutting scope (reported to David as a highlight); and any other question that is
    clear-cut, under the old conditions less the ones the named kinds replace.
  - **Held for David, never in the way of progress:** declining a high or critical finding on code
    that deletes, handles secrets or sits on another safety boundary, and anything that spends
    money or reaches outside. The Director names a way forward that doesn't need the decision yet
    (fix the finding after all, move the risky part to its own ticket and out of the PR, or park it
    behind a flag that stays off), the rest of the work keeps moving, and the held items go to
    David together once the ticket's other work is done: the session asks them in one interview
    and the Director relays them as one message. With no Director's answer, the session takes a
    way forward that needs no one's yes (fix the finding; don't spend or reach outside yet).
  - The forks `dv:groom` sends straight to David (a split as grooming's verdict, a target, a pull
    condition, a new milestone) stay his.
  - A new reply, `Held for David, VIL-N, Qk: <the way forward>`, beside `Answer` and `Ask David`.
- **`dv:director-mode`, "Every ask that reaches me stands on its own"** (new). Every ask names the
  chat it is in (ticket id and PR), the option to pick by its number and label, one line of why,
  and the opposing view in one line. The Director reads the session's dialog first
  (`orca agent list --worktree "path:<worktree path>"`, then `orca agent read <session id>`) and
  says whether a custom answer is needed. The relay of a decision highlight, closeout `WAITING ON`
  items and the Director's fuller reports use it.
- **`dv:director-mode`, "Merge and clean up".** A stale PR's findings, with no live session, are
  the Director's to decide under the split, not David's.
- **`dv:director-mode` description** is 1,011 characters by VIL-1143's measure (was 1,027), under
  the Agent Skills spec's 1,024 limit. It now names the routine calls the Director decides, and
  drops the stale-PR hiring sentence, which the body still states.
- **`dv:manager-mode`, "Questions go to the Director first"** (was "Clear-cut questions go to the
  Director first"). Points at the director-mode split instead of restating it. The question
  carries the PR and numbered options. On a fix round, a decline, a merge, a delete or cutting
  scope, the session accepts whichever option the Director names; a decline of a high or critical
  finding on a safety boundary counts as held. A `Held for David` reply: the session takes the way
  forward, keeps working, and asks David every held question together at the end, with one
  decision highlight to the Director; a held question moved to its own ticket is also written on
  that ticket as an open decision. Any reply other than `Answer` or `Held for David` counts as
  "ask David". The "Limits" bullet says the Director decides inside the
  merge rules, the standing approvals and the MergeWren gates, and changes none of them.
- **`dv:manager-mode`, "Decisions and escalation".** Drops "cutting scope is never clear-cut".
  After two fix rounds, each open finding goes to a verified Director as a question, where
  code-review.md's "Fix rounds" says to bring David the list (that text changes in dotfiles
  separately, VIL-1058); with no verified Director the list still goes to David. Declining a high
  or critical finding on safety-boundary code is held in any round.
- **`dv:manager-mode`, "Every ask to me stands on its own"** (new bullet). The session's own asks
  to David follow director-mode's self-contained form.
- **`dv:groom`, "From a worktree session: forks go to the Director first"** (was "clear-cut forks
  go …"). Drops "cutting scope never is": cutting scope is the Director's call. A fork the Director
  holds is recorded under Decisions as open and doesn't stop grooming. A split, a target, a pull
  condition or a new milestone still comes straight to David.
- **"Maintaining this text".** `dv:manager-mode` last reviewed 2026-11-25.
- **README.** The `dv:manager-mode`, `dv:director-mode` and `dv:groom` entries state the new split.

## Decisions

- High or critical declines on safety-boundary code, and spending money or reaching outside, go to
  David but must not stop progress; route around them and present them together at the end.
  Merges and deletes: the Director decides. Cutting scope: the Director decides and informs David
  (David Villavicencio, 2026-11-24).
- Every relayed ask names the chat and the exact option to pick (David Villavicencio, 2026-11-24).
- The director-mode description fix (VIL-1143) rides in this release (David, relayed by the
  Director, 2026-11-25).
