---
name: orca-setup
description: "Write, test, and ship an Orca setup script (orca.yaml scripts.setup) for a repo, so every new Orca worktree starts ready to work: submodules checked out, gitignored local files copied in, dependencies installed, and no change to state other checkouts or the machine depend on (shared caches excepted). Covers where Orca reads the file from, its parser's format, the env vars it passes, an end-to-end test through a real Orca worktree before merge, and why not to write an archive script that deletes things. Use when the user asks for an Orca setup script, a worktree setup hook, or orca.yaml, when adding a repo to Orca, or when new Orca worktrees come up missing files, dependencies or submodules."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.7.0"
---

# /orca-setup — An Orca setup script that works the first time

Orca runs a repo's **setup script** once in each worktree it creates, before you work there.
Its job is whatever git doesn't do for a fresh checkout: submodules and dependencies. Orca
copies gitignored local files itself, from the paths `.worktreeinclude` lists (Step 3). Done
well, an agent launched into a new worktree can run the project's checks straight away.

Origin: villavicencio/dotfiles#225 (2026-10-18 to 10-21). Most facts below came from reading
the Orca app bundle, not from docs, so Step 0 re-checks the ones that matter.

## Step 0 — Resolve the CLI and re-check Orca's behavior

Use the executable the `orca-cli` skill resolves (`orca` on macOS; never bare `orca` on Linux
outside an Orca terminal, which is the GNOME screen reader). Then confirm the facts this skill
depends on still hold for the installed version:

```bash
orca worktree create --help | grep -E -- '--setup|--base-branch'
orca worktree rm --help | grep -E -- '--force|--run-hooks'
orca repo show --repo id:<repoId> --json | jq .result.repo.hookSettings
```

If a flag is gone or renamed, stop and re-derive before writing anything. Step 4's real test
is the final check either way.

## Step 1 — Find what a fresh worktree is missing

Compare the main checkout with a worktree made from the default branch. Check each of these:

| Gap | How to see it | Usual fix in setup |
|---|---|---|
| Submodules | `git submodule status` lines starting `-` | `git submodule update --init <path>` |
| Gitignored local files (`.env`, `.claude/settings.local.json`, machine-local tool config) | `git -C <main> ls-files -o -i --exclude-standard` | none: list each path in `.worktreeinclude` and Orca copies it (Step 3) |
| Dependencies, virtualenvs | the project's own install step | `pnpm install`, `uv venv` + `uv pip install`, … |
| Git hooks | nothing: hooks live in the shared `.git/hooks` | none |

Skip per-session files such as `HANDOFF.md`: each worktree should start its own.

## Step 2 — Rule out anything other checkouts depend on

The script runs unattended in every new worktree, so it must not change state that other
checkouts or the machine depend on. **Shared caches are fine** and intended: uv's
`~/.cache/uv` and managed Pythons, pnpm's store, npm's cache. They're add-only and shared by
design, and a per-worktree cache would only make every new worktree download everything
again. Never:

- **Run an installer that links into `$HOME`** (Dotbot, Stow, a dotfiles `./install`). The
  links would point into the worktree and dangle once it's removed.
- **Migrate or seed a shared database, bind a fixed port, or register a launchd/systemd job.**
- **Start a tool whose first launch rewrites tracked files** (Neovim's lazy.nvim rewrites
  `lazy-lock.json`).
- **Run `git submodule deinit`.** In a linked worktree it unsets `submodule.<name>.*` in the
  config every checkout shares, so the main checkout's submodule reads as uninitialized. Repair:
  `git -C <main> submodule init <path>`.

Write each rule the repo needs into its `CLAUDE.md`/`AGENTS.md` too, next to the script.

## Step 3 — Write `orca.yaml`, and list local files in `.worktreeinclude`

Put `orca.yaml` at the repo root, so it's versioned. The other place for it, the repo settings
in Orca's UI, is local and untracked. **Format:** Orca's parser isn't full YAML. Keys under
`scripts:` take two spaces and every script line takes four, as in Orca's own template:

```yaml
scripts:
  setup: |
    set -eu
    cd "$ORCA_WORKTREE_PATH"
    PATH="$HOME/.local/bin:$PATH"   # GUI-launched Orca may not have the shell's PATH
    git submodule update --init <path>
    # then the project's install step: pnpm install, uv venv + uv pip install, …
```

- **Env:** `ORCA_ROOT_PATH` is the main checkout and `ORCA_WORKTREE_PATH` the new worktree.
  `ORCA_WORKSPACE_NAME` is set too.
- **Process:** Orca writes the script to its own `setup-runner.sh` and executes it, so
  `set -e` can't affect the user's shell. Keep it POSIX `sh`: no `<(…)`, no arrays.
- **Failures:** under `set -e`, a command inside `a && b` or an `if` condition doesn't stop
  the script. Handle those failures explicitly.
- **Nothing to set up?** If a fresh worktree needs only local files, write no `orca.yaml` at
  all.

**Local files go in `.worktreeinclude`, not the script.** Orca copies them itself: in 1.4.235
its worktree-create pipeline runs `copy_worktreeinclude` before `prepare_setup`, whether or
not setup runs (found in orcad's server bundle, 2026-10-23). It's the same file
`claude --worktree` reads. What Orca's copy does:

- It reads `.worktreeinclude` from the **main checkout**, not the new worktree, so an entry
  takes effect once it's in the main checkout, not on a branch.
- It takes **literal file or directory paths only**: one per line, with comments and blank lines
  allowed. A line with `*`, `?` or a leading `!` is skipped with a warning in Orca's log, so
  write each path out.
- It copies an entry only if the path exists in the main checkout and `git check-ignore` says
  it's ignored. Ignore each one in the repo's own `.gitignore`: a machine-level rule
  (`core.excludesFile`) works on your machine and silently skips the copy on any other.
- It skips entries over its copy budget and logs a warning.

Don't script the copy as well. The script would duplicate Orca's copy and race both it and the
agent Orca starts with the worktree, which can write `.claude/settings.local.json` while setup
runs. villavicencio/hal-bench#1 spent three review rounds hardening a scripted copy (temp file
and `ln`, then an `O_EXCL` create) before it turned out Orca had already copied the files.

## Step 4 — Test it through a real Orca worktree before merge

**Orca reads `scripts.setup` from the new worktree's own `orca.yaml`.** A worktree cut from the
default branch therefore has no script until the PR merges. Testing that way looks like
failure, but it isn't. Commit on the PR branch. If the main checkout has none of the files
`.worktreeinclude` names yet, put a throwaway one there (one the repo gitignores) **before**
the next command, so the test shows Orca's copy working. Then:

```bash
orca worktree create --repo id:<repoId> --name <topic>-setup-test --no-parent \
  --base-branch <pr-branch> --setup run --json
```

`--setup run` forces the script whatever the repo's policy. **A repo with no `orca.yaml`**
(local files only, Step 3) has no script to force, read or lint: drop `--setup run`, poll for
the included files with the same timeout as below and name any that never arrive, check
`git status --short`, then delete the throwaway file and remove the test worktree (Step 5).
Skip the terminal reading and linting below.

**A PR that changes `.worktreeinclude`, or the `.gitignore` rules for its paths, can't show
Orca's copy before merge.** Orca reads both from the main checkout (Step 3), so a worktree cut
from the PR branch is copied by the old rules. Test the rest before merge, and test the copy
after merge with a worktree cut from the default branch.

With a script, the command returns before it finishes, so judge the run by what it leaves
behind: poll, with a timeout, for the artifacts Step 1 needs (the submodule checkout,
`.venv/bin/<tool>`, the included files). The script's output shows in one of the new
worktree's terminals, not always the first
(`orca terminal list --worktree id:<repoId>::<worktreePath>`, then
`orca terminal read --terminal <handle>` on each). If the artifacts don't arrive, read them for
the error: under `set -e` a failed step, such as `git submodule update`, stops the script
there. Check each gap from Step 1 is closed and `git status --short` is clean, then delete the
throwaway file and remove the worktree (Step 5).

With a script, lint the extracted script with `sh -n` and `shellcheck -s sh -S warning`. For
failure cases, run it against a scratch `git worktree add` with both env vars set.

## Step 5 — Removing worktrees: Force, and no archive script

- **A submodule blocks a plain delete.** `git worktree remove` refuses a worktree with an
  initialized submodule, and Orca's plain delete doesn't pass `--force`. Orca then reports
  `removed: true, removing: true` while the worktree stays, stuck in "removing". Use
  `orca worktree rm --force`. It removes the directory (gitignored files and the submodule
  clone included), the git registration and Orca's entry, and deletes the branch only when
  Orca can prove it's merged.
- **Before Force, check the worktree being removed,** not the main checkout:
  `git -C "$W" status --porcelain --ignored --untracked-files=all`. Without
  `--untracked-files=all`, git collapses a directory into one `!! dir/` line.
- **Then check every initialized submodule.** Force deletes each submodule clone too, and a
  clean status, the parent's or the submodule's, doesn't show work that exists only in that
  clone. This lists, per submodule, its uncommitted changes, stash entries, and commits on
  local branches that no remote-tracking branch has:

  ```bash
  git -C "$W" submodule foreach --quiet --recursive \
    'echo "== $sm_path"; git status --porcelain; git stash list; git log --oneline --branches --not --remotes'
  ```

  Anything under a `==` line must be pushed or copied out first. Tags you created there aren't
  listed (`--tags` would also flag upstream release tags), so push those by hand. Remote-tracking
  refs can be stale, so an empty list is a strong hint, not proof.
- **Don't write a `scripts.archive` that deletes things.** dotfiles#225 tried one to clear
  the submodule automatically. Four review rounds each found a new way it could lose work: a
  staged gitlink, remote-tracking refs that outlive their branch, a tag-only pin, ref names,
  unreferenced objects. A script can't prove a clone is safe to delete. If one is ever needed
  for something harmless, Orca reads it from the **main checkout's** `orca.yaml`, and
  `orca worktree rm` skips it unless passed `--run-hooks`.

## Step 6 — Repo settings in Orca

- **Pin the base ref** when the main checkout may sit on a feature branch, so new worktrees
  start from the default branch and get the script:
  `orca repo set-base-ref --repo id:<repoId> --ref origin/main`.
- `setupRunPolicy: run-by-default` and `setupAgentStartupPolicy: start-immediately` are the
  defaults. An agent launched with the worktree starts while setup is still running, so keep
  setup fast or tell the agent to wait for it.

## Gotchas

- **`orca worktree rm` returns `ok: true` before removal finishes** (`removing: true`). Re-check
  `git worktree list` and `orca worktree list` before reporting a removal.
- **Orca names branches `<user>/<name>`.** Rename with `git branch -m` if the repo has a
  convention (`feat/…`); Orca tracks the worktree by path.
- **Other top-level `orca.yaml` keys exist** (`setupAgentStartupPolicy`, `defaultTabs`,
  `issueCommand`, `environmentRecipes`, `worktree`). They're unverified here, so read Orca's
  settings-page template before using one.
