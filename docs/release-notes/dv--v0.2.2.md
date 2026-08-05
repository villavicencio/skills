# dv — v0.2.2

Patch release. Records the first live-run findings for **`dv:gauntlet`** — a stdout-parsing hazard
in the Codex engine that could corrupt the skill's fingerprint ledger, plus a re-verification of the
cheap-verifier model default. No behavior changes to the other eight skills.

## What's fixed

### `dv:gauntlet` — deduplicate Codex findings before counting them

`dv:gauntlet` shipped in 0.2.0 with its native-review stdout parse pinned to the codex-cli contract
but never exercised against a live run. The first real invocation surfaced a formatting property the
schema does not describe.

**codex-cli 0.144.1 emits the summary line and the entire `Full review comments:` block twice,
verbatim,** at the end of stdout — in both `codex exec review` and steered `codex exec` runs. It was
reproduced across three separate calls this session (S1 FIND, S5 CLOSURE, S6 FINAL), so it is a
stable property of the CLI, not a transient glitch.

A naive parse therefore reads every finding twice. That is not merely cosmetic for this skill:

- **Severity counts inflate**, which can push a P2 tail over a threshold that opens the S7 extension
  gate and buys a paid flagship round the change never warranted.
- **The fingerprint ledger corrupts.** The ledger's whole job is to distinguish a *fingerprint-new*
  finding from a re-raise, since a re-raised `refuted` fingerprint is a standoff trigger and a
  re-raised `fixed` one is a closure failure. An echo that arrives looking like a second finding
  makes the loop reason about a debate that never happened.

Step 2's normalization boundary now says to parse the findings block once and dedupe by fingerprint
rather than trusting the block to appear a single time.

### `dv:gauntlet` — verifier staleness note re-verified

The cheap-tier default `gpt-5.6-luna` was re-smoke-tested on 2026-08-05 against codex-cli 0.144.1
under ChatGPT-account auth and still resolves. The note's date moved accordingly; the ids and the
never-treat-these-as-load-bearing warning are unchanged.

## Documentation

- **`README.md` — the migration recipe names its destination.** "Set aside any standalone skill that
  moved into the suite" previously said nothing about *where*, which is how the former `verify-cite`
  ended up parked unversioned under `~/.claude`, where the rollback window it was meant to provide
  never actually existed. The section now branches on `ls -ld`: a real directory moves into a
  dotfiles checkout behind a `git rev-parse` guard (so the chain no-ops rather than creating an
  untracked orphan when the path isn't a repo) and is committed, not merely staged; a symlink is
  retired at its source in three parts — live link, installer declaration, tracked source — since
  moving the link alone leaves the source to recreate the duplicate on the next bootstrap.
- **`docs/release-notes/dv--v0.2.0.md`** carried the bare `claude plugin update dv`, which reports
  "not found". Corrected to the fully-qualified target plus the marketplace refresh, with an inline
  note that the correction is post-publication.

All four documentation findings above were surfaced by running `dv:gauntlet` on the change itself.

## Version parity

Every skill in the suite shares the plugin version, so all nine skills and `plugin.json` move to
`0.2.2` together. CI enforces this parity across the ten files. The eight non-gauntlet skills are
otherwise unchanged in behavior — only their `metadata.version` moved.

## Install / update

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The update target must be **fully qualified** — bare `claude plugin update dv` reports "not found" —
and the marketplace clone is not auto-fetched, so the refresh has to come first. A plugin update
applies on the next session restart.

Fresh install:

```bash
claude plugin marketplace add villavicencio/skills
claude plugin install dv@villavicencio-skills
```
