# dv — v0.13.0

Minor release. Four skills now keep a Linear ticket's state matching where its work is. The other
ten skills have no behaviour changes; their version moves to `0.13.0` only because the suite is
released as one plugin.

Why: on 2026-11-19 a ticket (VIL-854) sat in Todo after a Manager Mode engineer had started on it.
Nothing moved a ticket when work began before a PR existed, and nothing checked for the mismatch
afterwards. Linear's own PR automation (a per-team setting) cannot be assumed to be set or to have
fired, so these skills check the state and correct it.

## Changed

Four skills compare a Linear ticket's state with its pull requests and the ticket's acceptance
lines (its Done means). Three correct a mismatch and one reports it (see below). The decision is
the same in each, in order, and the first match wins:

1. a linked PR is open and awaiting review (a draft PR is not, and counts as work continuing):
   In Review;
2. otherwise, at least one linked PR has merged and every acceptance line is true: Done;
3. otherwise, work continues now: In Progress;
4. otherwise: Todo.

A ticket in Done whose acceptance is not all true is reopened by this decision, whatever words its
PRs used (`Refs` or `Fixes`). A ticket in Done whose acceptance is all true stays in Done. A ticket
in Backlog stays there until its pull condition is met and
work starts, and a `someday` ticket's state is not changed.

How the skills apply it:

- **State names, not state types.** They use the state names `list_issue_statuses` returns for the
  ticket's team. In Progress and In Review are both of type `started`, so the type cannot choose
  between them. If a state the decision needs does not exist for the team, the ticket is left as it
  is and the skill's output says so. A ticket that is Blocked, Canceled or Duplicate is left alone
  and reported.
- **PRs from two sources, always.** The skills take the union of the PR attachments Linear returns
  with the ticket (`get_issue`) and `gh pr list --state all --search "<VIL-N>" --limit 1000`, and
  keep only search results whose head branch, title or body names the ticket id. Every linked PR
  counts, open and merged; a PR closed without merging does not.
- **No assumption about Linear's own PR automation.** It may not be set, so each skill checks the
  state.

Per skill:

- **`dv:manager-mode`** fixes the state itself. It moves the ticket to In Progress in the turn it
  hires an engineer, unless the ticket is already In Progress or In Review (a Done, Canceled or
  Duplicate ticket is left alone and reported); to In Review in the turn a report says a PR is
  open; and applies the decision above when a PR merges (a Done ticket is reopened only then).
- **`dv:handoff`** (new Step 1b) applies the decision to the session's ticket before the handoff is
  written and moves the state when it differs. When it is unclear whether every acceptance line is
  true, it leaves the state and asks. It records the ticket, its state and any move in the handoff.
- **`dv:closeout`** applies the decision in Step 1 and moves the state when it differs (the state
  only, never the description or checklist), then reads it back and lists the change under TICKETS
  FILED OR CHANGED. When it is unclear whether every acceptance line is true, it changes nothing
  and asks. Its older check for this branch's own PRs is about whether the worktree is safe to
  delete, not about ticket state, and is unchanged.
- **`dv:pickup`** applies the decision when the handoff, the branch name or the arguments name a
  ticket. It changes nothing in the tracker: it reports the result under Drift (or, when it is unclear
  whether every acceptance line is true, reports that and proposes no move) and folds the move
  into its closing offer, and makes the move once the user says go.

Not covered: a session that starts work with no hire and no pickup has no skill step that moves the
ticket; the global instructions cover that case.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
