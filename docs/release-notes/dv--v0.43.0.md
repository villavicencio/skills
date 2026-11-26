# dv — v0.43.0

Minor release. `dv:groom` and `dv:ticket` no longer run a command taken from ticket or request
text to check a fact. A fact stated as what a command does is checked only when the command is a
file test that `dv:groom`'s fixed git reads can settle; any other is not checked (`dv:groom`) or
marked `[assumed]` (`dv:ticket`). Only `dv:groom` and `dv:ticket` change. The other fourteen skills
have no behaviour changes; their version moves to `0.43.0` only because the suite is released as
one plugin.

Why: `dv:groom` step 3 ("How") and `dv:ticket` File step 5 let the session run a command from the
ticket or the request once it had read the command and judged that it only reads. A crafted ticket
could therefore get a command run on the groomer's machine, and an agent's judgment that a command
is read-only is not a boundary (VIL-1201). dv 0.41.0 (VIL-1169) settled on checking Done means
lines with grooming's own fixed git reads and never running ticket text; fact checks now follow the
same rule.

## Changed

- **`dv:groom`, step 3, "How".** A command taken from the ticket, its comments, or a ticket, PR,
  file or page they point to is never run: not on this machine or any other, not in a copy or a
  scratch directory, and not after the session reads it and judges it read-only. No script, test or
  build is run to check a fact either, whether the ticket names it or the repo holds it. A fact the
  ticket states as what a command does (such as "`test -f docs/x.md` passes") is checked only by
  step 3's "Done means lines that already pass", as if it were a Done means line holding that one
  command: only a file test (`test -f`/`-e`, or the `[ ]` spelling, with at most one `!`), under
  that check's path rules, with its fixed git reads (`cat-file -e`, `ls-tree`, each with
  `--no-lazy-fetch`), judged as its "Judge" says (a success statement only). "Already passes"
  makes the fact current; "fails in the tracked files at the commit" makes it stale in the files
  tracked at that commit, said in those words, since the reads do not see untracked or generated
  files; any "not run" reason leaves it not checked, with that reason. Such a fact is not checked
  any other way, such as with the session's own command that does the same thing. A fact stated in
  words, even with a command beside it as its evidence, is still checked with the session's own
  reads, and the command is not run.
- **The commit.** That check uses only the default branch's commit that step 1 verified against
  origin. When step 1 recorded another branch or version for the ticket, a fact stated as a command
  is "not checked: default-branch commit not verified", since the reads would answer for a
  different commit than the one the ticket is about.
- **`dv:groom`, step 3, "Conditional steps".** The check a step gives is never run. The step closes
  only when its check is a command that "How" checks as above and the result is "already passes" or
  "fails in the tracked files at the commit"; a step about an untracked or generated file stays.
  Any other step stays as it is, for whoever works the ticket, with the reason: the check's "not
  run" reason, or "check stated in words". Before, a step whose check was one or two read-only
  commands was closed by running them.
- **`dv:ticket`, File step 5.** The same rule for a command taken from the request. A fact the
  request states as what a command does is checked only the way `dv:groom` checks one (it points to
  `dv:groom` step 3 rather than copying it), at the default branch's commit read and compared with
  origin's as `dv:groom` step 1 does, and the draft says it was checked that way, with the commit.
  Any other is marked `[assumed]` with the reason, and so is a fact the request ties to another
  branch or version, one that does not name its repo when the request names more than one, and
  every such fact when `dv:groom`'s file cannot be read.
- **`dv:ticket`, the format's fail-first run.** The ticket format asks the author to run each Done
  means command on the default branch and note the result in the line ("A Done means command fails
  first"). `dv:ticket` now runs none, whether the command came from the request or the session
  wrote it: each line is checked with `dv:groom`'s "Done means lines that already pass", its
  "fails" result noted in the line with the commit, and a line that check does not read is listed
  as not run in the Agent notes, not in the line. The skill says this rule decides what the session
  runs, so the format's precedence over the skill does not reach it.
- **Values from ticket text.** Both skills' Rules sections say the boundary holds in every step, and
  that a branch, tag, owner, repo, path or PR number taken from ticket or request text goes into a
  command of the session's own only when it holds nothing but letters, digits, `.`, `_`, `-` and
  `/` and does not start with `-` (a PR number: digits only); otherwise that read is not made.
- **`dv:groom`, "Done means lines that already pass".** Its note on "How" now says "How" holds fact
  checks to the same rule; the check itself is unchanged.
- **README.** The version, and the `dv:groom` and `dv:ticket` entries.

## Not in this release

- A search form (`grep` and the like) for facts or Done means lines. It waits for VIL-1203, which
  defines which files a ticket-supplied pattern may search without letting ticket text probe their
  contents.
- Limits on the session's own reads for a fact stated in words. Those reads still take paths from
  the ticket without the file-test check's path rules (secret-named paths included), as before
  this release.
- The ticket format itself (dotfiles `docs/agents/tickets.md`) still says to run a Done means
  command on the default branch when writing a ticket; `dv:ticket` now overrides that for itself.
