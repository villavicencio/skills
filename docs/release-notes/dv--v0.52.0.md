# dv — v0.52.0

Minor release. `dv:manager-mode`, `dv:director-mode` and the README now say what dotfiles
`docs/agents/code-review.md` ("Fix rounds") says about a third MergeWren fix round: a third round
that section calls low-risk is the session's own call, recorded with that section's one-line
PR-body note. Any other round past two, and the declines the session asks about, still goes to the
Director as before. The other fourteen skills have no behaviour changes; their version moves to
`0.52.0` only because the suite is released as one plugin.

Numbering: 0.52.0 follows 0.50.0, with 0.51.0 held by open PR 130; the version is re-checked at
the merge if that changes.

Why: dotfiles "Fix rounds" now lets a low-risk third round go ahead without asking, but both
skills still gave a worktree session only rounds 1 and 2 and sent every round past two to the
Director, so they contradicted the rule they point to (VIL-1033).

## Changed

- **`dv:manager-mode`, "Review findings".** Rounds 1 and 2, and a third round "Fix rounds" calls
  low-risk, are the session's own call; the Director decides any other round past two and the
  declines the session asks about. The open list is sent where that section says to bring it, and
  the resume note names the Director for any other fix round past two. The list of decisions
  already the session's own (under "Questions go to the Director first") includes the low-risk
  third round.
- **`dv:director-mode`, "You decide, without asking me".** The fix-round bullet covers the rounds
  past the session's own calls: rounds 1 and 2, and a low-risk third round, stay the session's
  own call, and where "Fix rounds" says to bring the open list, it comes to the Director. The list
  of the session's own decisions in the question rule includes the low-risk third round.
- **README.** The `dv:manager-mode` and `dv:director-mode` summaries say the same, and the plugin
  table shows the version.

## Unchanged

- The low-risk test lives only in dotfiles "Fix rounds"; neither skill nor the README restates it.
- Who decides any other round past two, and held declines on safety-boundary code.
- Everything else in both skills.
