# dv — v0.6.0

Minor release. It ships one new skill, `dv:orca-setup`. The other eleven skills have no behaviour
changes; their version moves to `0.6.0` only because the suite is released as one plugin.

## What's new

### New skill: `dv:orca-setup`, PR #45

It writes, tests and ships an Orca setup script (`orca.yaml` `scripts.setup`) for a repo, so every new
Orca worktree starts ready to work. The skill covers:

- **What a fresh worktree lacks:** submodules, gitignored local files (copied via `.worktreeinclude`),
  dependencies. Git hooks need nothing, because they live in the shared `.git/hooks`.
- **What a setup script must never do:** change state other checkouts or the machine depend on. That
  rules out `$HOME` linkers such as Dotbot, shared databases, fixed ports, launchd jobs, tools whose first
  launch rewrites tracked files, and `git submodule deinit`. Shared caches (uv, pnpm, npm) are allowed.
- **`orca.yaml`'s format and environment:** a parser that isn't full YAML, plus `ORCA_ROOT_PATH`,
  `ORCA_WORKTREE_PATH` and `ORCA_WORKSPACE_NAME`.
- **An end-to-end test** through a real Orca worktree cut from the PR branch with `--setup run`. Orca
  reads `scripts.setup` from the new worktree's own `orca.yaml`, so a worktree cut from the default branch
  has no script until the PR merges.
- **Removal:** a checked-out submodule blocks Orca's plain delete, so removal uses Force, after a
  per-submodule check for work that exists only in that clone. The skill says not to write an archive
  script that deletes things: four review rounds on villavicencio/dotfiles#225 each found a new way one
  could lose work.

Its facts come from dotfiles#225, mostly read from the Orca app bundle and then tested. Step 0 of the
skill re-checks the flags it depends on against whatever Orca is installed.

### This repo gets its own setup script

`orca.yaml` at the repo root builds `.venv` with `skills-ref==0.1.1` on Python 3.12, as CI uses. So
`.venv/bin/agentskills validate plugins/dv/skills/<name>` works in any new Orca worktree, with no manual
venv step. It also copies the machine-local files `.worktreeinclude` names
(`.compound-engineering/*.local.yaml`, `.claude/settings.local.json`). `HANDOFF.md` is left out on purpose.

## Verification

- **Through Orca, before merge:** a worktree cut from the PR branch with `--setup run` had Python 3.12.14
  and `agentskills` in `.venv`, a byte-identical copy of the machine-local config, no `HANDOFF.md`, and a
  clean `git status`. `agentskills validate` passed inside it, and Orca's plain delete removed it.
- **After merge:** this release's own worktree, cut from `main` with the repo's default setup policy, got
  `.venv` and the copied config on its own.
- **`agentskills validate`** passes on all 12 skills, every skill and `plugin.json` read `0.6.0`, and
  `tooling/evals/test_assertions.py` and `test_trigger_parsing.py` pass.
- **CodeRabbit** reviewed #45 twice: one finding fixed (the per-submodule check), one declined and
  withdrawn by CodeRabbit (worktree-local uv directories), and no actionable comments on the second round.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The update applies on the next session restart.
