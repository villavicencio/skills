# dv — v0.28.0

Minor release. `dv:groom` adds the `groomed` label when it applies a ticket's grooming, and
`dv:ticket` allows that label on the children of a split that `dv:groom` files. The other fourteen
skills have no behaviour changes; their version moves to `0.28.0` only because the suite is
released as one plugin.

Numbering: 0.28.0 follows 0.27.0, which made `dv:pickup` and `dv:handoff` list long-running
background work.

Why: the board should show which tickets have been groomed. `dv:groom` wrote a dated grooming line
into Agent notes but never set a label, since step 7 forbade label changes, so the `groomed` label
was applied by hand and drifted (VIL-853).

## Changed

- **`dv:groom` step 7, new edit-list item.** The `groomed` label is its own numbered item, added
  with `addLabels` so the ticket's other labels stay, and applied with the other approved edits,
  last, so a grooming that stops part way leaves the label off. It is left out when the ticket
  already has the label, and left out (with the reason in the report) when the team has no active
  `groomed` label; the skill never creates the label.
- **Forks-only mode.** The label item is applied with the rest of the edit list, without the
  approval question, including when it is the only item.
- **Label rule.** "Do not change the state, labels, …" keeps every other label forbidden and names
  `groomed` as the one exception.
- **A ticket that needs no other edits.** The last Rules bullet no longer leaves it untouched: its
  text stays as it is, and the edit list holds only the label item (asked as usual, or applied
  without the question in forks-only mode). The grooming line and the no-split line still go in
  only alongside edits to the text. Forks-only's "Decided without asking" list refers to the
  ticket's text being unchanged in that case.
- **Split children, not spin-offs.** The children of a split filed in step 7 get `groomed` when
  their team has the label, and the split proposal shows it among their labels. A spin-off does
  not get it: it is drafted, not groomed, and `dv:director-mode`'s kickoff skips grooming for a
  ticket that has the label.
- **Step 8 report.** Says whether the label was added, already there, or not added and why (not
  approved, no active label, step 7 stopped before it, or the write failed), for the ticket and
  each child filed. When only the label landed, the report says the text is unchanged.
- **`dv:ticket` File step 2.** The rule that leaves off workflow-state labels gains one exception:
  a split's child that `dv:groom` files gets `groomed`; a spin-off does not.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
