# dv — v0.10.0

Minor release. It adds one skill, `dv:ticket`. The other eleven skills have no behaviour changes;
their version moves to `0.10.0` only because the suite is released as one plugin.

## Added

### `dv:ticket`: file or groom a Linear ticket in one format (PR #66)

- **File** (the default): turns a rough request into a full ticket draft with the reason and Done
  means lines that a command or an observation can prove, plus a type block for a bug, research or
  automation ticket. It finds the Linear project and the labels live, checks the facts the draft
  states, and creates the ticket only after you confirm.
- **Groom** (`groom VIL-N`): reads an existing ticket and its comments, lists the gaps against the
  format, verifies the facts the ticket states, brings open decisions to you as a multiple-choice
  interview, and edits the ticket with patches. It does not start the work.
- Linear only. It is not for GitHub issues, and it does not start the work on a ticket.
- The format itself is the dotfiles repo's `docs/agents/tickets.md`. The skill points at that file
  and carries a short fallback for when the file cannot be read.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
