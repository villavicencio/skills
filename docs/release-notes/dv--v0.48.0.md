# dv — v0.48.0

Minor release. `dv:groom`'s scouting again searches the repo for other spellings of a value the
ticket changes, but only inside the disclosure boundary of its "Done means lines that already pass"
check: a repo GitHub serves as public, searched at the commit GitHub reports as its default
branch's tip, with the boundary read again for that search. There every match discloses only what
anyone can already read. Outside the boundary the search stays refused, as in dv 0.46.0, and the
report now lists it as not run, with the reason ("repo not public", or the boundary's other
reasons). This closes, for public repos, the known limit the dv 0.46.0 release note listed as
"Scouting may miss a stale copy of a changed value"; outside the boundary (a private or internal
repo included) that limit still holds (VIL-1239). Only `dv:groom` changes. The other fifteen
skills have no behaviour changes; their version moves to `0.48.0` only because the suite is
released as one plugin.

Numbering: 0.48.0 follows 0.47.0 (skills PR 128), which has merged.

Why: dv 0.46.0 (VIL-1224, skills PR 127) removed scouting's repo-wide search, because a search of
every tracked file with a pattern taken from ticket text tells whoever reads the findings which
files hold that pattern, so the text could probe file contents. Grooming could then miss a stale
copy of a changed value in a file it did not read. In a public repo, at the tip GitHub serves, that
probe learns nothing that is not already public.

## Changed

- **`dv:groom`, step 5 ("Scout"), new "The search for other spellings".** One search, and no
  other search across files (inside the boundary or out), in each repo the ticket changes, for
  every value it changes there, unless a step stops it. Its result never settles a fact stated in
  words, which keeps "not checked: read across files" when only a read across files could settle
  it. In this order:
  1. **Spellings.** Each spelling of each value (as the ticket writes it, and each other way the
     groomer would look for it written) is taken as a pattern under step 3's "The path and the
     pattern", before any read; a spelling those rules refuse is not searched for ("unsafe
     pattern"), and with none left the search is "not run: unsafe pattern".
  2. **Boundary.** Only the commit that check's "Commit" verifies ("not run: default-branch commit
     not verified" otherwise), then the boundary's four reads (Remote, Branch, Tip, Visibility), in
     that order, before any other read for the search, then Visibility again as the last read
     before the search, with the search right after it. They are made afresh for each search,
     nothing taken from earlier in the run (a Done means line's boundary reads included) and none
     reused. Wherever the boundary would make a line "not run: repo not public", the search is
     "not run: repo not public", and nothing more is read for it.
  3. **Search.** One fixed read, one `-e` per spelling:
     `git --no-replace-objects --no-lazy-fetch -C "<top level>" grep -l -I --no-color --no-recurse-submodules -F -e '<pattern>' <commit>`.
     It searches the files tracked at the commit from the commit's own objects, so it sees no
     untracked or generated file and follows no symbolic link; `--no-recurse-submodules` keeps it
     out of every submodule, whatever git config says (`submodule.recurse=true` alone makes
     `git grep` enter one); `-I` skips binary files; `-l` prints file names, not lines. It is
     judged by its output: lines starting with `<commit>:` are matches, no output and no error is
     no match, and anything else is "not run: read failed".
  4. **Names.** Each printed path is judged by the path rules of "The path and the pattern"
     (unsafe path, git metadata, secret-named path) before it is used. A name they refuse is left
     out, and nothing about it goes in the reply, the report or Linear, not its name and not that
     a name was left out. Each other name the ticket does not name is reported as an in-ticket
     improvement, with the spellings searched and the commit's short id, within scouting's cap.

  When the search is not run, the report lists it under what was not checked, as "scouting search:
  not run: <reason>". The step's in-ticket improvements and its evidence list name the search's
  files beside the files the session reads.
- **`dv:groom`, step 3, "Paths in your own reads".** The refusal of a read across files is
  unchanged for a fact stated in words ("not checked: read across files"). For scouting it now
  holds except step 5's one guarded search, which the paragraph points to. The sentence on which
  searches are held to the disclosure boundary names step 5's search beside the check's.
- **`dv:groom`, Rules, the bullet on values taken from the ticket.** Its pattern exception covers
  step 5's search as well as the check, and its refusal of a read across files names step 5's
  guarded search as the one exception.
- **Unchanged:** a fact stated in words keeps its "read across files" refusal in every copy
  (`dv:groom` step 3 and Rules, `dv:ticket` File step 5 and Rules). The "Done means lines that
  already pass" check itself, its forms, path and pattern rules, disclosure boundary, reads and
  results.
- **README.** The version, and the `dv:groom` entry.

## Known limits

- **Outside the boundary, scouting may still miss a stale copy of a changed value.** In a private
  or internal repo, a repo whose origin is not on `github.com` or is named through an SSH host
  alias, a ticket tied to another branch or version, or when the default branch has moved since
  step 1, the search is not run, and a copy is found only in a file the session reads.
- **The search sees only the files tracked at the verified commit.** An untracked or generated
  file, a submodule's files and a file git takes for binary are not searched.
- **A spelling the pattern rules refuse is not searched for**, such as one that holds a quote,
  `$`, a backtick, `\`, `!` or a character outside printable ASCII.
- **A file whose name the path rules refuse is never reported**, even when it holds a copy.
- **A match names a file, not a line.** Whether the spelling found there is the value the ticket
  changes is left to whoever reads the item.
