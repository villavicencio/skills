# dv — v0.2.1

Patch release. Fixes a portability bug that broke **`dv:review-claudemd`** outright on any machine
where `ls` is aliased, and corrects the repo's install documentation. No behavior changes to the
other eight skills.

## What's fixed

### `dv:review-claudemd` — survives an aliased `ls`

All four `ls` invocations in the skill's bash are now `command ls`.

The skill's shell is sourced from the user's profile, so a common `alias ls=eza` (or `exa`, `lsd`)
is live **even non-interactively** — and those tools reject BSD/GNU flags. Step 1 died on the first
listing:

```
error: invalid value '/Users/…/0d383462-….jsonl' for '--time <FIELD>'
  [possible values: modified, changed, accessed, created]
```

This was worse than a broken display. The `ls -t` in Step 2 is **load-bearing**: it sorts
transcripts by mtime to identify the live session, which the skill then excludes to avoid analyzing
its own half-written transcript. Under an alias that line fails silently, so the run would either
mine the in-progress session or drop a real one — a correctness bug in the skill's core guard, not
a cosmetic one.

`command` bypasses aliases and shell functions without hardcoding an absolute path, so the fix
holds on macOS and Linux alike. The reasoning is recorded inline so a future edit doesn't quietly
reintroduce a bare `ls`.

Found by running `dv:review-claudemd` against this repo's own transcripts — the skill surfaced its
own bug.

## Repo documentation (not shipped in the plugin)

- **`AGENTS.md` install procedure corrected.** It still pointed at
  `claude plugin install pickup-handoff@villavicencio-skills` — a plugin retired by the
  consolidation in #16. The repo ships exactly one plugin, `dv`. The two-step update path and the
  fully-qualified-id requirement are now documented alongside it.
- **`HANDOFF.md` is gitignored here** is now recorded under Conventions, so `dv:handoff`'s
  auto-commit being a no-op reads as expected rather than as a failure.

## Versioning

Every skill in the suite shares the plugin version, so all nine skills and `plugin.json` move to
`0.2.1` together. CI enforces this parity across the ten files. Only `dv:review-claudemd` changed
in content; the other eight moved `metadata.version` alone.

## Install / update

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

Both steps are required — the local marketplace clone is not auto-fetched, and the update command
needs the **fully qualified** `dv@villavicencio-skills` (the bare `claude plugin update dv` reports
"not found"). The update applies on the next session restart.

Fresh install:

```bash
claude plugin marketplace add villavicencio/skills
claude plugin install dv@villavicencio-skills
```
