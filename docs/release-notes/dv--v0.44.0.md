# dv — v0.44.0

Minor release. `dv:groom`'s "Done means lines that already pass" check, which dv 0.41.0 limited
to file tests, checks a search of one file again (`grep` with a quoted pattern), but only inside a
disclosure boundary: the search runs only when origin is a GitHub repo that `gh repo view` reads
as `PUBLIC`, read again for each search line, so a match discloses only what anyone can already
read. In any other case, a failed or unreadable read included, the line is "not run: repo not
public". Since `dv:groom` step 3 ("How") and `dv:ticket` File step 5 check a fact stated as a
command with this same check, such a fact can now be a search too, under the same boundary. Only
`dv:groom` and `dv:ticket` change, with one sentence in the rules file they share. The other
fourteen skills have no behaviour changes; their version moves to `0.44.0` only because the suite
is released as one plugin.

Why: most Done means commands are searches, and since dv 0.41.0 every one of them was listed as
not run, so a search line that already passes could reach the queue unflagged. The search form was
cut from dv 0.41.0 (skills PR 118) because a result about a file's contents, on a pattern the
ticket supplies, lets ticket text probe a tracked file one substring at a time (MergeWren's
critical finding `70d9c96#1`). In a public repo, every match tells the reader only what anyone can
already read (VIL-1203).

## Changed

- **`dv:groom`, step 3, "Done means lines that already pass": forms.** A line is checked when its
  command is a file test, as before, or a search of one file: `grep <flags> <pattern> <path>`, with
  at most one `!` before it, `<flags>` none or more of `-n`, `-i`, `-q`, `-w`, `-F` and `-E` (alone
  or joined, never `-F` with `-E`), `<pattern>` in single or double quotes and `<path>` one path.
  A bare line (no backticks) that starts with exactly such a search is checked the same way as a
  bare file test. Any other command, a search with another flag, a second pattern or path, or
  anything outside the pattern's quotes that the shell reads, is "not run: unsupported form".
- **The pattern.** Inside its quotes the pattern must not be empty, start with `-`, hold anything
  outside printable ASCII (space to `~`), hold `'`, `"`, `$`, a backtick, `\` or `!`, or, under
  `-E`, hold `{`; otherwise the line is "not run: unsafe pattern". A leading `-` would be an option
  to `grep`; the quote and shell characters read differently inside double quotes than inside
  single ones (`\` also between `grep` and `git grep`, and `!` in an interactive shell); an
  interval (`{`) can make a pattern costly to compile; outside ASCII `grep` and `git grep` can
  match differently. The
  pattern reaches the check's own read only inside single quotes, after `-e`, so it cannot become an
  option, and the matcher is always named (`-G`, `-F` or `-E`), so git config cannot change the
  pattern syntax. Both skills' Rules sections name the pattern as the one exception to the
  plain-characters rule for values taken from ticket or request text.
- **The disclosure boundary.** For each search line, just before that line's other reads and its
  search (never reused from another line or run), the check reads `git remote get-url --all origin`, which
  must print one `github.com` URL (`https://github.com/<owner>/<repo>`,
  `git@github.com:<owner>/<repo>` or `ssh://git@github.com/<owner>/<repo>`, with or without
  `.git`, plain owner and repo names), then
  `gh repo view 'github.com/<owner>/<repo>' --json visibility --jq .visibility`, which must print
  `PUBLIC`. The `github.com/` keeps `GH_HOST` from sending the read to another host. The commit is
  the one the check already verifies against `git ls-remote origin`, so it is on origin. Anything
  else (another host or URL form, `PRIVATE`, `INTERNAL`, a read that fails or prints something
  else) is "not run: repo not public", and nothing else is read for that line. The URL is never
  quoted in a reply, report or Linear, since it can hold a credential. The path rules (unsafe path,
  `.git` part, secret-named path in any case) still come first, and the link, submodule and
  case-only rules still apply, in a public repo too.
- **The search's reads.** After the boundary, the same `ls-tree` reads as a file test. For a
  regular file, the check then asks whether a checkout would change the file's bytes:
  `check-attr --source <commit>` for `filter`, `working-tree-encoding`, `ident`, `crlf` and `eol`,
  plus the clone's `core.autocrlf` and `core.eol`. A `filter` (Git LFS included),
  `working-tree-encoding`, `ident` or `crlf` value, an `eol` set to anything but `lf`, a `core.autocrlf`
  other than `input` or false, a `core.eol` other than `lf` or `native`, or any search on Windows
  makes the line "not run: a checkout changes the file". The `text` attribute is not read, and the
  step says why: on checkout git only adds a CR before an LF, and only in the cases above; it never
  removes one, so a file committed with CRLF line endings checks out with the same bytes. Then
  `git grep -l --no-color` with the line's matcher and `-i`/`-w` on the commit and path, which
  names the file on a match and prints none of its lines (the line's `-n` and `-q` are not passed
  on). The check judges by that output, not by the exit
  alone: Claude Code's Bash tool reports a search's exit 1 as a success with no output, so a
  `git grep -q` that found nothing looked like a match in this release's first live check. On a
  match the search runs again with `-I`, and a file git takes for binary is "not run: binary
  file", since `grep` prints a notice there, not the lines, and the `grep` in Claude Code's shell
  skips binary files.
- **A path found with a case-variant sibling.** When `ls-tree` finds the path, the check now
  also lists the parent of each of its parts; another entry there that matches the part when case
  is ignored makes the line "not run: path differs only in case", as a missing path with such an
  entry already did, since a checkout on a disk that ignores case can put the other entry at the
  path. This applies to file tests and searches alike.
- **Every read of the repo's objects in the check now passes `--no-replace-objects`** (with
  `--no-lazy-fetch`, as before), the file test's included, so a local `refs/replace/` object cannot stand in for the
  verified commit's tree or file. Under the boundary this matters: a replaced file would be local
  content, not what origin serves.
- **Judge.** A success statement (nothing beyond the command, "exits 0", "succeeds", "passes")
  passes on exit 0, as before; a search exits 0 on a match, 1 on no match and 2 when the path is
  missing or a directory, and `!` turns 0 into 1 and anything else into 0. Only a success
  statement can give "already passes". A search of a regular file with no `!` and no `-q` stated
  to print or find one or more lines, described or counted ("prints the release rule", "prints one
  line"), fails on no match, since it then prints nothing; on a match it is "not run: output not
  checked", since the reads cannot show whether the lines it prints are the ones described.
  Anything else, a guard note, an expected failure or a statement that a search prints or finds
  nothing included, stays "not run: stated result unclear": a search that finds nothing exits 1,
  so an absence check passes only when written with `!` (`! grep -q "<pattern>" <path>`), which the
  success rule reads. So a fact stated as a search is current only by exit status, and a
  conditional step closes on a search only on that or on a search that finds nothing. Matched lines and file contents are never
  printed in a reply, report or Linear: a line gets a result, not output.
- **`dv:groom`, step 3, "How" and "Conditional steps".** A fact stated as a command, and a
  conditional step's check, can now be a search too, checked by the same rules and boundary; "repo
  not public" is one of the reasons such a fact stays not checked.
- **`dv:ticket`, File step 5.** It points at `dv:groom`'s check as before, so a fact the request
  states as a search is checked under the same boundary, and is `[assumed]` with "repo not public"
  outside it.
- **Shared rules, "What a session runs"** (`plugins/dv/skills/ticket/references/ticket-format.md`).
  Its sentence on the check now says it looks a file test up, or searches one tracked file in a
  public repo, with fixed reads of its own, and runs no command from the text. Nothing else in the
  file changes.
- **README.** The version, and the `dv:groom` and `dv:ticket` entries.

## Answers to the search form's earlier review findings (skills PR 118)

- **The oracle (`70d9c96#1`, critical).** The public-repo boundary: a search runs only where every
  match is already public, with the visibility read for each search and failing closed.
- **Checkout line endings (`754ba37#1`).** The attribute and config reads above, and Windows; a
  pattern cannot hold `$`, so it cannot anchor on a line end.
- **Case-sensitive secret names (`6eaf39a#1`).** The secret-name rule lowercases each path part
  first (since dv 0.41.0), and it applies to a search as to a file test.
- **Binary files (`3436f8f#1`).** The `-I` re-run on every match.
- **Git's `text` attribute (`70d9c96#2`).** Not read, with the reason now in the step itself.
- **Replacement refs (`20fdd3e#2`).** `--no-replace-objects` on every read of the repo's objects.

## Known limits

- The search reads the commit's copy with `git grep`. Another `grep` (GNU, BSD, or the ugrep that
  Claude Code's shell runs as `grep`) can still match differently on non-ASCII text in the file for
  `-i`, `-w`, `.` or a bracket expression, or take for binary a file git takes for text (such as a
  file with invalid UTF-8 and no NUL byte).
- A repo whose origin is not on `github.com`, or is named through an SSH host alias, is treated as
  not public, whatever its real visibility.

## Not in this release

- Limits on the session's own reads for a fact stated in words (VIL-1224). Those reads still take
  paths from the ticket without the check's path rules, as before this release.
