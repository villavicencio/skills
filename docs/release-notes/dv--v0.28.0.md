# dv — v0.28.0

Minor release. `dv:groom` points every ticket it grooms in Fibonacci story points (1, 2, 3, 5, 8
or 13) and sets them in Linear's estimate field. The other fifteen skills have no behaviour
changes; their version moves to `0.28.0` only because the suite is released as one plugin.

Numbering: 0.28.0 follows 0.27.0, which made `dv:pickup` and `dv:handoff` list the shells and
agents a session left running for a long time.

Why: hal's overnight runner is to measure its velocity per worker model and fill each night to
match, and that needs every groomed ticket to carry points (VIL-837). Grooming sized tickets in
words only, and its edit step forbade setting the estimate.

## Changed

- **`dv:groom`, step 4 "Size and split".** Beside the size word, grooming proposes points with
  one sentence on what drives them, taken from an anchor table (1 = a one-line docs or config
  change, up to 13 = too big to run as one ticket). As a guide and not a rule, small is typically
  1 to 3 points, medium 5, large 8 to 13. Points are proposed in the edit list, not asked, like
  Size.
- **Splits above 8 points.** A ticket pointed above 8 gets a proposed split, and each proposed
  child carries its own points. A 13 is never left or filed unsplit without David's explicit yes.
  A parent that stays as the parent carries no estimate of its own, so its children's points are
  not counted twice; a parent that becomes the first child takes that child's points.
- **Step 7 "Edit".** The points are written in the Size section and set with `save_issue`'s
  `estimate` field. `estimate` is out of the list of fields grooming must not change (only for
  the points it proposed), and each approved child gets its estimate in the `save_issue` call that
  creates it, overriding `dv:ticket` File's rule against setting an estimate unasked. Spin-offs
  get no estimate until they are groomed. Grooming compares the estimate `save_issue` returns with
  the points and reports a difference under Needs you: Linear stores a number outside the team's
  scale as a different one with no error (team VIL stored 13 as 8 on 2026-11-23, since its scale
  stops at 8).
- **Step 8 "Report".** The size line shows the points and the estimate as Linear now holds it;
  each filed child is listed with its estimate.
- **Forks-only mode.** Setting or changing points is a routine call, like Size. A split stays a
  fork, so a ticket pointed 13 always comes to David.
- **Format check and the "stays as it is" rule.** Step 2 flags a Size with no points as a gap. A
  ticket that already has its Size but no points, or an estimate that doesn't match them, or that
  is pointed 13 with no recorded yes to keeping it unsplit, is no longer left unchanged.
- **Step 6 "Interview".** The split proposal shows each child's size and points and the parent's
  estimate, and for a ticket pointed 13 the split question says that "no split" keeps it at 13. In
  forks-only mode that "no split" is David's answer to a fork, recorded in the fork form.

## Not tested

Tested on scratch tickets in Linear by following this branch's text by hand in forks-only mode
(the installed plugin was still 0.27.0); see the PR. The default mode's interview and approval
question, and a run through the installed skill, are proved the first time the released skill
grooms a ticket.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
