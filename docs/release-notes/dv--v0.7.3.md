# dv — v0.7.3

Patch release. It fixes `dv:mnemosyne-ops`'s freshness check and adds what the mnemosyne-hermes
0.7.1 live switch on hal taught (VIL-282). The other skills have no behaviour changes; their
version moves to `0.7.3` only because the suite is released as one plugin.

## Fixed

### `dv:mnemosyne-ops`: `freshness` no longer fails on a quiet agent, PR #57 (VIL-535)

`freshness` failed whenever nothing had been written to working memory for 48 hours. An agent
nobody had talked to, such as Atlas, whose cron runs don't autosave, read as `DRIFT`, which
blocked the VIL-282 runbook twice. The check now reads the profile's own Hermes `state.db`. It
fails only when a user turn that autosave should have stored, recorded after the last autosave
row (`source = 'conversation'`), wasn't stored. It skips the turns autosave skips:

- skip-context sources (`cron`, `subagent` and the rest);
- `ignore_patterns` matches;
- text of 5 characters or fewer;
- turns under 2 hours old.

Keying on conversation rows also catches a dead autosave that a later MEMORY.md mirror row used to
hide. Without a readable `state.db` it falls back to the 48-hour rule and says so.

`scripts/verify_freshness_check.py` runs 11 cases on temporary homes. The pre-0.7.3 script fails 6
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

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
