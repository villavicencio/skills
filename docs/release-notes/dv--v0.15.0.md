# dv — v0.15.0

Minor release. It adds one skill, `dv:director-mode`, and changes `dv:manager-mode` in three
places. The other thirteen skills have no behaviour changes; their version moves to `0.15.0`
only because the suite is released as one plugin.

Why: the role of the home session (the main checkout) beside worktree sessions that run
Manager Mode lived only in one project's memory note, so home sessions in other projects did not
know it, and worktree sessions merged their own PRs.

## Added

### `dv:director-mode`: the home session advises and merges while worktree managers hire (VIL-864)

- **The switch** is the same as `dv:manager-mode`'s: bare invocation turns it on, `off` turns it
  off, and one line in a project's `CLAUDE.md` or `AGENTS.md` makes it standing. The skill gives
  that line for a project whose main checkout runs Director Mode and whose worktrees run Manager
  Mode, and the `git rev-parse` comparison that tells the two apart. The on and off replies are
  fixed lines: `Director Mode on: <model> at <effort> effort.` and `Director Mode off.`, each
  followed by more lines only when needed (warning lines when on; `Still running: <agents>.`
  when off).
- **At each seam and each closeout** the Director names tickets newly unblocked (every ticket
  they are blocked by is Done; `someday` tickets skipped, Backlog ones only when their pull
  condition holds). At session start it reads the open tickets that have blockers.
- **It recommends which worktree sessions to start next** and which can run in parallel, judged
  by the files each ticket changes. A file every change touches (a version number, a changelog)
  counts as overlap that costs a rebase, not as a block. The user starts the sessions.
- **It takes `dv:closeout` notes**: checks their claims, does the cleanup they assign to it
  (removing a worktree or a branch follows the global worktree-removal procedure), brings
  decisions to the user, offers to file what was noticed and not filed.
- **It merges and cleans up from the main checkout** once MergeWren passes, following
  "Merging on a MergeWren review" in dotfiles `docs/agents/code-review.md` and the global
  worktree-removal procedure rather than a copy of them. A PR those rules don't let it merge,
  or one that needs a rebase, goes back to its worktree session. It leaves a worktree and its
  branch in place until that worktree's session has ended; the procedure's own checks decide
  removal. In a linked worktree, or with the main checkout off the default branch, it advises
  but does no merge, pull or cleanup.
- **It keeps ticket states true** at every seam, as the global Linear rules say.
- **It does not hire engineers for a ticket's work**, and does not do that work itself: a
  ticket's work belongs to its worktree session. It may hire for other work, or when asked,
  under `dv:manager-mode`'s tier and effort rules.

## Changed

- **Expected model and effort, with a warning.** A skill cannot set the session's model or
  effort (a skill's `model` and `effort` frontmatter last one turn), so each mode states the
  setting it expects and warns in one line when the mode turns on and the session differs.
  Director Mode expects Opus at `high`. Manager Mode expects Opus at `high`, or `xhigh` for a
  ticket on a safety boundary (a script that writes into the vaults, credentials, deletes); its
  ticket check says so when the ticket and the effort don't match. The model comes from the
  session's system prompt and the effort from `${CLAUDE_EFFORT}`, which Claude Code fills in
  when a plugin skill loads (checked on Claude Code 2.1.327 with `claude -p` and `--effort low`,
  `xhigh` and none: it gave `low`, `xhigh` and `medium`). A value that is not one of the five
  effort levels is reported as unknown and warned about.
- **`dv:manager-mode` no longer merges.** "merge" is gone from the commands the manager runs
  itself. A new line hands a PR that passed MergeWren to the home session, which merges it and
  cleans up; the manager never merges it, and a manager in the main checkout tells the user the
  PR is ready for `dv:director-mode`. "The team" gains a line pointing at the Director.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
