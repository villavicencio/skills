---
name: mnemosyne-ops
description: "Enable, health-check, and maintain the Mnemosyne memory provider on a Hermes profile without disturbing anything else in it. Gated enable (before/after integrity hashes, memory-block-only config splice, provider smoke through Hermes' own loader), a read-only health check for the known drift classes (carried patch lost on upgrade, installer override skill reappearing, injected system turns leaking into the store), and a tools-subset verifier. Use when turning Mnemosyne on for a profile, after any mnemosyne-hermes or Hermes upgrade, when recall seems polluted or empty, or before migrating Hermes to another host."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.4.0"
---

# /mnemosyne-ops — Mnemosyne on Hermes, operated safely

Mnemosyne is a local, SQLite-backed external memory provider for Hermes: it autosaves user
turns, embeds them (fastembed / bge-small, no LLM), and prefetches relevant ones into each new
turn. It **augments** `MEMORY.md` / `USER.md`, the Obsidian vault, and session search. It never
replaces them. Origin and evidence: VIL-143 (`~/Projects/mnemosyne-pilot/DECISION.md` on the
VPS).

**Host-specific by design.** Assumes the side-venv install at
`~/.hermes/venvs/mnemosyne` (python3.11) with the wrapper plugin at
`<home>/plugins/mnemosyne`, pinned to `mnemosyne-memory==3.15.1` and
`mnemosyne-hermes==0.5.0`.

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
| `patch` | a carried patch was lost on upgrade: C (MEMORY.md mirrors become session-only) or D (non-default profiles' banks land in the default home under `hermes serve`) | re-apply (Step 4) |
| `isolation` | another profile's bank is living under this home: the multiplex leak | apply patch D, restart `hermes serve`, and move the bank (export, then import into its owner's home) |
| `override` | installer re-dropped `mnemosyne-memory-override`, which tells the agent MEMORY.md is deprecated | delete `<home>/skills/memory/mnemosyne-memory-override` |
| `leak` | injected system turns stored in the last 7 days | widen `ignore_patterns`; invalidate the rows |
| `freshness` | autosave silent > 48h | check `hermes memory status`, the gateway log |
| `versions` | unpinned upgrade | re-verify everything below before accepting |

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
to its owner.

New sessions pick the provider up. A session that was already running keeps the toolset it
started with.

## Step 3 — Verify the tools knob (after any upgrade)

```bash
~/.hermes/hermes-agent/venv/bin/python scripts/verify_tools_config.py --home <pilot-home>   # add --disposable for a throwaway home
```

Run this against a disposable or pilot home. The verifier rewrites that home's config three
times, then restores the original bytes in a `finally` block (even if a probe fails), and exits non-zero if any check fails. Expected results: 6 names produce exactly those 6 tools; a typo
produces a loud `ValueError` rather than a silent fallback to all 40; leaving the key out
produces all 40.

## Step 4 — The carried patches

**D — multiplex bank root.** This is a backport of upstream #958, which ships in mnemosyne-hermes ≥ 0.7.1 but needs beta core 4.0.0b3. In `initialize`, the profile-isolation branch passes `db_path=<hermes_home>/mnemosyne/data[/banks/<bank>]/mnemosyne.db` to `Mnemosyne(...)`. Without it, a multiplexed `hermes serve` puts every non-default profile's bank under the default home. Drop the patch once you're on a stable release that includes #958. Restart `hermes serve` after applying it.

**C — MEMORY.md mirror scope.**

`mnemosyne_hermes/__init__.py`, `on_memory_write`: upstream scopes `MEMORY.md` mirrors to
`session`, so a fact evicted from `MEMORY.md` can't be recalled from any other session. The
patch changes it to `scope = "global"` and adds an `ATLAS CARRIED PATCH` marker comment, which
the health check looks for. **Re-apply after every `mnemosyne-hermes` upgrade.** Then rescope
the existing rows:

```sql
UPDATE working_memory SET scope='global'
 WHERE source LIKE 'builtin_memory_%' AND scope='session' AND (valid_until IS NULL OR valid_until='');
```

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
- **Multiplex isolation.** CLI and per-profile gateways run one profile per process. `hermes serve` (Desktop) runs many. Isolation tests must cover two homes in one process (A→B→A), or they miss defect D.
- **Host migration.** Move `<home>/mnemosyne/`, `~/.hermes/venvs/mnemosyne/` (or rebuild it
  and re-patch), `<home>/cache/fastembed/`, `<home>/plugins/mnemosyne/`, and the config block.
  Run Step 1 on the new host before trusting it.
