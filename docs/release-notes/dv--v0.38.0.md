# dv — v0.38.0

Minor release. `dv:groom` splits a ticket that needs more than one PR into one child ticket per
PR, and runs each Done means command that only reads on the default branch to flag lines that
already pass. Only `dv:groom` changes. The other fifteen skills have no behaviour changes; their
version moves to `0.38.0` only because the suite is released as one plugin.

Numbering: 0.38.0 follows 0.37.1, in which `dv:groom`'s points follow the amount of work, not the
number of repos, and the stale 13-stored-as-8 note is gone. 0.38.0 keeps that change and 0.37.0's
(a Director that turns on announces itself to the worktree sessions). 0.37.1's new sentence under
"Points" now names needing more than one PR, not only PRs in more than one repo, as the split
signal, to match the widened split verdict.

Why: on the hal runs of 2026-11-19 and 11-20, groomed tickets still reached the queue with two
problems grooming could have caught. Tickets spanning two repos or several parts produced partial
PRs that closed their tickets on merge, and three Done means commands already passed on the
unchanged code, so those checks proved nothing (VIL-890). dotfiles `docs/agents/tickets.md` holds
the two rules this applies: "A Done means command fails first" and "A ticket is sized to one PR".

## Changed

- **`dv:groom`, step 3, new "Done means fails first".** It replaces the sentence that said a Done
  means line's result is not checked, only its means. For each Done means line with a command in
  backticks, grooming runs the command when every part of it only reads (reading or searching
  files, reading git), on the default branch's local commit (grooming does not fetch, and says so
  when the remote commit differs), from the root of a clean tree: the session's checkout when it is
  at that commit with no local changes, otherwise a copy of that commit extracted with
  `git archive` into a new empty directory outside the repo and removed once the interview has
  settled every flagged line. A command that writes or might write, pushes or reaches another
  machine, sends a message, calls a paid service or a model, or runs a script or program from the
  repo (even one named `--dry-run`) is not run and is listed as not run with the reason; so is one grooming is unsure
  about. A line whose output matches what it says passing looks like is flagged, with the command,
  commit and output; a line already marked as a guard of unchanged behavior is not. A line that
  fails but does not note that result gets it noted ("nothing at `<commit>`"), as an edit-list
  item.
- **`dv:groom`, step 6.** The findings list names the lines that already pass and those not run.
  Each flagged line is an interview question: rewrite it so it fails first (a read-only rewrite is
  run first and offered only if it fails, with its result in the line; one that cannot be run is
  offered marked "not run"), mark it as a guard when it checks behavior that must not change, keep
  it with a reason, or drop it.
- **`dv:groom`, "Forks-only mode".** Rewriting a flagged line with a rewrite that was run and
  failed, or marking it as a guard when it checks behavior that must not change, is a routine call.
  Keeping it with a reason when neither fits, and dropping it, are forks. Both lists say so.
- **`dv:groom`, step 4, split verdict.** "The ticket needs more than one PR" is a reason to split,
  one child ticket per PR; PRs in more than one repo that can merge on their own stay covered. A
  ticket left whole that still needs more than one PR (its parts must land together, or you
  answered "no split") gets a line in its Agent notes telling the engineer to link each partial PR
  with `Refs`, not a closing keyword. The split question in step 6 says when the split is for more than one PR, that each child is one PR, and that a
  ticket left whole closes on its first PR's merge unless each PR uses `Refs`.
- **`dv:groom`, steps 7 and 8, and Rules.** The edit list carries rewritten, guard-marked and
  dropped lines, and the result noted in a line that fails. A flagged line left with no rewrite, guard mark or recorded reason fails the ready test (so the
  ticket gets no `groomed` label) and keeps it from being reported ready. The report lists the
  Done means lines not run. The Rules allow the temporary copy as grooming's one file write.
- **README.** The version, and the `dv:groom` entry: the Done means check, the one-PR split rule,
  and the forks-only lists.
