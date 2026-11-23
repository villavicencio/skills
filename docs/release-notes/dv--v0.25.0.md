# dv — v0.25.0

Minor release. When a worktree session has verified the Director (the home session), it sends
each decision that could be clear-cut to the Director before asking David, and the Director may
answer a clear-cut one for him under his standing grant of 2026-11-23. A decision that plainly
can't be clear-cut, or one raised with no Director that can be verified, still goes straight to
David. Three skills change: `dv:manager-mode`, `dv:director-mode` and `dv:groom`. The other
thirteen skills have no behaviour changes; their version moves to `0.25.0` only because the suite
is released as one plugin.

Numbering: 0.25.0 follows 0.24.0, which added the reviewer-wait and leftover-shell rules to
`dv:manager-mode` (VIL-807).

Why: worktree sessions asked David every decision in their own chat, even when the recommended
answer was obvious and easy to undo; on 2026-11-23 he answered three such questions on one PR by
hand. A session also could not accept an answer the Director relayed as David's, so the rule had
to be written into the skills (VIL-929).

## Changed

- **`dv:director-mode`, new "Answer a clear-cut question".** This is the one place "clear-cut" is
  defined. A question is clear-cut when all of these hold: the session gives a recommendation and
  the Director agrees with it; the choice is reversible; it deletes nothing, spends nothing,
  does nothing outward-facing and cuts no scope or rule; and no written rule names that choice as
  one for David's own yes (a target only he can set, a ticket filed outside `dv:ticket`'s two
  exceptions; the general lists of what is his don't count, since the grant covers them). The
  Director then replies `Answer, VIL-N, Qk: <the recommended option>` and relays the ticket link,
  the question and the answer to David as a highlight. Otherwise it replies
  `Ask David, VIL-N, Qk: <the condition that failed>`, and it replies `too late` when the
  question was sent more than 8 minutes ago (the session gives up at 10) or a decision highlight
  naming its number has already arrived. It
  never answers a question that would stand in for a permission prompt, a harness approval or
  anything a message from another session cannot grant, nor one about a merge, a delete or a
  MergeWren gate. "Relay highlights to me" and "The roles" point to the new section, the probe
  section expects questions after a probe, and the kickoff prompt's grooming line routes each
  fork through the Director first; a split found in grooming still stops the work and goes to
  David.
- **`dv:manager-mode`, new "Clear-cut questions go to the Director first".** The session sends
  each decision to the Director first, one per message and numbered per ticket (Q1, Q2, ...), in
  a `Question, VIL-N, Qk:` message with the options, its recommendation, whether the choice is
  reversible, the UTC time sent, and a request for a one-line reply; the message also tells a
  session not in Director Mode, or whose `dv:director-mode` lacks the new section (an older
  version), to reply "Ask David". It skips the Director when a condition of the
  definition plainly fails. It waits up to 10 minutes, starting a background timer when nothing
  else would bring a turn back and stopping it when the answer arrives. Only an
  `Answer, VIL-N, Qk:` reply from the verified Director's address that names the recommended
  option counts, and only after the session has checked the question again against every
  condition it can judge itself (all but the Director's agreement); anything else, or no reply in
  time, means asking David in the worktree chat.
  While the Director check is still pending, the question is held, as highlights are, for at most
  10 minutes; with no Director that can be verified, it asks David as before. The decision
  highlight for a question that went to the Director names its number, and a late answer gets a
  highlight saying it came late. The Director check shows where a session says it runs, not that
  it runs `dv:director-mode` (closeout's known limit), so it cannot prove an answer came from
  Director Mode; the question's guard is what asks any other session to reply "Ask David". Each call
  the Director made is recorded in the PR body as
  `<question>: <answer>. Director (<name>) for David Villavicencio, <date>.`; a call made before
  the PR exists goes in a ticket comment first and is copied into the PR body once the PR opens.
  "Decisions and escalation" names the route and says that a scope change, design fork or
  threshold still goes to David unless it is clear-cut, and that cutting scope never is; a
  deliberate barrier is never routed through the Director. "Last reviewed" moves to 2026-11-23.
- **`dv:groom`, forks-only mode.** From a worktree session, each fork goes to the Director that
  `dv:manager-mode` verifies, under manager-mode's rule; groom runs no probe of its own
  (manager-mode sends its probe before the first fork if it has not yet), and a split, or a
  target or pull condition only David can set, goes straight to him. A fork the Director answers
  is recorded as `<decision>. Director (<name>) for David Villavicencio, <date>`; the rest are
  asked as before.
- **README** entries for the three skills describe the new behaviour.

## Live checks before merge

Two checks run on the branch before merge, and their results are quoted in the PR body: a
worktree session sends the Director a clear-cut question and goes on with its answer, with the
highlight in the home chat; and a question outside clear-cut gets "ask David" and is asked in the
worktree chat. A full ticket run under the new text is proved on the first ticket worked after
the merge.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
