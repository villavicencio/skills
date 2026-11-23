# dv — v0.30.0

Minor release. `dv:groom` adds the `groomed` label to a ticket, and to each child of a split it
files, only when grooming leaves that ticket ready, setting aside its workflow state and what it
waits on. So on the board, `groomed` means grooming finished with no gap left: no needed fix
declined or missing, every overlap and duplicate search finished, every Done means line provable,
no unconfirmed target, and its points stored. `dv:ticket` allows the label on those children. The
other fourteen skills have no behaviour changes; their version moves to `0.30.0` only because the
suite is released as one plugin.

Numbering: 0.30.0 follows 0.29.0, which made `dv:ticket` set Linear's blocked-by relation when a
filed ticket waits on another, and 0.28.0, which made `dv:groom` point every ticket it grooms in
Fibonacci story points and set Linear's estimate.

Why: the board should show which tickets have been groomed. `dv:groom` wrote a dated grooming line
into Agent notes but never set a label, since step 7 forbade label changes, so the `groomed` label
was applied by hand and drifted (VIL-853).

## Changed

- **`dv:groom` step 7, new edit-list item.** The `groomed` label is its own numbered item, counted
  as an item that adds, added with `addLabels` so the ticket's other labels stay. It is decided last
  (new "Order of writes" item 5), after every other approved item, the estimate included, has
  landed. If step 7 stopped before then, no ticket gets the label. Otherwise `dv:groom` reads the
  ticket again and applies the ready test: step 8 would call it ready, setting aside its state and
  blockers (and, for a split's parent that stays as the parent, that its work sits in its
  children). A ticket with a gap (a needed fix declined or not landed, an unfinished overlap or
  duplicate search, a Done means line that can't be proved, an unconfirmed target, points Linear
  did not store) does not get the label, and the report names the gap. The item is left out when
  the ticket already has the label, and left out (with the reason in the report) when the team has
  no active `groomed` label; the skill never creates the label.
- **Forks-only mode.** The label item is applied with the rest of the edit list, without the
  approval question, including when it is the only item, under the same ready test.
- **Label rule.** "Do not change the state, labels, project, priority or assignee" keeps every
  other label forbidden and names `groomed` as the one exception, allowed only as the ready test
  allows. The estimate rule from 0.28.0
  is unchanged; two lines beside it now say what step 4 already implied: a parent that becomes the
  first child takes that child's size and points, and a split's child is filed with its size and
  points in its Size section.
- **A ticket that needs no other edits.** The last Rules bullet (Size with points, a matching
  estimate, no unapproved 13) no longer leaves it untouched: its text stays as it is, and the edit
  list holds only the label item (asked as usual, or applied without the question in forks-only
  mode), still under the ready test. The grooming line and the no-split line still go in only
  alongside other edits to the text. Forks-only's "Decided without asking" list refers to the
  ticket's text being unchanged in that case.
- **Split children, not spin-offs.** A split's children are filed with their size and points and
  without the label. Once the whole split has landed (children filed, parent changed), `dv:groom`
  gives each child the same ready test and adds `groomed` to each child that passes, when its team
  has the label, in the same last step as the groomed ticket's label. A split that stops before that
  step leaves every label off, so `dv:director-mode`'s kickoff, which skips grooming for a ticket
  that has the label, still grooms those children. The label writes are separate calls and can
  themselves stop part way, so after them, or after an error during them, `dv:groom` reads back the
  groomed ticket and every child it filed, reports each one's labels as read, and names under Needs
  you each ticket it meant to label that lacks the label. A spin-off never gets the label: it is
  drafted, not groomed.
- **Step 8 report.** Says, from the read-back, whether the label was added, already there, or not
  added and why (not approved, no active label, step 7 stopped before it, the ticket is not ready
  and the gap that keeps it so, or the write failed), for the ticket and each child filed, beside
  the size, points and estimate lines from 0.28.0. A ticket that already had `groomed` but is not
  ready now is named under Needs you. When only the label landed, the report says the text is
  unchanged.
- **`dv:ticket` File step 2.** The rule that leaves off workflow-state labels gains one exception:
  `dv:groom` adds `groomed` to a split's child it filed once the split is complete and the child
  passes the ready test; a spin-off never gets it.
- **README.** The plugin table shows `0.30.0`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
