# dv — v0.14.0

Minor release. `dv:manager-mode` checks a ticket before its first hire. The other thirteen skills have
no behaviour changes; their version moves to `0.14.0` only because the suite is released as one plugin.

Why: a stale ticket, or one that already has an open PR, a branch or a running session, cost a whole
engineer run before anyone noticed.

## Changed

- **`dv:manager-mode`** has a new section, "Before the first brief: check the ticket", directly above
  "How to write a brief". The manager runs it once per ticket, whatever the ticket's age, before the
  first hire and so before the In Progress move. It does not run again for fix rounds or reviews. It
  makes three checks: read the ticket's current scope, Done means and discussion; check its
  prerequisites and referenced docs against the repo as it stands; and look for an existing owner,
  meaning work that is not in the manager's written state. The owner lookup uses the ticket's real
  id (and its lowercase form for branches): the ticket's assignee, state and attachments; after
  `git fetch --prune`, `git branch -a --list` and `git worktree list`; `gh pr list --head` for each
  branch found and `gh pr list --search`, both with `--state all --limit 1000`; and the running
  agents and sessions. It finds an owner only where those lookups look. It returns one of three
  verdicts, each with the evidence:
  - `ready`: nothing found and every lookup ran, with what was checked. A lookup that fails or cannot
    run rules `ready` out. Brief and hire.
  - `ready with caveats`: something changed or is unclear, but the work can go ahead as briefed. Brief
    and hire, with the caveats in the brief and in the report to the user.
  - `blocked`: a prerequisite is missing, a decision is open, someone else already owns the work, or
    the ticket is Done, Canceled or Duplicate. No hire. If someone else owns the work, the ticket's
    state stays as it is and the manager reports the owner (the PR, branch or session) to the user.
    For any other blocker the manager moves the ticket to Blocked, using the state name
    `list_issue_statuses` returns for the team; if there is no such state, or the ticket is Done,
    Canceled or Duplicate, it leaves the ticket as it is and says so. It brings the blocker or
    decision to the user with a recommendation. A later hire moves the ticket to In Progress as usual.
- The check is not a grooming gate: no scope growth, no redesign, no reopening a settled decision
  without new evidence. The manager digs deeper only on a concrete concern the check found; anything
  that needs authoring is still a hire.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
