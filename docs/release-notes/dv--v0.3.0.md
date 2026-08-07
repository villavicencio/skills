# dv — v0.3.0

Minor release. Adds a tenth skill, **`dv:vps-health`**, which snapshots the live `openclaw-prod`
runtime in one SSH call and interprets each section against known-good. No behavior changes to the
other nine skills — their version moves to `0.3.0` only because the suite releases at the plugin
grain.

## What's new

### `dv:vps-health` — openclaw-prod runtime snapshot

Restores the VPS health probe that `v0.1.0` dropped from `/pickup`'s Step 2c, as a skill that owns
it properly. Source recovered from git history at
`81d581d^:skills/pickup/references/vps-health-snapshot.md`.

It catches the failure classes nothing else surfaces: cron-delivery errors that silently swallow
output, scheduler crashes, gateway restarts, feed staleness, and sustained SSH brute-force pressure.
One SSH call, ten sections, an interpretation table with concrete thresholds, and an explicit
failure mode — if SSH fails it says so and stops rather than retrying or blocking.

Four design decisions worth recording, since the tracking issue left them open:

- **Host-specific, not parameterized.** The recovered probe describes exactly one deployment.
  A generic version would be an *invented* abstraction rather than a derived one. Easy to generalize
  when a second host actually exists.
- **A skill inside `dv`, not its own plugin.** The original intent was an independent version cycle,
  but the repo has since consolidated to a single plugin. Matching current architecture beats
  honoring superseded intent.
- **User-invoked only.** Auto-firing from `/pickup` is exactly what got Step 2c removed in the first
  place.
- **Interpretation stays explicit.** The value is in the specific thresholds — a daily feed over 30h
  *means* a cron silently failed to deliver — and that judgment should not be re-derived per session.

**Read-only.** Every command inspects; none mutate. The restart commands in the interpretation table
are for the operator to run deliberately, not for the agent to fire.

## Three bugs found by running it before shipping it

The probe was run against the live host before merge. It found two defects **in itself**, both
inherited verbatim from the recovered reference, and both defeating the purpose of the check they
belonged to.

### The cron check could not see a dead cron

It filtered to jobs whose `last_run_at` fell *inside* a 24h window and skipped jobs that had never
run. So a job that fails and then stops running entirely — the precise silent-failure class the
section exists to catch — ages out of the window and reports as healthy.

Not hypothetical. The first run printed `(no cron failures in past 24h)` while a Friday bill-pay
checklist had been failing for **161 hours** with `status=error`. A week of a finance job silently
not running, reported as clean.

Now age-independent, with an `age=` column so "failing" is distinguishable from "stopped running",
and `NEVER RUN` jobs surfaced explicitly — which immediately caught a quarterly job that has never
fired.

### The Axiom check used the wrong user and the wrong socket

`axiom-tmux.service` runs as `User=node` on the **named** socket `-L axiom`, despite the service
name. The probe ran `sudo -u axiom tmux ls` — uid 1001, *default* socket — so it could only ever
return `error connecting to /tmp/tmux-1001/default`, and it created that stray directory as a side
effect. Axiom was healthy the whole time. A permanent false alarm.

The interpretation table also gained a case it was missing: the unit is `Type=forking`, so it can
report `active` after the session dies. An active service with an empty session list is still a
failure.

### The recovered probe would have crashed on Python < 3.12

The cron-failure reporter used an f-string with nested double quotes — `f"{j["id"]...}"` — which is
a `SyntaxError` before Python 3.12 (PEP 701 relaxed same-quote nesting only in 3.12), and the host
runs 3.11. Single quotes are unavailable inside the SSH quoting, so the values are hoisted to locals
instead. Caught by parsing the extracted block, before the first live run.

## Repo-level changes (not shipped in the plugin)

The eval harness under `tooling/` is repo infrastructure, not plugin content, so none of this
reaches installed skills. Recorded here because it landed in the same cycle.

- **`must_match_any` was implemented as must-match-ALL.** Two of the three `cite` output-eval cases
  were effectively unpassable — each listed five alternative decline phrasings, and a response had
  to contain all five. It never fired because the paid behavioral job is unfunded and `--dry-run`
  returns before the assertion code is reached.
- **The assertion logic now has tests, gated on every push and PR.** The bug survived for exactly one
  reason: nothing ever executed that function. The new suites are stdlib-only and framework-free,
  which is what lets them run on every push rather than at release cadence behind an API key.
- **Trigger-harness hardening.** Unparseable model responses were scored as `none`, silently
  inflating no-trigger pass rates; retry now delegates to the SDK, whose backoff honors `Retry-After`
  where the hand-rolled loop ignored it; and trigger rates divide by *parseable* samples rather than
  every run, so an unreadable sample no longer drags a query toward passing.
- **The Linux install-failure diagnosis was wrong.** It blamed old git, but git 2.55.0 rejects the
  same invocation with the same error — no git accepts `-o` as a top-level flag, so a version
  difference cannot explain macOS working and Linux failing. Framing corrected; root cause still
  unconfirmed.

## Upgrading

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The marketplace clone is never auto-fetched, so the two-step order matters. An update applies on the
next session restart. Plugin installs are per-machine — every other install needs the same two
commands run there.
