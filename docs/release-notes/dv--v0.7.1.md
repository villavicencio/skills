# dv — v0.7.1

Patch release. It fixes `dv:pickup`, `dv:cite`, `dv:review-claudemd` and `dv:orca-setup`, and
prepares `dv:mnemosyne-ops` for the mnemosyne-hermes 0.7.1 upgrade on hal. The other skills have
no behaviour changes; their version moves to `0.7.1` only because the suite is released as one
plugin.

## Fixed

### `dv:pickup`: text typed after the command no longer garbles Step 1b, PR #52

Claude Code substitutes the words typed after a skill command for `$0`, `$1`, … anywhere in the
skill text, fenced code included (CLI 2.1.309: `/\$(\d+)(?!\w)/g` over the whole text). Step 1b's
`get()` helper used `$1` and its awk used `$0`, so `/dv:pickup some words` blanked every other
session's branch, head and focus, skipped the merged-PR archive, and emptied the worktree list.
`get()` now takes its key from a variable and the awk uses `$(0)`. Typed text now reaches the skill
as an appended `ARGUMENTS:` line instead of being silently consumed.

`dv:cite` had the same exposure in its prose: amounts such as `$1,250` were replaced by argument
words. They're written as `USD 1,250` now, and its eval's quoted-price guard matches that form.

A new CI step, `tooling/check_skill_placeholders.py`, fails on any `$` followed by a digit in a
`SKILL.md`.

### `dv:review-claudemd`: Step 6 no longer deletes other runs' scratch dirs, PR #51

Step 6 removed `claudemd-review.*` under `$TMPDIR`, which matched every concurrent run's scratch
dir. It now removes only this run's dir (the path Step 2 printed), and sweeps leftovers from
aborted runs only when the dir and everything in it are over 24 hours old. A new test,
`tooling/evals/test_review_claudemd_cleanup.py`, runs the real Step 2 and Step 6 blocks under bash
and zsh with BSD and GNU find.

### `dv:orca-setup`: Orca copies `.worktreeinclude` itself, PR #49

Orca 1.4.235 copies `.worktreeinclude` entries before setup runs, reading the file from the main
checkout and taking literal paths only. The skill no longer has the setup script copy them, and
Step 4 judges a test run by the artifacts it leaves rather than by its output. A repo with no
`orca.yaml` drops the script checks. A PR that changes `.worktreeinclude` or its `.gitignore`
rules can only show Orca's copy after merge.

## Changed

### `dv:mnemosyne-ops`: tested pair 3.15.1 + 0.7.1, PR #53

- `TESTED_PAIRS` adds `("3.15.1", "0.7.1")` and keeps `("3.15.1", "0.5.0")`, so the health check
  reads HEALTHY before, during and after the switch on hal, and after a rollback.
- Upstream 0.7.1 ships the multiplex bank-root fix, so carried patch D retires; patch C is still
  carried. New `apply_patch_c.py` applies it idempotently, checks every installed file against
  the wheel's RECORD hashes, and fails on any file the wheel didn't install. Don't use mnemosyne-hermes 0.7.2 (upstream: it installs on stable core,
  then fails at provider init).
- The health check reads both wrapper formats (0.7.x keeps the venv in `mnemosyne-wrapper.json`).
- `enable_profile.py` and `verify_tools_config.py` no longer hard-code the retired VPS's
  `/home/node`; new `verify_multiplex_isolation.py` runs the A→B→A check.

The live upgrade on hal is a separate step run as the `hal` account.

## Also in this release

- **This repo's own Orca setup**, PR #50: `.worktreeinclude` lists literal paths, `.gitignore` covers
  `.claude/settings.local.json`, and `orca.yaml` no longer copies files.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The update applies on the next session restart.
