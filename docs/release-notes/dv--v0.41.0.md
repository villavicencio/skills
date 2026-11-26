# dv — v0.41.0

Minor release. `dv:groom` flags a Done means line whose command already passes on the default
branch, judged from the files tracked at its commit, without running a command from the ticket.
Only `dv:groom` changes. The other fifteen skills have no behaviour changes; their version moves
to `0.41.0` only because the suite is released as one plugin.

Why: dotfiles `docs/agents/tickets.md` says a Done means command fails on the default branch
before the work ("A Done means command fails first"), but `dv:groom` said a Done means line's
"result is not checked, only its means". So groomed tickets reached the queue with checks that
already passed and proved nothing (VIL-1169). An earlier version of this check ran the ticket's
command in a temporary copy of the repo, and review found a new way for ticket text to reach
outside the repo or a secret in each of four rounds. This one runs no command from the ticket.

## Changed

- **`dv:groom`, step 3, "Done means lines that already pass".** Two forms are checked: a file
  test (`test -f <path>`, `test -e <path>`, `[ -f <path> ]` or `[ -e <path> ]`, with at most one
  `!`) and a search of one file (`grep` with flags from `-n`, `-i`, `-q`, `-w`, `-F` and `-E`, a
  quoted pattern and one path, with at most one `!` before it). For those, grooming reads the
  named tracked file at the default branch's commit with fixed git reads of its own:
  `cat-file -e` for the commit, `ls-tree` for the path (and its leading directories and parent
  when it is missing), and, for a search, `check-attr` and `grep -q`, each with
  `--no-lazy-fetch`, plus the clone's `core.autocrlf` and `core.eol`. It uses that commit only
  when step 1 found its local id equal to origin's and the commit is in the clone, and it does not
  fetch. It runs no command from the ticket and no code from the repo, and it reports a result for
  each line, not file contents. A result note the author left in the line ("nothing at
  `abc1234`") is set aside.
- **Results.** Each line gets one: "already passes" (flagged), "fails on the default branch" (as
  far as the tracked files show), "guard, passes" (a line that says it guards unchanged behavior;
  not flagged), "guard, fails" (an open decision), "not run: <reason>" (listed apart from the lines
  that fail) or "observation, not checked". A line is not run when its command is in neither form
  (a pipe, `;`, `&&`, `$`, a backtick, a glob, `-r` or another program, among others); when its
  path is not a plain repo-relative path or is secret-named, in any case (`.env`, `.netrc`, key
  files, `*.pem`, `id_rsa*`, names holding `secret`, `credential`, `password` or `token`, among
  others); when its
  pattern is empty, starts with `-`, or holds a quote, `$`, a backtick, a backslash or a line
  break; when the path, or a directory on its way, is a link or a submodule; when a missing path
  differs only in case from a tracked one; when a checkout would change a searched file's bytes
  (a `filter`, `working-tree-encoding`, `ident` or `crlf` attribute, an `eol` other than `lf`,
  `core.autocrlf` set to anything but `input` or false, `core.eol` set to anything but `lf` or
  `native`, or a groomer on Windows; Git LFS and CRLF line endings are such cases); when a read
  fails; or when what the line says passing looks like is unclear.
- **A flagged line is an open decision:** rewrite it so it fails first, or keep it as a guard of
  unchanged behavior with the reason in the line. In `forks-only` mode a rewrite that fails is a
  routine call, and so is the guard mark when the ticket says the behavior must not change; when
  neither fits, what to do with the line is a fork, and dropping it is a fork, as dropping any
  Done means line already was. A flagged line left as it is counts against the ready test, so the
  ticket gets no new `groomed` label; a line not run does not count against it.
- **Steps 6 and 8.** The findings before the interview and the report list each line's result.
  The bullet before the new check says to look for a Done means line's means, not to run its
  command.
- **README.** The version, and the `dv:groom` entry.

## Not in this release

Step 3's "How" still lets a fact check run a read-only command taken from the ticket, and
`dv:ticket`'s File step 5 does the same.
