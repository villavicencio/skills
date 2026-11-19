# dv — v0.12.0

Minor release. It adds one skill, `dv:closeout`. The other thirteen skills have no behaviour
changes; their version moves to `0.12.0` only because the suite is released as one plugin.

## Added

### `dv:closeout`: close out a finished worktree session and brief the parent (PR #68, VIL-836)

For a session in a linked git worktree whose work is finished. A handoff (`dv:handoff`) is for
work that continues; a closeout is for work that is finished.

- **Verify, don't recall.** From git, `gh` and the tracker it checks the ticket's state; the PRs
  whose head is this branch, plus PRs you opened in the repo since the session began; uncommitted
  files; ignored entries compared one by one with the main checkout's; worktree-private git state
  (an operation in progress, per-worktree refs or config, commits reachable only from the
  worktree's reflog); submodule state; commits not on the default branch (a squash-merged PR's
  commits count as merged) and whether origin has each one; and the main checkout against its own
  upstream's tip as the remote reports it now.
- **A verdict by these checks.** Safe to delete; safe once you accept losing named build output
  and reflog-only commits; not safe (naming what would be lost); or not confirmed safe, when any
  check could not run. Every verdict carries a fixed list of what is not checked.
- **A note for the parent session**, as plain text: what shipped, tickets filed or changed, things
  noticed and not filed, decisions waiting, cleanup the parent owns, and whether a reply is
  needed. It is saved under `<git-common-dir>/closeouts/` without overwriting and copied to the
  clipboard.
- **Handoff archive.** When safe, it moves the session's handoff to `handoffs/_done/`, a detached
  worktree's included, so `dv:pickup` stops listing a closed session. A failed archive blocks the
  removal offer.
- **Nothing is removed without a yes**, and every later yes reruns the checks first.
- **Optional Orca section**, used only when the Orca CLI is on PATH: sends the note to the
  parent's agent terminal and offers `orca worktree rm`, then confirms the removal finished. Tested
  so far: the text reaches a terminal in the main checkout. Whether a parent agent acts on it is
  not yet tested.

Known limits are listed in PR #68's description.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
