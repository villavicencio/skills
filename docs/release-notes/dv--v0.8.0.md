# dv — v0.8.0

Minor release. It adds the skill `dv:manager-mode`. It also carries everything planned for 0.7.3,
which was never released: its notes are folded in below. Tag `dv--v0.7.2` exists on origin, but no
GitHub release was made for it and, to our knowledge, no machine has it installed. So this release includes
what 0.7.2 shipped as well (the shorter `dv:pickup` kickoff, see `docs/release-notes/dv--v0.7.2.md`).
The other skills have no behaviour changes; their version moves to `0.8.0` only because the suite
is released as one plugin.

## Added

### `dv:manager-mode`: one copy of the Manager Mode text, with a switch, PR #61

The skill makes a session work as an engineering manager. The session plans, briefs, checks
and reports. Agents it hires do all the engineering, and every hire names a model tier and an
effort with a one-line reason.

- **On:** invoke `dv:manager-mode`. Text after the skill name is the first request.
- **Off:** invoke `dv:manager-mode off`. The session goes back to doing the work directly. Running
  agents keep going and their reports are handled as ordinary work.
- **Standing:** a project puts one line in its `CLAUDE.md` or `AGENTS.md` telling sessions to
  invoke the skill at the start. The text is not copied into projects.

One stated exception: a procedure that starts its own agents and cannot be given a model and effort
per agent (such as `dv:critique` and `dv:gauntlet`) is run by an engineer on a named tier, and the
written state records what its agents run on.

The review-round rules are not in the skill. It links the "Fix rounds" section of
`docs/agents/code-review.md` in the dotfiles repo, and tells the session to ask when it cannot read it.

## Fixed

### `dv:mnemosyne-ops`: `freshness` no longer fails on a quiet agent, PR #57 (VIL-535)

`freshness` failed whenever nothing had been written to working memory for 48 hours. An agent
nobody had talked to, such as Atlas, whose cron runs don't autosave, read as `DRIFT`, which
blocked the VIL-282 runbook twice. The check now reads the profile's own Hermes `state.db`. Once the
bank has any working-memory rows, it fails only when a user turn that autosave should have stored, recorded after the last autosave
row (`source = 'conversation'`), wasn't stored. It skips the turns autosave skips:

- skip-context sources (`cron`, `subagent` and the rest);
- `ignore_patterns` matches;
- text of 5 characters or fewer;
- turns under 2 hours old.

Keying on conversation rows also catches a dead autosave that a later MEMORY.md mirror row used to
hide. Without a readable `state.db` it falls back to the 48-hour rule and says so. A bank with no
working-memory rows at all, or no bank, fails before any of this.

`plugins/dv/skills/mnemosyne-ops/scripts/verify_freshness_check.py` runs 11 cases on temporary homes. The script from before this fix fails 6
of them. On hal, Atlas and Axiom both read HEALTHY, and their turn and write times line up in
UTC. Known limit: an unstored turn in the same second as the last autosave row is missed,
because `created_at` stores whole seconds. The next turn still fails the check.

## Changed

### `dv:mnemosyne-ops`: restart list, backup nesting, and hand-patch leftovers, PR #56

- **Restarts after an upgrade.** The generic step names every process that loads the provider:
  per-profile gateways, `hermes serve`, the web UI and interactive TUIs. A hal example lists its
  five processes, how to restart each one, and how to prove the restart with `ps -o lstart=`.
  It also covers:
  - `launchctl print` rather than `launchctl list`;
  - tmux `-L` names a socket, not a session;
  - Ctrl-b doesn't detach.
- **Backup step.** `cp -a` into a directory that already exists nests a second copy inside it.
  Back up to a directory that doesn't exist yet.
- **Gotcha.** Hand-patch leftovers such as `__init__.py.orig-0.5.0` aren't in the wheel's
  `RECORD`. They survive uninstall and fail `apply_patch_c.py`. Act on the check's own
  `(not in RECORD)` entries: inspect each one, then move it out of the venv keeping its path. Never
  delete one.

## Repository

- PR #58: MergeWren is now this repo's review gate. CodeRabbit's automatic reviews are off
  (`.coderabbit.yaml`), and agents don't request them here.

## Docs

- PR #60: `dv:orca-setup` records four Orca 1.4.257 behaviours (the setup script runs under bash
  in a "Setup" tab, `--base-branch` takes an unpushed local branch, `orca worktree rm` keeps the
  local branch by default, and `orca worktree list` can hide `.claude/worktrees/` worktrees).

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
