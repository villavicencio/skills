# dv — v0.13.0

Minor release. Four skills now keep a Linear ticket's state matching where its work is. The other
ten skills have no behaviour changes; their version moves to `0.13.0` only because the suite is
released as one plugin.

Why: on 2026-11-19 a ticket (VIL-854) sat in Todo after a Manager Mode engineer had started on it.
Nothing moved a ticket when work began before a PR existed, and nothing checked for the mismatch
afterwards. Linear's own PR automation (a per-team setting) cannot be assumed to be set or to have
fired, so these skills check the state and correct it.

## Changed

Four skills compare a Linear ticket's state with its pull requests. Three correct a mismatch and
one reports it (see below). The rule is the same in each:

- no PR yet and work has started, or only draft PRs: In Progress;
- a linked PR is open and awaiting review: In Review;
- every linked PR merged and the ticket finished (every acceptance line true): Done;
- a `Refs` PR merged (it finished only part of the ticket): if the ticket moved to Done, reopen it,
  then set In Review if another linked PR is open and awaiting review, otherwise In Progress
  if work continues now, otherwise Todo.

How the skills apply it:

- **State names, not state types.** They use the state names `list_issue_statuses` returns for the
  ticket's team. In Progress and In Review are both of type `started`, so the type cannot choose
  between them. If a state the rule needs does not exist for the team, the ticket is left as it is
  and the skill's output says so. A ticket that is Blocked, Canceled or Duplicate is left alone and
  reported.
- **PRs from the ticket.** They take the ticket's linked PRs from Linear (`get_issue` returns its
  GitHub PR attachments), and fall back to `gh pr list --state all --search "<VIL-N>"` when there
  are none. Every linked PR counts, open and merged; a PR closed without merging does not.
- **No assumption about Linear's own PR automation.** It may not be set, so each skill checks the
  state.

Per skill:

- **`dv:manager-mode`** fixes the state itself. It moves the ticket to In Progress in the turn it
  hires an engineer, unless the ticket is already In Progress or In Review (a Done, Canceled or
  Duplicate ticket is left alone and reported); to In Review in the
  turn a report says a PR is open; and applies the rule above when a PR merges.
- **`dv:handoff`** (new Step 1b) applies the rule to the session's ticket before the handoff is
  written, moves the state when it differs (when it is unclear whether the PR finished the ticket, it leaves the
  state and asks), and records the ticket, its state and any move in the
  handoff.
- **`dv:closeout`** applies the rule in Step 1 and moves the state when it differs (the state only,
  never the description or checklist), then reads it back and lists the change under TICKETS FILED
  OR CHANGED.
- **`dv:pickup`** applies the rule when the handoff, the branch name or the arguments name a ticket.
  It changes nothing in the tracker: it reports a mismatch under Drift and folds the move into its
  closing offer, and makes the move once the user says go.

Not covered: a session that starts work with no hire and no pickup has no skill step that moves the
ticket; the global instructions cover that case.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
