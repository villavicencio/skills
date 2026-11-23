# dv — v0.19.1

Patch release. `dv:closeout` accepts build output at any depth, including files that differ from
the main checkout's copies. The other fifteen skills have no behaviour changes; their version moves
to `0.19.1` only because the suite is released as one plugin.

Numbering: 0.19.1 follows 0.19.0, which made `dv:manager-mode` hand ticket work in the main
checkout to a worktree session.

Why: closeout called a finished worktree "NOT safe to delete" only because Python caches differed
from the main checkout's copies. It grouped ignored entries by top-level path, so a cache below the
top level (`tooling/evals/__pycache__/*.pyc`) showed up under `tooling/`, and it accepted only
"only here" entries as build output, so a top-level `.venv/` whose files differed blocked the
verdict too. On 2026-11-22 a review-stack closeout was blocked by 495 differing `.venv/` files and
666 differing nested `__pycache__/` files. Python and a setup step recreate both (VIL-869).

## Changed

- **`dv:closeout` Step 1, the ignored-entries listing.** An entry inside a directory named
  `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` or
  `.ruff_cache/`, at any depth, is build output. It is listed on one line per name with its entry
  count, how many directories of that name hold the entries, and the same per-kind counts as
  before, for example
  `__pycache__/ (any depth): 666 entries in 87 directories: 0 same as the main checkout, 0 only here, 666 different, 0 not examined`.
  Other ignored entries stay grouped by top-level path, and only they are listed as "different" or
  "not examined" examples.
  - **Whole directory names only.** `myvenv/`, `venv_notes/` and a file named `venv` are not
    build output.
  - **An entry is counted once,** under the outermost name on its path:
    `node_modules/pkg/__pycache__/x.pyc` counts under `node_modules/`.
- **`dv:closeout` Step 2, "Safe once you accept losing".** Every ignored entry under a build-output
  name counts as accepted build output, whatever its kind: only here, different or not examined.
  Entries outside those names keep the old rules: anything different or not examined, or only here,
  makes the worktree not safe to delete.
- **The verdict, the closing question and the recheck** name each build-output line by its name,
  entry count and directory count. A yes is acted on only if the recheck finds the same lines.
  Step 4 and the Orca removal offer now say what the yes covers: the listed build-output lines and
  reflog-only commits.

## Tests

- **New `tooling/evals/test_closeout_build_output.py`** runs closeout's own Step 1 block from
  `SKILL.md` against a scratch main repo and a linked worktree, under bash and zsh and every awk
  present. It covers differing files in a nested `__pycache__/`, a top-level `.venv/`, a
  differing ignored file outside build output, near-miss names, an entry under two names, and
  nested repos ("not examined") inside and outside build output. Pointed at the 0.19.0
  `SKILL.md`, it fails. CI runs it with the other `tooling/evals/test_*.py` files.

## Documentation fixes

- **README, `dv:closeout` entry:** describes build output at any depth.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
