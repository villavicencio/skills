# dv — v0.46.0

Minor release. When `dv:groom` or `dv:ticket` checks a fact the ticket or request states in words,
the session's own reads now hold every path they take from that text to the path rules of
`dv:groom`'s "Done means lines that already pass" check ("The path and the pattern"), with one
rule before them: a path that starts with `/` or `~` is outside the repo and is not read. A
refused path is never read, not even to see whether it exists, and the fact is not checked
(`dv:groom`) or `[assumed]` (`dv:ticket`), with the reason. A search of the session's own across
more than one file, for a word the text gives, leaves out every tracked secret-named file. This
closes the limit that the dv 0.43.0 and 0.44.0 release notes listed under "Not in this release":
those reads took paths from the ticket without the check's path rules, secret-named paths
included (VIL-1224). Only `dv:groom` and `dv:ticket` change. The other fourteen skills have no
behaviour changes; their version moves to `0.46.0` only because the suite is released as one
plugin.

Why: since dv 0.43.0 a fact stated as a command is checked only by the already-passing check,
under its path rules, but a fact stated in words was still checked with reads that took any path
from the ticket. So ticket text such as "`.env.example` names the key" could point a session at a
secret-named file and get back what it found.

## Changed

- **`dv:groom`, step 3, "Paths in your own reads"** (new, right after "How"). Before any read of a
  path that a read of the session's own takes from the ticket's text, its comments, or a ticket,
  PR, file or page they point to, the session checks the path. A file the text names only in words
  counts, as the path the session would read, worked out from the words alone or from a listing
  whose command drops every secret-named entry before its output reaches the session. The path is taken as "The path and the pattern"
  takes a file test's `<path>` (without its quotes, a leading `./` dropped, relative to the top
  level of the repo the fact is about), and the first rule that refuses it gives the reason:
  - a path that starts with `/` or `~`: "not checked: path outside the repo", so whoever reads the
    report knows to check it by hand;
  - otherwise that section's rules, in its order: "not checked: unsafe path", "not checked: git
    metadata" or "not checked: secret-named path" (the `.git` and secret-name tests ignore case,
    as before).

  A refused path is not read in any way, not even to see whether it exists, and nothing about it,
  or about a secret-named entry any read shows, goes in the reply, the report or Linear beyond the
  reason. A search of the session's own across more than one file in a repo, for a word the text
  gives (step 5's search for every spelling of a value included), opens no secret-named file: it
  is `git grep -F -e '<word>' <commit> -- .` at the commit step 1 recorded, which reads only that
  commit's tracked files (not made when that commit is not in the local clone: "not checked:
  commit not in the clone"), with the word only when it passes the Rules' test for a value taken from
  ticket text, and with a `':(exclude,literal)<path>'` pathspec for each secret-named path that
  `git ls-tree -r -z --name-only <commit>` lists. When such a path holds `'` or a character outside
  printable ASCII, it cannot be left out that way, and the search is not made: "not checked:
  search would open a secret-named path". The paragraph does not apply to the check's own reads,
  which keep the check's rules and results. It says plainly that these reads are not held to the
  disclosure boundary (only the check's search is), so in a private repo a fact stated in words
  about a file whose path passes the rules is still read and reported.
- **`dv:groom`, step 5 ("Scout") and Rules.** Scouting's evidence points to the new paragraph as
  well as "How", and the Rules bullet on values taken from ticket text says a path taken from that
  text goes through "Paths in your own reads" before any read of it, in every step, and so does a
  search across more than one file for a word that text gives.
- **`dv:ticket`, File step 5.** Each path the session's own reads take from the request, or from
  anything it points to, goes through `dv:groom`'s "Paths in your own reads", with the same order
  and reasons. A refused path is not read in any way; the fact is marked `[assumed]` and listed in
  the Agent notes under what was not checked, with the reason ("path outside the repo", "unsafe
  path", "git metadata", "secret-named path", "commit not in the clone", or "search would open a
  secret-named path"). The search runs at the default branch's commit, taken from the local clone
  and compared with origin's as `dv:groom` step 1 does, the same commit a fact stated as a command
  uses. If `../groom/SKILL.md` cannot be read, every fact whose check would
  read a path taken from the request, or search more than one file for a word it gives, is
  `[assumed]` ("dv:groom's path rules could not be read"). The step says plainly that in a private
  repo a fact stated in words about a file whose path passes the rules is still read, and the draft
  says what was found. Its Rules bullet gains the matching sentence, pointing to File step 5.
- **Unchanged:** the "Done means lines that already pass" check itself, its forms, path and
  pattern rules, disclosure boundary, reads and results, and so the check of a fact stated as a
  command.
- **README.** The version, and the `dv:groom` and `dv:ticket` entries.

## Known limits

- **A file whose name passes the path rules is still read and reported in a private repo.** The
  session's own reads for a fact stated in words get the path rules only, not the disclosure
  boundary of the check's search, which would leave almost every content fact in a private repo
  unchecked. The same holds in any repo for a file the repo does not track, and for a path that is
  a link or sits under one, since the rules judge a path by its name alone and a read follows the
  link wherever it leads.
- **A path outside the repo is not checked.** A path that starts with `/` or `~` is never read;
  the report says "not checked: path outside the repo" (in `dv:ticket`, `[assumed]` with that
  reason), and such a fact has to be checked by hand. A path that climbs out with `..` is refused
  too, as "unsafe path".
