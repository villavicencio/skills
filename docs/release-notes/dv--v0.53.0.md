# dv — v0.53.0

Minor release. Every dv skill now checks, as its first step, that the dv it was loaded from is the
latest stable release, and holds its dv-dependent actions when it is stale or the check can't be
verified. All sixteen skills change the same way; `dv:director-mode` and `dv:manager-mode` also
run the check again before each later dv-dependent action.

Numbering: 0.53.0 follows 0.52.0 (PR 132, merged).

Why: a session keeps the dv version it loaded when it started, so an agent can run old rules for
hours after a release. On 2026-11-24 sessions still ran 0.32.0 after 0.34.0 was out; on
2026-11-27 the skills Director ran 0.48.0 while 0.51.0 was out, and re-invoking the skill in that
session still loaded 0.48.0. The Head of Skills set the rule as his item 78, from David
(VIL-1083).

## Added

- **`dv-latest-check`** (`plugins/dv/scripts/dv_latest_check.py`, stdlib Python 3.9+). Run with
  the skill's base directory as the client reported it at load time:
  `python3 -I "<base directory>/../../scripts/dv_latest_check.py" "<base directory>"`. It reads:
  - the loaded version, from the `…/plugins/cache/<marketplace>/dv/<version>/skills/<name>` path
    (Claude Code's "Base directory for this skill"; Codex reports the same versioned cache path,
    `~/.codex/plugins/cache/villavicencio-skills/dv/<version>/skills/<name>`), even when an update has
    since removed that directory (Codex replaces it on update). A path outside a plugin
    cache (a `--plugin-dir` development copy) falls back to `metadata.version` in its `SKILL.md`;
  - the latest release: the highest `dv--v<version>` tag among the repository's stable releases
    (`gh release list --exclude-drafts --exclude-pre-releases --limit 100`; drafts, pre-releases
    and other plugins' tags are ignored);
  - the installed version: Claude Code's `<home>/plugins/installed_plugins.json` entry
    `dv@<marketplace>` (the user-scope entry when there is one), or, in a home with no such file
    (Codex), the highest version directory in `<home>/plugins/cache/<marketplace>/dv/`. A
    development copy has no installed version (`installed unknown`).

  Its first line is one of `current` (exit 0), `stale` (exit 1; names the loaded, latest and
  installed versions and says either that a fresh session picks up the update or that the install
  itself is behind) or `not verified` (exit 2; the release or the base path can't be read).
  `DV_LATEST_CHECK_GH`, when set, names a stand-in `gh` for tests and live checks (a Codex shell
  rebuilds `PATH` from the login profile, so a stand-in on `PATH` is not seen there).
- **Every dv skill's first section, "First step: dv-latest-check"** (identical in all sixteen):
  run the check with the base directory given at load time, never a newer path on disk; give it
  network access (a Codex sandbox blocks it, and the check then says `not verified`); if an update
  removed the loaded copy, run the newest copy of the script in the same plugin cache with the
  same base directory; quote its first line (none counts as `not verified`); on `stale` or
  `not verified`, hold every dv-dependent action and say why, while work that doesn't depend on
  dv continues and turning a mode `off` is never held.
- **`dv:director-mode` ("What you do") and `dv:manager-mode` ("Running the team")** rerun the check
  before each later dv-dependent action: a merge, a closeout, ending a session, a hire, a brief, a
  Linear write.
- **Tests:** `tooling/evals/test_dv_latest_check.py` (stand-in `gh`; current, stale, install
  behind the release, release unreadable, base path unreadable or malformed, and the identical
  first step in all sixteen skills), run by CI's validate job.

## Changed

- **README:** the dv entry, a paragraph under "Skills at a glance" that covers every skill's first
  step, the version, and the layout (`plugins/<plugin>/scripts/`).
- **AGENTS.md:** the live-check recipe notes that a `--plugin-dir` copy is checked by its
  `metadata.version`, and how to see the stale outcomes with a stand-in cache path.
- **`dv:director-mode` `scripts/head_wait.py`:** `VERSION` moves to `0.53.0` with the plugin, as
  its test requires.

## Unchanged

- Every skill's own steps. Installing and auto-updating dv on each machine is VIL-1090 and
  VIL-1091 (Dotfiles), not this release.
