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
Its job is whatever git doesn't do for a fresh checkout: submodules, gitignored local files,
dependencies. Done well, an agent launched into a new worktree can run the project's checks
straight away.

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
| Gitignored local files (`.env`, `.claude/settings.local.json`, machine-local tool config) | `git -C <main> ls-files -o -i --exclude-standard` | list them in `.worktreeinclude`, copy them (Step 3) |
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

## Step 3 — Write `orca.yaml`

Put it at the repo root, so it's versioned. The other place for it, the repo settings in
Orca's UI, is local and untracked. **Format:** Orca's parser isn't full YAML. Keys under
`scripts:` take two spaces and every script line takes four, as in Orca's own template:

```yaml
scripts:
  setup: |
    set -eu
    m=$ORCA_ROOT_PATH
    cd "$ORCA_WORKTREE_PATH"
    PATH="$HOME/.local/bin:$PATH"   # GUI-launched Orca may not have the shell's PATH
    git submodule update --init <path>
    # Copy from the main checkout the files .worktreeinclude names that are also
    # gitignored (the claude --worktree convention).
    if [ -f .worktreeinclude ]; then
      t=$(mktemp -d)
      trap 'rm -rf "$t"' EXIT
      git -C "$m" ls-files -o -i --exclude-standard > "$t/ign"
      git -C "$m" ls-files -o -i --exclude-from="$PWD/.worktreeinclude" > "$t/inc"
      LC_ALL=C sort -o "$t/ign" "$t/ign"
      LC_ALL=C sort -o "$t/inc" "$t/inc"
      LC_ALL=C comm -12 "$t/ign" "$t/inc" > "$t/carry"
      while IFS= read -r f; do
        if [ -n "$f" ] && [ ! -e "$f" ] && [ ! -L "$f" ]; then
          p="$f.orca-setup.$$"
          if mkdir -p "$(dirname "$f")" && cp -p "$m/$f" "$p" && ln "$p" "$f" 2>/dev/null; then
            echo "copied $f"
          elif [ -e "$f" ] || [ -L "$f" ]; then
            echo "kept $f: it appeared during setup"
          else
            echo "couldn't copy $f; copy it by hand" >&2
          fi
          rm -f "$p" 2>/dev/null || :
        fi
      done < "$t/carry"
    fi
```

- **Env:** `ORCA_ROOT_PATH` is the main checkout and `ORCA_WORKTREE_PATH` the new worktree.
  `ORCA_WORKSPACE_NAME` is set too.
- **Process:** Orca writes the script to its own `setup-runner.sh` and executes it, so
  `set -e` can't affect the user's shell. Keep it POSIX `sh`: no `<(…)`, no arrays.
- **Failures:** under `set -e`, a command inside `a && b` or an `if` condition doesn't stop
  the script. Handle each copy failure explicitly, as above. Any other failure exits early,
  so the `EXIT` trap is what removes the temp directory.
- **Don't overwrite:** an agent Orca starts with the worktree runs while setup does, and it can
  write one of these files first (Claude Code writes `.claude/settings.local.json`). So the
  script copies beside the target and `ln`s it into place: `ln` fails rather than replace a
  file that's already there.
- **`.worktreeinclude`:** one gitignore pattern per line, comments allowed. Read the list from
  the **worktree's** copy, not the main checkout's, so it travels with the branch like
  `orca.yaml` does. Every file it names must be ignored by the **repo's** `.gitignore`. A
  machine-level rule (`core.excludesFile`) works on your machine and silently skips the copy
  on any other.

## Step 4 — Test it through a real Orca worktree before merge

**Orca reads `scripts.setup` from the new worktree's own `orca.yaml`.** A worktree cut from the
default branch therefore has no script until the PR merges. Testing that way looks like
failure, but it isn't. Commit on the PR branch, then:

```bash
orca worktree create --repo id:<repoId> --name <topic>-setup-test --no-parent \
  --base-branch <pr-branch> --setup run --json
```

A run with nothing to do prints nothing and changes nothing, which looks the same as a script
that never ran. If the main checkout has none of the files `.worktreeinclude` names yet, put a
throwaway one there (one the repo gitignores) **before** running the command above, check it
arrives in the test worktree, then delete it.

`--setup run` forces the script whatever the repo's policy. The command returns before the
script finishes, so judge the run by what it leaves behind: poll, with a timeout, for the
copied files, `.venv/bin/<tool>` and whatever else Step 1 needs. Don't count on its output.
It can show in one of the new worktree's terminals, not always the first
(`orca terminal list --worktree id:<repoId>::<worktreePath>`, then
`orca terminal read --terminal <handle>` on each), but on Orca 1.4.235 (2026-10-23) a script
that finished in well under a second left nothing readable there, while one that built a
virtualenv first did. If the artifacts don't arrive, read the terminals anyway for the
error: under `set -e` a failed step, such as `git submodule update`, stops the script before
the copy. Check each gap from Step 1 is closed and `git status --short` is clean, then
remove the worktree (Step 5).

For the edge cases (a failed copy, a parent path that's a regular file, a file that appears
between the check and the copy), extract the block and
run it against a scratch `git worktree add` with both env vars set. Lint it with
`sh -n` and `shellcheck -s sh -S warning`.

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
