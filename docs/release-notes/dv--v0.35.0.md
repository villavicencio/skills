# dv — v0.35.0

Minor release. `dv:director-mode` sweeps stale ticket states when its session starts: it corrects
the repo project's In Progress and In Review tickets whose linked PRs are all merged or closed.
The other fifteen skills have no behaviour changes; their version moves to `0.35.0` only because
the suite is released as one plugin.

Numbering: 0.35.0 follows 0.34.0, which let the Director end a finished worktree session after
four checks.

Why: stale states pile up unseen. On 2026-11-22 the mergewren board had four tickets In Progress
for one to three weeks after their PRs merged, and one In Review for eight weeks (VIL-911).

## Changed

- **`dv:director-mode`, "At each seam and each closeout".** A new bullet runs at the start of the
  session only:
  1. List the repo project's tickets that are In Progress or In Review, using the state names
     `list_issue_statuses` returns. A `someday` ticket and a Backlog ticket are skipped.
  2. Find each ticket's linked PRs: the GitHub pull request URLs among its `get_issue`
     attachments, plus the PRs the `gh pr list` commands of the Ownership lookup find for the
     ticket (pointed at, not copied). Read each with `gh pr view <url> --json state,isDraft,body`.
     A failed read leaves the ticket as it is, named.
  3. Flag a ticket with at least one linked PR and no open PR, a draft counting as open. A ticket
     with no linked PR is named and not moved, since it may be In Progress with no PR on purpose.
  4. Run the Ownership lookup in `dv:manager-mode`'s "Before the first brief: check the ticket"
     (pointed at, not copied) for each flagged ticket. A ticket a live session owns keeps its
     state and is named. When a lookup can't run, or the session can't see other sessions (under
     Codex, `list_agents` lists only its own agents), the owner is unknown: the ticket keeps its
     state and is named.
  5. Move the rest by the global state rule: Done when a merged linked PR's description has a
     closing word from the list in dotfiles `docs/agents/tickets.md`, "Linking a PR to a ticket
     without closing it", followed by the ticket's id, such as `Fixes VIL-N`; the PR title does
     not count. Otherwise Todo (a non-closing word such as `Refs VIL-N`, or all PRs closed
     unmerged). Just before each write the ticket's state and PRs are read again; if either
     changed since step 2, the ticket keeps its state and is named. Each move gets a one-line
     comment naming the PR.
  6. The session-start report has one line per moved ticket, and names each ticket left as it is
     with the reason.
- **"Keep ticket states true".** Points at the sweep, and says it follows the global state rule
  only, not a repo's own meanings for a state.
- **"Maintaining this text".** Last reviewed 2026-11-25.
- **README.** The `dv:director-mode` entry names the session-start sweep.

## Decisions

- Done only when a merged linked PR's description closes the ticket; otherwise Todo (David
  Villavicencio, 2026-11-24).
- The sweep moves only a ticket with at least one linked PR and none open or draft; a ticket with
  no linked PR is named, not moved (2026-11-25). A standing health-check ticket in hal-pilot is
  In Progress with no PR by design.
- The sweep follows the global state rule, with no repo-override clause (2026-11-25).
