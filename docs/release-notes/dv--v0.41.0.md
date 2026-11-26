# dv — v0.41.0

Minor release. `dv:groom` flags a Done means line whose file-existence test already passes on the
default branch, judged from the files tracked at its commit, without running a command from the
ticket. Only `dv:groom` changes. The other fifteen skills have no behaviour changes; their version
moves to `0.41.0` only because the suite is released as one plugin.

Why: dotfiles `docs/agents/tickets.md` says a Done means command fails on the default branch
before the work ("A Done means command fails first"), but `dv:groom` said a Done means line's
"result is not checked, only its means". So groomed tickets reached the queue with checks that
already passed and proved nothing (VIL-1169). An earlier version of this check ran the ticket's
command in a temporary copy of the repo, and review found a new way for ticket text to reach
outside the repo or a secret in each of four rounds. This one runs no command from the ticket.

## Changed

- **`dv:groom`, step 3, "Done means lines that already pass".** It checks file-existence lines
  only: `test -f <path>`, `test -e <path>`, `[ -f <path> ]` or `[ -e <path> ]`, with at most one
  `!`, written in backticks or bare at the start of the line (after the `- [ ]` box, with the rest
  of the line as the stated result). For those, grooming looks up the named path in the files
  tracked at the default branch's commit with fixed git reads of its own: `cat-file -e` for the
  commit, and `ls-tree` for the path (and its leading directories and parent when it is missing),
  each with `--no-lazy-fetch`. It uses that commit only when step 1 found its local id equal to
  origin's and the commit is in the clone, and it does not fetch. It runs no command from the ticket
  and no code from the repo, and it reports a result for each line, not file contents. A result note
  the author left in the line ("nothing at `abc1234`") is set aside.
- **A search is not run.** A `grep` or any other search line is "not run: unsupported form",
  because a result about a file's contents would let ticket text probe them.
- **Results.** Each line gets one: "already passes" (flagged), "fails in the tracked files at the
  commit" (the check does not see untracked or generated files), "guard, passes" (a line that
  says it guards unchanged behavior; not flagged), "guard, fails" (an open decision), "not run:
  <reason>" (listed apart from the lines that fail) or "observation, not checked". A line is not
  run when its command is not a file test (a search, another program, another flag, a pipe, `;`,
  `&&`, `$`, a backtick or a glob, among others); when its path is not a plain repo-relative path
  or is secret-named, in any case (`.env`, `.netrc`, key files, `*.pem`, `id_rsa*`, names holding
  `secret`, `credential`, `password` or `token`, among others); when a part of the path is named
  `.git`, in any case (git does not track it); when the path, or a directory on its way, is a link
  or a submodule; when a missing path differs only in case from a tracked one;
  when a read fails; or when what the line says passing looks like is unclear.
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

A check for search lines limited to files that are safe to disclose. Step 3's "How" still lets a
fact check run a read-only command taken from the ticket, and `dv:ticket`'s File step 5 does the
same.
