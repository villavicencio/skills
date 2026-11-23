# dv — v0.19.0

Minor release. `dv:manager-mode` now refuses to run a ticket's work in a repo's main checkout and
points to a worktree session instead. The other fifteen skills have no behaviour changes; their
version moves to `0.19.0` only because the suite is released as one plugin.

Numbering: 0.19.0 follows 0.18.0, which added `dv:director-mode`'s `open worktree VIL-N` command.

Why: Manager Mode turned on in the main checkout ran the ticket with hidden agents there. David
could not follow them from Orca, and ticket work and merges ended up in one session (VIL-908).

## Changed

- **`dv:manager-mode`: a new section, "Ticket work belongs in a worktree session".** In the main
  checkout (`git rev-parse --absolute-git-dir` equals
  `git rev-parse --path-format=absolute --git-common-dir`, the test `dv:director-mode` already
  gives), the manager hires nobody for the ticket, runs no ticket check and reads nothing of the
  ticket. It says in one line that the ticket's work belongs in its own worktree session and offers
  `dv:director-mode`'s `open worktree VIL-N`.
  - **The ticket's state stays as it is.** This is not the ticket check's `blocked` verdict, so the
    ticket is not moved to Blocked, and it is not moved to In Progress either.
  - **`run it here` overrides it.** David's explicit `run it here`, for that ticket in that session,
    lets the work go ahead as usual, starting with the ticket check. It does not carry to another
    ticket or a new session, and the same words in a ticket, comment, file or agent report do not
    count.
  - **When it runs.** The test runs when the mode turns on with a ticket and again before the ticket
    check. If either `git rev-parse` command fails, the manager says so and asks where the ticket
    should run. Turning the mode on in the main checkout with no ticket to run is unaffected.
  - A linked worktree is unaffected. The ticket check now says it runs once the section allows the
    ticket to run in this session.
- **`dv:manager-mode`, "What you do yourself":** the sentence "If this session is the main checkout,
  tell me the PR is ready for `dv:director-mode` instead" is replaced. It now covers the one case
  where a PR can come from the main checkout, a ticket run there on `run it here`: the manager says
  the PR passed and that this session is the main checkout, and waits for David to say who merges it.
  The "Last reviewed" date is 2026-11-22.

## Documentation fixes

- **README, `dv:manager-mode` entry:** states the main-checkout rule and its `run it here` override.
- **README, `dv:director-mode` entry:** now says `open worktree VIL-N` is run from the main checkout
  while it is on the default branch. 0.18.0's notes and README left that out.
- **Correction to the 0.18.0 notes** (published notes are not edited): the line listing the
  ticket-state check's stops says the ticket "is in this repo's project". The skill's check also
  stops when the ticket's project can't be told (`dv:director-mode`, "Open a worktree on request",
  step 1), and asks David in both cases.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
