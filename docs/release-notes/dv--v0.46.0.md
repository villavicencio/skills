# dv — v0.46.0

Minor release. When `dv:groom` or `dv:ticket` checks a fact the ticket or request states in words,
the session's own reads now hold every path they take from that text (for `dv:groom`, the ticket's
comments too), or from anything it points to, to the path rules of `dv:groom`'s "Done means lines
that already pass" check ("The path and the pattern"), with one rule before them (a path that
starts with `/` or `~` is outside the repo and is not read) and link tests after them (a path that
is, or sits under, a symbolic link or a submodule, or is a hard link, is refused, found by its git
file mode at the commit and by `ls -ld` in the working tree). A path a name rule refuses is never
read, not even to see whether it exists, one the link tests refuse has no contents read, and the
fact is not checked (`dv:groom`) or `[assumed]` (`dv:ticket`), with the reason. While a fact stated
in words is checked, no read opens or names a file whose path has not passed the rules and link
tests, whoever chose the word or path (a search of a directory or of the whole repo, a recursive
`grep`, `find`, a glob or a directory listing): such a fact is not checked ("read across files"; in
`dv:ticket`, `[assumed]`). This closes the limit that the dv 0.43.0 and 0.44.0 release notes listed
under "Not in this release": those reads took paths from the ticket without the check's path rules,
secret-named paths included (VIL-1224). Only `dv:groom` and `dv:ticket` change. The other fourteen
skills have no behaviour changes; their version moves to `0.46.0` only because the suite is
released as one plugin.

Why: since dv 0.43.0 a fact stated as a command is checked only by the already-passing check,
under its path rules, but a fact stated in words was still checked with reads that took any path
from the ticket. So ticket text such as "`.env.example` names the key" could point a session at a
secret-named file and get back what it found.

## Changed

- **`dv:groom`, step 3, "Paths in your own reads"** (new, right after "How"). Before any read of a
  path that a read of the session's own takes from the ticket's text, its comments, or a ticket,
  PR, file or page they point to (together, "the text"), the session checks the path. A URL of a
  file in a repo (a GitHub `blob`, `raw` or `contents` URL, or the like) counts as that file's
  path, and is opened only with its ref replaced by the tested commit's id. A file the text names
  only in words counts, as the path the session would read, worked out from the words alone, never
  from a listing. The path is taken as "The path and the pattern" takes a file test's `<path>`
  (without its quotes, a leading `./` dropped, relative to the top level of the repo the fact is
  about), and the first rule that refuses it gives the reason:
  - a path that starts with `/` or `~`: "not checked: path outside the repo", so whoever reads the
    report knows to check it by hand;
  - otherwise that section's rules, in its order: "not checked: unsafe path", "not checked: git
    metadata" or "not checked: secret-named path" (the `.git` and secret-name tests ignore case, as
    before);
  - then the link tests: a path that is a symbolic link, a hard link or a submodule, or that sits
    under a symbolic link or a submodule, is "not checked: link". A submodule gets the same reason
    as a link, since both lead to files the rules did not judge.

  The link tests are the only reads of the path before it passes, and read modes, never contents,
  on each part of the path from the top; a path passes only when every part passes both. At the
  commit step 1 recorded, one `ls-tree <commit> -- '<part>'` per part, with `--no-replace-objects`
  and `--no-lazy-fetch`, the read the already-passing check makes: mode `040000` passes the part,
  `100644` or `100755` passes it and ends the test, `120000` is a symbolic link, `160000` a
  submodule, and a part that prints nothing passes and ends the test. In the working tree, whether
  the commit tracks the path or not, one `ls -ld` naming every part, from the first directory to
  the whole path; for `docs/notes/a.md` that is
  `ls -ld -- "<top level>"/'docs' "<top level>"/'docs/notes' "<top level>"/'docs/notes/a.md'`.
  A `d` line passes a part, and so does a `-` line (for the whole path, only with a link count of
  1); an `l` line is a symbolic link, and a `-` line for the whole path with a link count above 1 a
  hard link; a missing part passes and ends the test. Any other output, or a test that cannot be
  made (the commit not in the local clone, or a repo with no local clone), is "not checked: read
  failed". Only a path that passes both tests is read.

  A path a name rule refuses is not read in any way, not even to see whether it exists, one the
  link tests refuse has no contents read, and nothing about a refused path, or about a secret-named
  entry any read shows, goes in the reply, the report or Linear beyond the reason. While the
  session checks a fact stated in words, and in step 5's search for other spellings of a value the
  ticket changes, no read opens or names a file whose path has not passed every rule and both link
  tests, whoever chose the word or path, so no search of a directory or of the whole repo, no
  recursive `grep`, no `find`, no glob and no directory listing. What depended on such a read is
  "not checked: read across files". A read of one file, or a search of one file, at a path that
  passed every rule and both link tests stays allowed, and so do the link tests' own reads, which
  name only the parts of a path the name rules judged. The paragraph, the refusal of a read across
  files included, does not apply to the fixed reads of the already-passing check (its
  `ls-tree --name-only` listings of a parent directory included), which keep the check's rules and
  results. It says plainly that these reads are not held to the disclosure boundary (only the
  check's search is), so in a private repo a fact stated in words about a file whose path passes
  the rules and tests is still read and reported.
- **`dv:groom`, step 5 ("Scout") and Rules.** Scouting's evidence points to the new paragraph as
  well as "How". Its in-ticket improvements no longer search the repo for every spelling of a value
  the ticket changes: a copy the change misses is reported only from a file the session reads, and
  the skipped search is listed under what was not checked. The Rules bullet on values taken from
  the ticket, its comments or anything they point to says a path taken from that text goes through
  "Paths in your own reads", its name rules and then its link tests, before any read of it, in
  every step, and that while a fact stated in words is checked, or other spellings are searched
  for, no read opens or names a file whose path has not passed those rules and tests ("read across
  files").
- **`dv:ticket`, File step 5.** Each path the session's own reads take from the request, or from
  anything it points to, goes through `dv:groom`'s "Paths in your own reads", its name rules and
  then its link tests, with the same order and reasons, URLs of repo files included. The link tests
  run at the default branch's commit, taken from the local clone and compared with origin's as
  `dv:groom` step 1 does, the same commit a fact stated as a command uses, and in the working tree;
  when that comparison does not verify the commit, or the request ties the fact to another branch
  or version, the fact is `[assumed]` ("default-branch commit not verified"). A refused path has no
  contents read; the fact is marked `[assumed]` and listed in the Agent notes under what was not
  checked, with the reason ("path outside the repo", "unsafe path", "git metadata", "secret-named
  path", "link", "read failed" or "default-branch commit not verified"). While a fact the request
  states in words is checked, no read opens or names a file whose path has not passed the rules and
  link tests, whoever chose the word or path, and the fact is `[assumed]` ("read across files"); a
  read or search of one file at a path that passed stays allowed, and the fixed reads of
  `dv:groom`'s already-passing check keep that check's own rules. If `../groom/SKILL.md` cannot be
  read, every fact whose check would read a path taken from the request or from anything it points
  to is `[assumed]` ("dv:groom's path rules could not be read"). The step says plainly that in a
  private repo a fact stated in words about a file whose path passes the rules and tests is still
  read, and the draft says what was found. Its Rules bullet gains the matching sentence, pointing
  to File step 5.
- **Unchanged:** the "Done means lines that already pass" check itself, its forms, path and
  pattern rules, disclosure boundary, reads and results, and so the check of a fact stated as a
  command.
- **README.** The version, and the `dv:groom` and `dv:ticket` entries.

## Known limits

- **A file whose name passes the path rules is still read and reported in a private repo.** The
  session's own reads for a fact stated in words get the path rules and link tests only, not the
  disclosure boundary of the check's search, which would leave almost every content fact in a
  private repo unchecked. The same holds in any repo for a file the repo does not track.
- **An untracked file, a file inside a nested repository included, is judged by its name alone.**
  Apart from the working-tree link test (a symbolic or hard link), nothing looks at it beyond its
  name: git's file mode does not cover it, and nothing checks whether it sits inside another
  repository nested in this one that the commit does not record as a submodule (mode `160000`), so
  that repository's files (a bare repository's `config` included) are read and reported when their
  names pass the rules.
- **A path outside the repo is not checked.** A path that starts with `/` or `~` is never read;
  the report says "not checked: path outside the repo" (in `dv:ticket`, `[assumed]` with that
  reason), and such a fact has to be checked by hand. A path that climbs out with `..` is refused
  too, as "unsafe path".
- **A fact that needs a read across files is not checked.** A fact stated in words that only a read
  opening or naming more than one file, some of them not judged by the rules, could settle (a
  search of a directory or of the whole repo, a recursive `grep`, `find`, a glob or a directory
  listing), such as "no file mentions X", is reported "not checked: read across files" (in
  `dv:ticket`, `[assumed]` with that reason), whoever would have chosen the word or path.
- **Scouting may miss a stale copy of a changed value.** `dv:groom` no longer searches the whole
  repo for other spellings of a value the ticket changes; it looks for them only in the files the
  session reads, so a stale copy elsewhere in the repo can go unreported.
