# dv — v0.47.0

Minor release. When a project has open milestones but none fits a ticket, and the groomer has no
concrete milestone to propose, `dv:groom` records "No milestone" with a one-line reason, as a
routine call in `forks-only` mode, instead of asking. Only a concrete proposal (a new milestone's
name and one line on what done means) is asked, as one question: create it, or "No milestone".
Only `dv:groom` changes. The other fifteen skills have no behaviour changes; their version moves to `0.47.0` only
because the suite is released as one plugin.

Numbering: 0.47.0 follows 0.46.0 (VIL-1224, skills PR 127), which has merged.

Why: the "none fits" case was one open decision whose options included creating a milestone, so in
`forks-only` mode from a worktree session the whole decision went to the Head and stayed pending,
even when the outcome was only to leave the ticket out of milestones. The VIL-1212 live check
(2026-11-26) showed a scratch ticket stalled on it (VIL-1214).

## Changed

- **`dv:groom`, step 3, "Milestone", the case "It has no milestone and none fits".** The case
  now names a project that has open milestones but none that fits; a project with no milestones or
  only finished ones still takes the case before it and records nothing, as before. The field stays
  empty and the report says so, as before. Then:
  - A concrete proposal is a new milestone's name and one line on what done means, for a goal the
    ticket's work serves that no open milestone states. The groomer makes one only when it would
    recommend creating it, not to have something to ask.
  - With no concrete proposal, "No milestone" is the call: an add item, the Decisions line "No
    milestone: <one-line reason none fits>". In default mode it is in the edit list like the other
    add items, and approving it records your name. In `forks-only` mode it is a routine call,
    recorded as "Decided by dv:groom (forks-only), <date>".
  - With one, it is one open decision: create the proposed milestone, or "No milestone". The old
    "leave it with none" option is gone. A "No milestone" answer adds "No milestone: <one-line
    reason>" in that answer's form (yours, the Director's or the Head's). No "No milestone" line
    is written before the answer, the milestone is created only on your yes, and from a worktree
    session with a Head the decision goes to the Head and stays pending, as before.
- **`dv:groom`, "Forks-only mode".** "Routine calls" names recording "No milestone" when the
  project has open milestones but none fits and there is no concrete proposal; the Forks list
  names a new milestone as a concrete proposal; "From a worktree session" names that fork's "No
  milestone" answer among what only the Head decides (it was "a new milestone's other options").
- **`dv:groom`, Rules, the no-text-edits bullet.** It lists milestone-field items and says a "No
  milestone" Decisions line is a text edit.
- **`dv:groom`, step 7, the edit list.** The milestone item names the "No milestone" Decisions
  line as an add item that leaves the field empty.
- **README.** The version, and the `dv:groom` entry.

## Known limits

- A "No milestone" line keeps the ticket out of milestones on later grooms (shared rules,
  "Milestones"), also when a milestone that fits is added later. Removing the line lets the next
  groom look again.

## Not in this release

- The shared rules' "Milestones" bullet in `plugins/dv/skills/ticket/references/ticket-format.md`
  is unchanged.
- VIL-996's rule in tickets.md (dotfiles) is a follow-up after the merge.
