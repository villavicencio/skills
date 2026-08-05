# dv — v0.2.0

Adds the ninth skill, **`dv:gauntlet`** — a staged, cost-tiered adversarial code-review loop —
and bumps the whole `dv` suite from `0.1.0` to `0.2.0` (one suite, one version).

## What's new

### `dv:gauntlet` — staged adversarial code-review loop

Packages the house "run the Claude↔Codex adversarial review until it approves, then present"
practice — until now folklore living only in per-project harness memory — as a public, reusable
skill. The loop is upgraded from *resummon-the-flagship-until-approve* to a **staged, cost-tiered
pipeline** so an autonomous review loop is actually sustainable on a metered plan:

```
S1 FIND     flagship reviewer, one full adversarial pass          [flagship · paid]
S2 REFUTE   Claude validators, 3 questions, conservative-reject   [host-side]
S3 FIX      one batched fix pass, theme-audit sweeps, one commit  [host-side]
S4 GATES    local checks (test/lint/typecheck) + gate:<command>   [free]
S5 CLOSURE  cheap verifier: fixes closed? + regression look       [cheap · paid]
S6 FINAL    flagship reviewer, native review over cumulative diff [flagship · paid]
S7 EXTEND?  only on a fingerprint-new P0/P1 → one more leg; else terminal
```

The flagship judges exactly twice (first + final); a cheap tier handles the repetitive closure
checks; fixes are batched into one commit per round; free local gates catch regressions between
paid rounds. Default budget is **4** model-review rounds, hard ceiling **10**, and extensions are
granted *only* for a fingerprint-new P0/P1 with concrete evidence — so the loop converges instead
of burning credits rediscovering the same finding.

**Behavior:**

- **Bare `dv:gauntlet` is the full autonomous loop** — it finds, refutes, fixes, and **commits**
  on your current feature branch across the budgeted rounds, and comes back only at the terminal.
  Invoking the skill is the authorization for that.
- **`report`** runs a single FIND + REFUTE round, report-only — tree untouched, no commits, ending
  with the would-be fix plan.
- **Refuses to run on the default branch** in loop mode (branch first) — never pushes, never merges,
  never widens scope to force an approval.
- **No external dependency required.** With the Codex CLI present it runs genuine cross-provider
  find→refute (native `codex exec review --base`); without it, self-contained Claude subagents fill
  every role under the identical contract.

**Cost discipline built in:** role-based model routing (`reviewer` for the two flagship passes,
a cheap `verifier` for closure), a **fingerprint ledger** that turns a re-raised refuted/deferred
finding into a `standoff` instead of a new round, **slim-context re-reviews** (never re-feed the
accumulated debate), and codified stop rules — including `standoff` as a first-class terminal for
when `approve` is only reachable by scope-creep.

**Args:** `report` · `base:<ref>` · `rounds:<n>` · `gate:<command>` · `reviewer:<model>` ·
`verifier:<model>` · free-text review focus.

It ships with `references/` prompts (adversarial FIND persona, 3-question REFUTE validator, cheap
closure verifier, and the codified stop rules) and an `evals/triggers.json` fixture for the
behavioral eval harness.

## Where it sits among the siblings

`dv:critique` stress-tests a **plan, pre-code**; `dv:gauntlet` drives a **diff, post-change** to
convergence. The pair now covers both ends of the change lifecycle. `dv:gauntlet` is deliberately
*not* a plain one-shot PR review (that's the builtin `/review`), *not* `ce-code-review`'s breadth
(persona roster, standards discovery), and *not* a security-only audit — it is one adversarial lens
driven to a verdict, cheaply.

## Versioning

Every skill in the suite shares the plugin version, so all nine skills and `plugin.json` move to
`0.2.0` together. CI enforces this parity across the ten files. The existing eight skills are
otherwise unchanged in behavior — only their `metadata.version` moved.

## Install / update

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The update target must be fully qualified — bare `claude plugin update dv` reports "not found" —
and the marketplace clone is not auto-fetched, so it needs the refresh first. (Corrected after
publication; the note originally carried the bare form, which does not work.)

Fresh install:

```bash
claude plugin marketplace add villavicencio/skills
claude plugin install dv@villavicencio-skills
```

## Notes & known limitations

- **Model ids rot.** The reviewer role inherits the Codex CLI's configured default (no `-m`); the
  cheap `verifier` default is a *documented, overridable* id carrying a dated staleness note. As of
  2026-07-24 (codex-cli 0.144.1, ChatGPT-account auth) the resolvable cheap tier is `gpt-5.6-luna`
  and the mid tier is `gpt-5.6-terra`; smoke-test before relying on either, and use
  `verifier:<model>` to override.
- **Codex review runs routinely exceed the 600s Bash cap** — the skill detaches them
  (`run_in_background`) and collects on completion.
- **Not a CI job in v1.** A key-gated CI variant (mirroring the behavioral eval harness) is a
  natural v2.
