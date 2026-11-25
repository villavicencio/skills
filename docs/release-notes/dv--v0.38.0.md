# dv — v0.38.0

Minor release. `dv:groom` splits a ticket that needs more than one PR into one child ticket per
PR. Only `dv:groom` changes. The other fifteen skills have no behaviour changes; their version
moves to `0.38.0` only because the suite is released as one plugin.

Numbering: 0.38.0 follows 0.37.1, in which `dv:groom`'s points follow the amount of work, not the
number of repos, and the stale 13-stored-as-8 note is gone. 0.38.0 keeps that change and 0.37.0's
(a Director that turns on announces itself to the worktree sessions). 0.37.1's new sentence under
"Points" now names needing more than one PR, not only PRs in more than one repo, as the split
signal, to match the widened split verdict.

Why: on the hal runs of 2026-11-19 and 11-20, groomed tickets that spanned two repos or several
parts produced partial PRs that closed their tickets on merge (VIL-890). dotfiles
`docs/agents/tickets.md` holds the rule this applies: "A ticket is sized to one PR".

## Changed

- **`dv:groom`, step 4, split verdict.** "The ticket needs more than one PR" is a reason to split,
  one child ticket per PR; PRs in more than one repo that can merge on their own stay covered. A
  ticket left whole that still needs more than one PR (its parts must land together, or you
  answered "no split") gets a line in its Agent notes telling the engineer to link each partial PR
  with `Refs`, not a closing keyword, and the PR that completes the ticket with a closing keyword.
- **`dv:groom`, step 6, split question.** When the split is proposed because the ticket needs more
  than one PR, the question says so, that each child is one PR, and that a ticket left whole closes
  on its first PR's merge unless each partial PR uses `Refs` (the PR that completes it uses a
  closing keyword).
- **README.** The version, and the `dv:groom` entry's split verdict.

## Not in this release

Running each Done means command on the default branch to flag lines that already pass was cut
from this release on 2026-11-25 and moves to VIL-1169. Step 3 still checks only that a Done means
line's means exist.
