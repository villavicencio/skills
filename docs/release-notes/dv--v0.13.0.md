# dv — v0.13.0

Minor release. Four skills now deal with a Linear ticket's state. The other ten skills have no
behaviour changes; their version moves to `0.13.0` only because the suite is released as one plugin.

Why: on 2026-11-19 a ticket (VIL-854) sat in Todo after a Manager Mode engineer had started on it.

## Changed

- **`dv:manager-mode`** moves a ticket to In Progress in the turn it hires an engineer for it,
  unless the ticket is already In Progress or In Review, and to In Review in the turn an engineer's
  report says the ticket's PR is open, if Linear has not. It uses the state names
  `list_issue_statuses` returns for the ticket's team; if the team has no state with that name, it
  says so and leaves the ticket as it is.
- **`dv:pickup`, `dv:handoff` and `dv:closeout`** each show the ticket's Linear state beside the
  state of its linked PRs (taken from the ticket's Linear PR attachments, with no GitHub search)
  and flag a mismatch. They point to the Linear rules in the global instructions for what to do
  about it. They move no ticket.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
