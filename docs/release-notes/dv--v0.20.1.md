# dv — v0.20.1

Patch release. `dv:closeout` accepts build output at the top level or nested, including files
that differ from the main checkout's copies. The other fifteen skills have no behaviour changes;
their version moves to `0.20.1` only because the suite is released as one plugin.

Numbering: 0.20.1 follows 0.20.0, which let a worktree session running `dv:manager-mode` handle
routine PR work without asking and send the Director short highlights.

Why: closeout called a finished worktree "NOT safe to delete" only because Python caches differed
from the main checkout's copies. It grouped ignored entries by top-level path, so a cache below the
top level (`tooling/evals/__pycache__/*.pyc`) showed up under `tooling/`, and it accepted only
"only here" entries as build output, so a top-level `.venv/` whose files differed blocked the
verdict too. On 2026-11-22 a review-stack closeout was blocked by 495 differing `.venv/` files and
666 differing nested `__pycache__/` files. Python and a setup step recreate both (VIL-869).

## Changed

- **`dv:closeout` Step 1, the ignored-entries listing.** An ignored entry inside a directory
  whose name is exactly `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`,
  `.mypy_cache` or `.ruff_cache`, at the top level or nested, is build output. It is listed on one line per name with its entry
  count, how many directories of that name hold the entries, and the same per-kind counts as
  before, for example
  `__pycache__/ (any depth): 666 entries in 87 directories: 0 same as the main checkout, 0 only here, 666 different, 0 not examined`.
  Other ignored entries stay grouped by top-level path, and only they are listed as "different" or
  "not examined" examples.
  - **Whole directory names only.** `myvenv/`, `venv_notes/` and a file named `venv` are not
    build output.
  - **An entry is counted once,** under the outermost name on its path:
    `node_modules/pkg/__pycache__/x.pyc` counts under `node_modules/`.
  - **A nested git repository is never build output.** A directory entry holding a `.git` file
    or directory (such as a `pip install -e git+…` clone in `.venv/src/<pkg>/`) gets its own kind,
    `nested-repo`, stays on its top-level line even under a build-output name, and is listed by
    path outside the 10-example cap. A repo git cannot open (a `.git` file pointing nowhere, a
    `.git` directory without `HEAD`) is listed file by file by git, so each entry is also checked
    for a `.git` in the directories above it, and the repo is listed once, by path. One that holds
    only its `.git` folder is not listed by git at all, so a `find` also looks for every `.git`
    file or folder below the worktree's top and lists each one, ignored or not, except an
    initialized submodule's. Top-level lines gain a nested git repos count, and the section
    heading now reads "Ignored entries and nested git repos".
  - **Names git quotes are read as they are.** The ignored entries now come from a second
    `git status --porcelain -z` call, so a name with a space or a non-ASCII character is compared
    and matched unquoted. Before, such a name was not found on disk, was listed as "not examined"
    and made the worktree not safe. The uncommitted-files listing still shows git's quoted form.
- **`dv:closeout` Step 2, "Safe once you accept losing".** Every ignored entry under a build-output
  name counts as accepted build output, whatever its kind: only here, different or not examined.
  Entries outside those names keep the old rules: anything different or not examined, or only here,
  makes the worktree not safe to delete. A nested git repository (a `.git` below the worktree's top
  that is not an initialized submodule's) also makes it not safe to delete, because it can hold unpushed commits, and the verdict names it by path (David's
  decision, 2026-11-22).
- **The verdict and the closing question** name each build-output line by its name, entry count
  and directory count. **The recheck** acts on a yes only if every build-output line is the same
  as printed, per-kind counts included, and no nested git repo is listed. It compares counts, not
  paths or contents, so a file edited in place with every count unchanged is not caught.
  Step 4 and the Orca removal offer now say what the yes covers: the listed build-output lines and
  reflog-only commits.

## Tests

- **New `tooling/evals/test_closeout_build_output.py`** runs closeout's own Step 1 block from
  `SKILL.md` against a scratch main repo and a linked worktree. It runs under bash, and under zsh
  when zsh is installed, with the system awk plus gawk and mawk when they are installed and differ
  from it. It covers differing files in a nested `__pycache__/`, a top-level `.venv/`, a
  differing ignored file outside build output, near-miss names, an entry under two names,
  nested git repos inside and outside build output and in an untracked folder with no ignore
  rule, which block "safe", repos git cannot open, a top-level initialized submodule, which is
  not listed, and names with a space or a non-ASCII character. Pointed at the 0.20.0 closeout
  `SKILL.md`, it fails. CI runs it with the other `tooling/evals/test_*.py` files.

## Documentation fixes

- **README, `dv:closeout` entry:** describes nested build output and the nested-repo rule.
- **AGENTS.md, live-checking a skill change:** a skill whose bash block is one compound command
  needs `--allowed-tools "Bash"` in the throwaway clone, and the prompt goes after `--`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
