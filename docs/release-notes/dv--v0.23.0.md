# dv — v0.23.0

Minor release. `dv:director-mode` runs a ticket from kickoff to cleanup: the worktree session
grooms in forks-only mode and runs `dv:closeout` after the merge, the Director relays highlights
to David in its chat, answers the `Director check` probe, cleans up after a finished worktree session once David has
closed it, and has a stale PR with no live session updated by merge. The other fifteen
skills have no behaviour changes; their version moves to `0.23.0` only because the suite is
released as one plugin.

Numbering: 0.23.0 follows 0.22.0, which delivered `dv:closeout`'s note to a Director that runs as
an Orca chat (VIL-918).

Why: after `open worktree VIL-N`, David still ran grooming, triggered `dv:closeout`, and updated
stale agent PRs by hand. On 2026-11-22 he chose more autonomy: he starts each ticket, and the
rest runs on its own while the home chat keeps him up to date (VIL-917).

## Changed

- **`dv:director-mode`, "Open a worktree on request".**
  - The `orca worktree create` line passes `--surface chat`, so the session opens as an Orca
    chat whatever the host's Chat UI setting is.
  - The kickoff prompt invokes `dv:manager-mode` first. Its grooming line (kept only for a ticket
    that isn't groomed) comes after that and runs `dv:groom VIL-N forks-only` right away, before
    the first hire; the work starts once its forks are settled. Each fork is asked in the
    worktree chat. Once a Director is verified, each fork is also sent to it as a decision
    highlight; before that, manager-mode's "Highlights" rule decides (held while the probe is
    pending, never sent if no Director can be verified). Nothing waits on the Director's probe
    answer. If grooming leaves the ticket not ready or splits it, the session stops, asks David
    in the worktree chat and, under the same rule, sends the Director a decision highlight.
  - The kickoff prompt adds `After the Director reports the PR merged, run dv:closeout.`
- **New: "Relay highlights to me".** Each `Highlight, VIL-N:` message a worktree session sends is
  relayed to David in the home chat as one or two lines under the ticket id as a link. The
  Director's own merges, cleanups and newly unblocked tickets are highlights too. A highlight
  asks David nothing unless it is a decision for him.
- **New: "Answer a "Director check" probe".** The Director answers each probe that
  `dv:closeout` or `dv:manager-mode` sends with one line, the absolute path of the directory it
  runs in (in the main checkout, the main checkout's path), and nothing else, then expects that
  sender's closeout note or highlights.
- **"Take closeout notes".** The Director runs the cleanup the note names as soon as it arrives,
  still through the global removal procedure and its checks, and reports it as a highlight.
  Anything that doesn't touch the worktree or its branch is done at once. While the worktree's
  session is still running, the worktree and its branch stay in place: the Director tells David,
  as a highlight, that the session is ready to close in Orca, and removes them by the global
  procedure after the session has ended. It never signals or stops a
  session's process. Ending a finished session automatically moved to a follow-up ticket.
- **"Merge and clean up".** "Hand it back to its worktree session; you don't update it" is
  replaced. When a PR falls behind after another merge, its live worktree session updates it by
  merge. With no live session (a pilot PR counts as having none until the pilot runner updates its
  own PRs, VIL-879), the Director hires one engineer under `dv:manager-mode`'s tier and effort
  rules to update the PR, and reports it as a highlight. The engineer never touches an existing
  worktree, the PR's old one included: it makes a temporary detached worktree at
  `origin/<branch>`, merges `origin/<default branch>` in, bumps the version and pushes with `git
  push origin HEAD:<branch>`, which only fast-forwards. If the push is rejected it stops and
  reports, never forces, and the temporary worktree comes to David as a leftover; when it has
  finished, it removes that temporary worktree by the global removal procedure, and reports it to
  David as a leftover if the procedure keeps it. This also fits pilot PRs, which have no local
  worktree. A pilot PR counts only once its pilot run has ended; when that can't be told, David is
  asked. The Director still never merges a PR MergeWren hasn't passed on its new head. After a
  merge it tells a live session that the PR merged, so the session runs `dv:closeout`, and the
  branch and worktree wait for the note.
- **"Hiring"** names the one exception (the stale-PR update), and the frontmatter description
  and the README entry describe the new behaviour.

## Not tested

A full run under the new text, from
`open worktree` to cleanup, is proved on the first ticket worked after the merge and quoted on
VIL-917.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
