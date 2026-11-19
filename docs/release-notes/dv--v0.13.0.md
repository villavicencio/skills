# dv — v0.13.0

Minor release. Four skills now keep a Linear ticket's state matching where its work is. The other
ten skills have no behaviour changes; their version moves to `0.13.0` only because the suite is
released as one plugin.

Why: on 2026-11-19 a ticket (VIL-854) sat in Todo after a Manager Mode engineer had started on it.
Nothing moved a ticket when work began before a PR existed, and nothing checked for the mismatch
afterwards. Linear's own PR automation (a per-team setting) cannot be assumed to be set or to have
fired, so these skills check the state and correct it.

## Changed

The rule, in each skill's own words: no PR yet and work started, In Progress; PR open and under
review, In Review; PR merged and the ticket finished, Done; PR merged but only part of the ticket
finished (a `Refs` PR), reopen it. State names come from `list_issue_statuses` for the ticket's
team; a team with other names is handled by state type.

- **`dv:manager-mode`**: the manager moves the ticket to In Progress in the turn it hires an
  engineer for it, to In Review in the turn a report says a PR is open, and compares state with PR
  when a merge is reported. It fixes the state itself.
- **`dv:handoff`**: a new Step 1b compares the session's ticket with its PR before the handoff is
  written, fixes the state, and records it in the handoff. It fixes the state itself: the session's
  own work is what the state describes.
- **`dv:closeout`**: the ticket check in Step 1 compares state with PR and fixes the state (the
  state only, never the description or checklist), and lists the change under TICKETS FILED OR
  CHANGED. A merged PR does not make the ticket Done while an acceptance line is untrue.
- **`dv:pickup`**: the Step 3 cross-check compares state with PR and reports a mismatch as drift,
  with the move that would fix it in the closing offer. It does not change the tracker: pickup reads
  and orients, and no work has started yet.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
