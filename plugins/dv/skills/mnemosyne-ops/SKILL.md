---
name: mnemosyne-ops
description: "Enable, health-check, and maintain the Mnemosyne memory provider on a Hermes profile without disturbing anything else in it. Gated enable (before/after integrity hashes, memory-block-only config splice, provider smoke through Hermes' own loader), a read-only health check for the known drift classes (carried patch lost on upgrade, installer override skill reappearing, injected system turns leaking into the store), and a tools-subset verifier. Use when turning Mnemosyne on for a profile, after any mnemosyne-hermes or Hermes upgrade, when recall seems polluted or empty, or before migrating Hermes to another host."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.7.0"
---

# /mnemosyne-ops — Mnemosyne on Hermes, operated safely

Mnemosyne is a local, SQLite-backed external memory provider for Hermes: it autosaves user
turns, embeds them (fastembed / bge-small, no LLM), and prefetches relevant ones into each new
turn. It **augments** `MEMORY.md` / `USER.md`, the Obsidian vault, and session search. It never
replaces them. Origin and evidence: VIL-143 (`~/Projects/mnemosyne-pilot/DECISION.md` on the
VPS).

**Host-specific by design.** Assumes Hermes at `~/.hermes/hermes-agent` (with its `venv/`), the
side-venv install at `~/.hermes/venvs/mnemosyne` (python3.11, the same minor as Hermes' venv), and
the wrapper plugin at `<home>/plugins/mnemosyne`, all under the account that runs Hermes. Pinned to
`mnemosyne-memory==3.15.1` and `mnemosyne-hermes==0.7.1` with patch C carried. The previous pair,
0.5.0 with patches C and D, is the rollback target; both pairs are in `TESTED_PAIRS`.

## Step 1 — Health check first, always

Run every command below from this skill's directory (`plugins/dv/skills/mnemosyne-ops/` in a repo checkout, or the installed plugin's copy), so `scripts/` resolves:

```bash
cd "$(dirname "$(find ~/Projects/skills ~/.claude/plugins -path '*mnemosyne-ops/SKILL.md' 2>/dev/null | head -1)")"
```

```bash
~/.hermes/hermes-agent/venv/bin/python scripts/mnemosyne_health.py --home ~/.hermes
```

Read-only. Exit 0 means healthy and exit 1 means drift. Each `FAIL` line names its fix:

| Check | Drift it catches | Fix |
|---|---|---|
| `config` | `config.yaml` missing or invalid YAML | fix the file; every other check is unreliable until this passes |
| `provider` | provider switched off | `hermes config set memory.provider mnemosyne` |
| `tools` | full 40-tool surface (~6.5k tok/request) | set `memory.mnemosyne.tools` (6 for Atlas, 3 suggested elsewhere) |
| `filters` | Hermes cron / background-process / system-note turns being stored as `[USER]` | re-run `enable_profile.py` (it writes `ignore_patterns`) |
| `patch` | fix C or D is not in effect in the loaded provider code: C (MEMORY.md mirrors become session-only) or D (non-default profiles' banks land in the default home under `hermes serve`). The check is functional: upstream 0.7.1 ships fix D, so it passes there without a carried patch D | re-apply patch C (Step 4); on 0.5.0, also patch D |
| `isolation` | another profile's bank is living under this home: the multiplex leak | run 0.7.1 (or 0.5.0 with patch D), restart `hermes serve`, and move the bank (export, then import into its owner's home) |
| `override` | installer re-dropped `mnemosyne-memory-override`, which tells the agent MEMORY.md is deprecated | delete `<home>/skills/memory/mnemosyne-memory-override` |
| `leak` | injected system turns stored in the last 7 days | widen `ignore_patterns`; invalidate the rows |
| `freshness` | autosave silent > 48h | check `hermes memory status`, the gateway log |
| `versions` | the installed (core, hermes) pair isn't one we've tested (`TESTED_PAIRS`: 3.15.1 + 0.7.1, and 3.15.1 + 0.5.0 for rollback) | run the pilot verification on throwaway homes (Step 3), then add the pair to `TESTED_PAIRS` |

## Step 2 — Enable on a profile

```bash
~/.hermes/hermes-agent/venv/bin/python scripts/enable_profile.py \
    --home ~/.hermes --identity default --tools 6 --dry-run      # then without --dry-run
```

The script runs these gated steps and stops at the first failure:

0. sha256 `config.yaml` / `MEMORY.md` / `USER.md`, then write a config backup to
   `$MNEMOSYNE_OPS_RECORDS` (default `~/.hermes/mnemosyne/records`).
1. Install the wrapper plugin. This is idempotent: it skips if the wrapper already points at
   the side venv and refuses if it points elsewhere. 1b removes the installer's override skill.
2. **Splice only the `memory:` block** into `config.yaml`. Do not use `hermes config set`,
   which strips every YAML comment, and do not round-trip the whole document, which re-indents
   lists and re-wraps long strings.
3. Hash everything again. `MEMORY.md` and `USER.md` must be byte-identical, and the config diff
   must stay inside the memory block, both semantically and textually. Otherwise the step exits
   non-zero and the backup restores the file.
4. Load the provider through Hermes' own `load_memory_provider`. Assert that the tool list
   equals the configured subset and that the DB sits under `<home>`.

Any profile other than `default` requires `--owner-confirmed`. Each profile's memory belongs
to its owner. `MNEMOSYNE_VENV=<venv>` points the wrapper at a candidate side venv instead of the
live one, and `MNEMOSYNE_OPS_RECORDS=<dir>` keeps a pilot's backups out of the live records; Step 3
uses both.

New sessions pick the provider up. A session that was already running keeps the toolset it
started with.

## Step 3 — Pilot a new pair on throwaway homes (before any upgrade)

Build the candidate side venv somewhere else, apply patch C to it (Step 4), and enable two
throwaway homes against it. Neither the live venv nor a live profile is touched:

```bash
T=~/mn-pilot                      # any scratch dir; the homes' names become their bank names
uv venv --python ~/.hermes/hermes-agent/venv/bin/python "$T/venv"   # same Python minor as Hermes (3.11 here)
uv pip install --python "$T/venv/bin/python" 'mnemosyne-hermes==0.7.1' 'mnemosyne-memory[embeddings]==3.15.1'
"$T/venv/bin/python" scripts/apply_patch_c.py --site "$T/venv/lib/python3.11/site-packages"
for h in pilota pilotb; do
  mkdir -p "$T/homes/$h" && printf 'memory:\n  memory_enabled: true\n' > "$T/homes/$h/config.yaml"
  MNEMOSYNE_VENV="$T/venv" MNEMOSYNE_OPS_RECORDS="$T/records" ~/.hermes/hermes-agent/venv/bin/python \
      scripts/enable_profile.py --home "$T/homes/$h" --identity "$h" --owner-confirmed
done
~/.hermes/hermes-agent/venv/bin/python scripts/verify_tools_config.py --home "$T/homes/pilota" --disposable
~/.hermes/hermes-agent/venv/bin/python scripts/verify_multiplex_isolation.py \
    --home-a "$T/homes/pilota" --home-b "$T/homes/pilotb" --disposable
~/.hermes/hermes-agent/venv/bin/python scripts/mnemosyne_health.py --home "$T/homes/pilota"
```

- **`verify_tools_config.py`** (`--home` is required) rewrites that home's config three times,
  then restores the original bytes in a `finally` block, even if a probe fails. Expected: 6 names
  give exactly those 6 tools, a typo gives a loud `ValueError` rather than a silent fallback to
  all 40, and leaving the key out gives all 40.
- **`verify_multiplex_isolation.py`** runs A→B→A in one process with the process-global
  `HERMES_HOME` pinned to A, the way `hermes serve` multiplexes. It checks that each bank lands in
  its own home, that A recalls its fact with `dense_score > 0` and can't recall B's, and that
  neither home holds a foreign bank. On 0.5.0 without patch D it fails 3 of 9 checks (B's bank
  lands in A), which is the negative control.
- The health check must be HEALTHY on the throwaway homes, except `versions` until the pair is
  added to `TESTED_PAIRS`.

## Step 4 — Carried patches and upgrades

**C — MEMORY.md mirror scope (carried).** `mnemosyne_hermes/__init__.py`, `on_memory_write`:
upstream scopes `MEMORY.md` mirrors to `session`, so a fact evicted from `MEMORY.md` can't be
recalled from any other session. The patch changes it to `scope = "global"` with an
`ATLAS CARRIED PATCH C` marker comment. Upstream #1101 is still open, and 0.7.1 still has the
`session` line. **Re-apply after every `mnemosyne-hermes` upgrade**:

```bash
SITE=~/.hermes/venvs/mnemosyne/lib/python3.11/site-packages
~/.hermes/venvs/mnemosyne/bin/python scripts/apply_patch_c.py --site "$SITE"            # --check: verify only
```

It is idempotent and refuses if the upstream line isn't there exactly once. It then checks every
installed `mnemosyne_hermes` file against the wheel's `RECORD` hashes, so a stale patch (D, after
0.7.1) can't survive unnoticed. Rows mirrored while the patch was missing need rescoping:

```sql
UPDATE working_memory SET scope='global'
 WHERE source LIKE 'builtin_memory_%' AND scope='session' AND (valid_until IS NULL OR valid_until='');
```

**D — multiplex bank root (retired by 0.7.1).** A backport of upstream #958, carried only on
0.5.0. In `initialize`, the profile-isolation branch passes
`db_path=<hermes_home>/mnemosyne/data[/banks/<bank>]/mnemosyne.db` to `Mnemosyne(...)`; without
it, a multiplexed `hermes serve` puts every non-default profile's bank under the default home.
0.7.1 ships #958 itself, so the `patch` check passes there with no patch D. A rollback to 0.5.0
restores it from the venv backup.

**Upgrading `mnemosyne-hermes`.** On stable core, the target is 0.7.1: upstream names
`mnemosyne-memory` 3.15.1 + `mnemosyne-hermes` 0.7.1 as the last audited stable pair. **Don't use
0.7.2.** Its declared floor admits a core that lacks APIs it imports, so it installs cleanly and
then fails when the provider initializes. 0.7.3 and later require beta core `>=4.0.0b3`
(upstream `docs/hermes-integration.md`, read 2026-10-24). Pilot the pair first (Step 3). Then, on the live host: back up the side venv (`cp -a`), upgrade it
in place with the core pinned
(`uv pip install --python ~/.hermes/venvs/mnemosyne/bin/python 'mnemosyne-hermes==<ver>' 'mnemosyne-memory[embeddings]==3.15.1'`),
re-apply patch C, run Step 1 on every profile home, and restart every process that loads the
provider (the per-profile gateways and `hermes serve`). A running process keeps the code it
imported until it restarts. Use plain `uv pip install`, never `mnemosyne-hermes install` or
`upgrade`: those rewrite the wrapper and re-drop the override skill. Roll back by restoring the
venv backup and restarting the same processes.

## Gotchas

- **`mnemosyne_stats.vectors` counts the episodic tier only.** With consolidation off it reads
  0 even though every working row is embedded. Check `memory_embeddings` / `vec_working`
  before you call recall broken.
- **Cron isolation needs both layers.** Hermes ≥ `6f305f3dc1` derives
  `agent_context="cron"` from the platform, so cron turns skip autosave. Background-process
  and watch-pattern notices are injected into the *primary* session as user turns, so no
  context gate can catch them. Only `ignore_patterns` does.
- **Purge by invalidating, not deleting.** `mnemosyne_invalidate` sets `valid_until`, which
  keeps the row recoverable and removes it from recall. Run `mnemosyne backup <dir>` first.
- **Temporal facts go in as triples** or as invalidate-with-replacement. Two loose sentences
  about the same entity rank the older one first.
- **`mnemosyne-hermes upgrade` re-drops the override skill** and can replace the patched
  `__init__.py`. Run Step 1 immediately afterward.
- **Two wrapper formats.** A wrapper written by 0.5.0 assigns `_SITE` in
  `<home>/plugins/mnemosyne/__init__.py`. One written by 0.7.x keeps the venv in
  `mnemosyne-wrapper.json` beside it and refuses a side venv whose Python minor differs from
  Hermes'. The old wrapper loads 0.7.1 unchanged, so an in-place upgrade doesn't need a new
  wrapper. The health check and `enable_profile.py` read both formats.
- **Multiplex isolation.** CLI and per-profile gateways run one profile per process. `hermes serve` (Desktop) runs many. Isolation tests must cover two homes in one process (A→B→A, `verify_multiplex_isolation.py`), or they miss defect D.
- **Host migration.** Move `<home>/mnemosyne/`, `~/.hermes/venvs/mnemosyne/` (or rebuild it
  and re-patch), `<home>/cache/fastembed/`, `<home>/plugins/mnemosyne/`, and the config block.
  Run Step 1 on the new host before trusting it.
