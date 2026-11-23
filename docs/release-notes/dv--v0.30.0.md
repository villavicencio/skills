# dv — v0.30.0

Minor release. `dv:groom` adds the `groomed` label when it applies a ticket's grooming, and to
the children of a split it files once the split is complete. `dv:ticket` allows that label on
those children. The other fourteen skills have no behaviour changes; their version moves to
`0.30.0` only because the suite is released as one plugin.

Numbering: 0.30.0 follows 0.29.0, which made `dv:ticket` set Linear's blocked-by relation when a
filed ticket waits on another, and 0.28.0, which made `dv:groom` point every ticket it grooms in
Fibonacci story points and set Linear's estimate.

Why: the board should show which tickets have been groomed. `dv:groom` wrote a dated grooming line
into Agent notes but never set a label, since step 7 forbade label changes, so the `groomed` label
was applied by hand and drifted (VIL-853).

## Changed

- **`dv:groom` step 7, new edit-list item.** The `groomed` label is its own numbered item, counted
  as an item that adds, added with `addLabels` so the ticket's other labels stay. It goes on last
  (new "Order of writes" item 5), after every other approved item, the estimate included, has
  landed, so a grooming that stops before it, or leaves an approved item for David to edit in
  Linear (a description with no headings), leaves the label off. It is left out when the ticket
  already has the label, and left out (with the reason in the report) when the team has no active
  `groomed` label; the skill never creates the label.
- **Forks-only mode.** The label item is applied with the rest of the edit list, without the
  approval question, including when it is the only item.
- **Label rule.** "Do not change the state, labels, project, priority or assignee" keeps every
  other label forbidden and names `groomed` as the one exception. The estimate rule from 0.28.0
  is unchanged; two lines beside it now say what step 4 already implied: a parent that becomes the
  first child takes that child's size and points, and a split's child is filed with its size and
  points in its Size section.
- **A ticket that needs no other edits.** The last Rules bullet (Size with points, a matching
  estimate, no unapproved 13) no longer leaves it untouched: its text stays as it is, and the edit
  list holds only the label item (asked as usual, or applied without the question in forks-only
  mode). The grooming line and the no-split line still go in only alongside other edits to the
  text. Forks-only's "Decided without asking" list refers to the ticket's text being unchanged in
  that case.
- **Split children, not spin-offs.** A split's children are filed with their size and points and
  without the label. Once the whole split has landed (children filed, parent changed), `dv:groom`
  adds `groomed` to each child, when its team has the label, in the same last step as the groomed
  ticket's label. A split that stops before that step leaves every label off, so
  `dv:director-mode`'s kickoff, which skips grooming for a ticket that has the label, still grooms
  those children. The label writes are separate calls and can themselves stop part way, so after
  them, or after an error during them, `dv:groom` reads back the groomed ticket and every child it
  filed, reports each one's labels as read, and names a partly labelled split under Needs you. A
  spin-off never gets the label: it is drafted, not groomed.
- **Step 8 report.** Says, from the read-back, whether the label was added, already there, or not
  added and why (not approved, no active label, step 7 stopped before it, an approved item did not
  land, or the write failed), for the ticket and each child filed, beside the size, points and
  estimate lines from 0.28.0. When only the label landed, the report says the text is unchanged.
- **`dv:ticket` File step 2.** The rule that leaves off workflow-state labels gains one exception:
  `dv:groom` adds `groomed` to a split's child it filed once the split is complete; a spin-off
  never gets it.
- **README.** The plugin table shows `0.30.0`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
