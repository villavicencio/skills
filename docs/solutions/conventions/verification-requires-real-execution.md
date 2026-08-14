---
title: Verification requires executing the code in its real environment
date: 2026-08-13
category: conventions
module: "verification pipeline (tooling/evals, plugins/dv/skills, .github/workflows)"
problem_type: convention
component: development_workflow
severity: high
applies_when:
  - "Declaring work verified on the strength of a static parse, structural validation, green CI, or careful reading"
  - "Changing a code path that nothing actually executes -- dry-run short-circuits, skipped jobs, deliberately unfunded steps"
  - "Writing a probe, query, or script that targets a live host or service it has never been run against"
  - "Claiming a script imports or runs with no dependencies installed, without a clean-environment run"
  - "A local run passes while CI fails (or the reverse) because the two environments have different packages installed"
  - "Asserting a causal diagnosis -- why something fails, which version tolerates what -- that nobody has reproduced"
related_components: [testing_framework, tooling]
tags: [verification, ci, evals, dry-run, execution-environment, false-green, dependency-isolation, pre-merge-testing]
---

# Verification requires execution: structural validation and green CI prove shape, not behavior

## Context

Five defects in this repo shipped, or nearly shipped, past every check that did not actually run the code in its real environment.

The eval harness at `tooling/evals/` is the clearest case. `check_assertions` in `tooling/evals/run_output_evals.py` implemented a field named `must_match_any` as must-match-*all* — the loop failed the case on the first non-matching pattern, contradicting the field name, its own failure message, and its inline comment. The live effect was that `plugins/dv/skills/cite/evals/evals.json` had two unpassable cases: `realtime-price-no-tool` lists five alternative decline phrasings (`plugins/dv/skills/cite/evals/evals.json:17-23`) and `realtime-version-no-tool` lists five more (`:37-43`), so a response had to contain all five phrasings at once to pass.

Nothing caught it, because nothing ran it. Two independent paths lead away from that function:

- `--dry-run` prints the plan and returns at `tooling/evals/run_output_evals.py:137`, well before the only call site at `:154`.
- The real path requires an API key (`:139-141`), and the paid `behavioral-evals` job in `.github/workflows/validate.yml:171` is doubly gated — on release tags or manual dispatch (`:172`) and on `ANTHROPIC_API_KEY` being non-empty (`:184`, `:189`). That key is deliberately absent: the behavioral suite makes roughly 540 live calls per run at about $1.50-2.00, and the standing decision is not to fund it (auto memory [claude], `behavioral-evals-deliberately-unfunded`; also documented in the job's own comment block at `.github/workflows/validate.yml:155-170`).

CI was green the entire time. It was validating structure — per-skill spec validation via `agentskills`, per-plugin version parity, plugin.json parity — and those checks passed because they were true. The function's logic was correct-by-inspection only, and inspection missed it. Fixed in PR #23.

The same shape appeared again. `plugins/dv/skills/vps-health/SKILL.md` (added in PR #30) passed a static Python parse of its embedded probe script, `agentskills` structural validation, green CI, and careful reading — and PR #30's own description says so plainly, flagging under "Not verified" that the probe had not been run against `openclaw-prod` and that "a live run should happen before this skill is trusted." The first live run found two defects, both of which defeated the exact purpose of the checks they belonged to. And in PR #27, a module-scope `import yaml` in `tooling/evals/run_trigger_evals.py` passed locally on a machine that happens to have pyyaml installed, then failed on a clean CI runner that does not.

Notably, static analysis was not useless here — the static parse of the vps-health probe caught a real defect the recovered source carried: an f-string with nested double quotes, which is a `SyntaxError` on Python < 3.12 and would have killed the whole cron section on the Debian bookworm host (PR #30). That is the correct division of labor. Static checks find the class of defect that is visible without state; only execution finds the rest.

### The pattern predates all of this — and repeated anyway

The earliest instance is a release older than the eval-harness work, and it is the reason this document exists rather than a fourth release note. `dv:gauntlet` shipped in dv 0.2.0 with its Codex stdout parse written against the codex-cli contract, reviewed, and never executed against a live Codex run. Its first real invocation found that codex-cli 0.144.1 emits the summary line and the entire `Full review comments:` block **twice, verbatim** — two findings read as four. It reproduced across all three paid calls in that run, so it was a stable property of the CLI, not a fluke (session history; documented in `docs/release-notes/dv--v0.2.2.md:12-18`).

That was not cosmetic. Doubled findings inflate severity counts, which can push a P2 tail across the threshold that opens a paid extension round, and they corrupt the fingerprint ledger whose entire job is to distinguish a new finding from a re-raise. The fix was a dedupe rule at the normalization boundary in `plugins/dv/skills/gauntlet/SKILL.md`, shipped as 0.2.2.

**The important part is what happened next: the same class of defect shipped again one minor version later, in `vps-health`.** A narrative postmortem in a release note did not prevent recurrence, because a release note is a story about the past, not a rule applied to the next change. That gap is what this convention is for.

Two further findings from that same run sharpen the rule (session history):

- A `bash -n` syntax gate passed on the round-1 fix, which nonetheless shipped two real defects: `git add` that stages but never commits (so the "version controlled" promise is unfulfilled), and `-A` on a pathspec that sweeps in unrelated pending edits. Syntax validity cannot see either.
- The reviewer found a README path that read perfectly and did not exist, only because it ran `git -C ~/dotfiles status` and got nothing — the real checkout is `~/Projects/Personal/dotfiles`. Following the prose would have silently manufactured the exact untracked-orphan outcome the paragraph existed to prevent.

### The claim itself has to be run, not just the code

Issue #8 is the non-code variant. Both the issue and the README asserted a root cause for a Linux install failure — old git rejects the CLI's malformed clone invocation, while "Mac's git (likely Homebrew 2.50+) appears to tolerate it." Nobody ran it. PR #29 falsified it in one command: git 2.55.0 on macOS rejects the identical invocation with the identical `unknown option: -o`, proving no git accepts `-o` as a top-level flag and that a version difference cannot explain the platform split.

A diagnosis survived roughly two and a half months of careful reading and died to a single execution. Prose describing behavior is subject to the same rule as code implementing it.

## Guidance

**1. Name the two layers, and never let one stand in for the other.**

- *Structural validation* proves shape: the file parses, the frontmatter has required keys, versions agree across a plugin, the script compiles. Cheap, fast, safe to run on every push.
- *Behavioral validation* proves it works: the function was called with real inputs and produced the right output, or the script ran against the real host and returned the truth.

A green pipeline made entirely of the first layer is not evidence of the second. Before trusting green, ask which layer is green — and specifically, name the code paths that were *executed* by the run. In this repo, the answer for `check_assertions` was "none."

**2. Trace whether a code path is reachable in CI at all — an early return or a skipped gate makes a function permanently untested.**

Both escape routes here were ordinary and invisible in review: a `--dry-run` early return, and a job gate on a secret that is intentionally never set. Neither shows up as a failure; both show up as green. When a function has no reachable execution path in CI, treat it as unverified code regardless of how many times it has been read.

**3. Prove a test in both directions before believing it.**

A test that cannot fail against the broken version is not a test. Both new suites were proven against the pre-fix implementation:

- `tooling/evals/test_assertions.py` passes at HEAD and produces 11 failing checks against the pre-fix `run_output_evals.py` at `3f5170f` (PR #27; re-verified for this document by running the current test file against the pre-fix harness — exit 1, 11 checks).
- `tooling/evals/test_trigger_parsing.py` covers the trigger-harness defects hardened in PR #27 the same way.

This is cheap to do and it is the only thing that distinguishes a regression test from a test-shaped comment.

**4. Make the test suite dependency-free when you want it always-on.**

Both suites are stdlib-only and framework-free, and that is a deliberate design choice with a specific payoff — no install step means the CI step can run on every push and PR for free rather than sitting behind the funded, tag-cadence gate. `tooling/evals/test_assertions.py:1-17` states the reasoning: this repo has no pytest, no pyproject, and no test convention, so a bare script was chosen precisely so it needs no install.

The constraint propagates to the code under test. `tooling/evals/test_trigger_parsing.py:8-15` spells out the three things that keep `run_trigger_evals.py` importable with nothing installed: `import anthropic` inside `main()` (`run_trigger_evals.py:255`), `import yaml` inside `parse_frontmatter()` (`:78`), and `_retryable` classifying by exception *name* rather than `isinstance` against anthropic's types. If you want always-on tests, the import surface of the module under test is part of the contract.

**5. Verify in an environment that matches the one that runs it.**

The local machine has pyyaml, the CI test step installs nothing, and a docstring claimed "importable with nothing installed" without anyone having tested that in a clean environment. The fix (PR #27) was verified in a venv with neither pyyaml nor anthropic installed — the check that should have preceded the original claim.

The recurrence guard chosen was structural, not a new assertion: the always-on test step imports both harness modules and installs nothing before doing so, so any future module-scope third-party import fails CI the same way. Prefer a structural guard over an assertion when the environment itself can enforce the property.

**6. For code that talks to a live system, execution against that system is the only verification that counts — and it belongs before merge.**

Reading a probe script tells you what it says, not what the host will answer. Both vps-health defects were of a kind no amount of reading finds: they depend on the shape of real data (a cron job whose last run is 161 hours old) and on real service configuration (which user and which tmux socket the unit actually uses). PR #30 shipped honest about this — the probe was merged with a live run explicitly named as the outstanding item — and the live run happened before merge, producing the fix commit that corrected both.

**7. Distrust a check that reports "nothing to report."**

The vps-health cron section printed `(no cron failures in past 24h)` while a job had been erroring for 161 hours. A silent, healthy-looking output from a check is the highest-risk state in a monitoring tool, because it is indistinguishable from a working check. The corrected SKILL.md now encodes this as a reading rule: "Treat each section independently. Empty sections are load-bearing — never skip past one silently. A section that produced no output is a finding, not an absence of one." (`plugins/dv/skills/vps-health/SKILL.md:101-102`)

**8. A verification artifact is not evidence the verification ran.**

During the 0.2.0-era gauntlet run, the REFUTE stage executed in-context rather than as the specified fresh-context subagents, because the then-current global instructions forbade unsolicited agent spawning. The report still came out correctly shaped — labeled sections, per-finding verdicts, a convergence table — with none of the independence it claimed, and the degradation had to be disclosed in prose because nothing in the artifact revealed it (session history; the episode drove the global `## Subagents` carve-out in dotfiles PR #125).

Check that the stage ran as specified, not that its output looks right. This applies to your own tooling most of all: a review pipeline that reports a clean convergence table is making a claim about a process you cannot see.

## Why This Matters

The failure mode is not "we forgot to test." It is that every available signal said the code was fine. Structural validation passed, CI was green, the function had been read by multiple reviewers, and the field name, docstring, and failure message all *described* the correct behavior. The only thing missing was a single execution with real inputs.

That combination is what makes this class of defect long-lived. A red build gets fixed the same day. A green build over unexecuted code can persist indefinitely — the `must_match_any` bug survived from PR #17 (the harness's introduction) through PR #23, and while it survived, the `cite` eval fixture was silently unpassable. Had the behavioral job ever been funded and run, it would have reported failures for a skill that was working correctly. An unexecuted verification tool is worse than no tool: it produces confidence with no information, and when it finally runs it reports noise.

The cost asymmetry favors execution heavily. Running `python3 tooling/evals/test_assertions.py` takes under a second and needs nothing installed. Running the vps-health probe once against the real host takes one SSH round-trip. Against that: a monitoring skill that reports "all clear" while a bill-pay job silently fails for a week, and creates a stray `/tmp/tmux-1001` on the host as a side effect of the wrong check.

There is also a discipline point about claims. The docstring asserting "importable with nothing installed" was written before anyone tried it in a clean environment, and it was wrong. A claim about behavior in an environment you have not entered is a guess wearing the grammar of a fact. Either run it there or phrase it as an intention.

## When to Apply

- **Before trusting a green CI run on a change to logic**, ask which of the change's code paths CI actually executed. If the honest answer is "none," you have structural validation, not verification.
- **When any test-execution path is gated** — on a secret, a paid API, a tag cadence, a `--dry-run` flag, an opt-in environment variable — treat everything downstream of that gate as unverified code, and add an ungated path that exercises the pure logic.
- **When writing a regression test for a bug you just fixed**, before you consider it done: run it against the pre-fix code and confirm it fails.
- **When adding any script that talks to a live system** — a health probe, a migration, a deploy hook, a monitoring query — run it against the real system before merge, not after.
- **When a check reports a clean result on its first run**, verify it can report a dirty one. Confirm it against a case you know is broken.
- **When claiming a property of a different environment** ("runs with no dependencies," "works on the CI runner," "compatible with Python 3.11"), reproduce that environment and check, or downgrade the claim.
- **When asserting a causal diagnosis** — why a command fails, which version tolerates what, which platform differs — reproduce it before writing it down. Issue #8's root-cause section survived months of readers and one execution.
- **When choosing a test framework** for a repo with no existing test convention: consider whether dependency-free tests would let you run them always-on rather than behind an install or funding gate.
- **After shipping a fix for this class of defect**, ask what would prevent the next instance. A release-note postmortem did not stop the same class recurring one minor version later.

## Examples

### Structural gate vs behavioral gate, side by side

Both live in `.github/workflows/validate.yml`. The always-on `validate` job runs `agentskills validate` per skill, two version-parity checks, and this step:

```yaml
- name: Unit-test eval harness logic
  run: |
    set -e
    shopt -s nullglob
    tests=(tooling/evals/test_*.py)
    if [ ${#tests[@]} -eq 0 ]; then
      echo "::error::No tooling/evals/test_*.py found — the harness unit tests have gone missing."
      exit 1
    fi
    for t in "${tests[@]}"; do
      echo "::group::${t}"
      python3 "${t}"
      echo "::endgroup::"
    done
```

(`.github/workflows/validate.yml:140-153`) Three properties earn their keep. It installs nothing, so it is free and always-on — and so it is also the thing that catches a module-scope third-party import. It globs `test_*.py`, so new test files need no workflow edit. And it *errors on an empty glob* rather than passing vacuously, which is the same class of bug as the one that motivated it: a check that quietly reports success when it did no work.

Compare the paid job, gated twice (`.github/workflows/validate.yml:171-189`):

```yaml
behavioral-evals:
  if: startsWith(github.ref, 'refs/tags/') || github.event_name == 'workflow_dispatch'
  ...
  - name: Install uv
    if: ${{ env.ANTHROPIC_API_KEY != '' }}
```

With no key configured, every real step skips and the job reports green. That green means "we did not check."

### The bug that read as correct

Current implementation, `tooling/evals/run_output_evals.py:72-80`:

```python
    failures = []
    pats = spec.get("must_match_any", [])
    # The `pats and` guard is load-bearing, not stylistic: any([]) is False, so
    # dropping it would fail every case that omits the key or lists no
    # alternatives — and the call site passes {} for a case with no with_skill
    # assertions at all.
    if pats and not any(re.search(p, text) for p in pats):
        alts = ", ".join(f"/{p}/" for p in pats)
        failures.append(f"must_match_any unsatisfied: none of {len(pats)} patterns matched: {alts}")
```

The pre-fix version looped and failed on the first non-matching pattern, making a disjunction behave as a conjunction. Two details worth carrying forward:

- **The obvious rewrite regresses three cases.** `any([])` is `False`, so a bare `not any(...)` without the `pats and` guard would flip absent-key, empty-list, and empty-spec cases from pass to fail — including the `{}` the call site at `:154` passes for a case with no `with_skill` assertions. The fix's own edge cases needed tests as much as the bug did, and `tooling/evals/test_assertions.py` covers all three vacuous-pass paths explicitly.
- **The fix changed short-circuit direction.** The old loop stopped at the first *non-matching* pattern; `any()` stops at the first *match*, so an invalid regex sitting after a matching alternative is never compiled at runtime. PR #23 disclosed this rather than papering over it with a `try/except`, and PR #27 covered the consequence directly: the test suite compiles every pattern in every shipped fixture (`tooling/evals/test_assertions.py:163-181`).

### Proving the test in both directions

The claim in PR #27 — "fails with 11 checks against the pre-fix implementation at `3f5170f`" — is reproducible. Copy the pre-fix harness alongside the current test file and the shipped fixture, preserving the `parents[2]` repo-root layout the test resolves against:

```bash
mkdir -p /tmp/prefix/tooling/evals /tmp/prefix/plugins/dv/skills/cite/evals
git show 3f5170f:tooling/evals/run_output_evals.py > /tmp/prefix/tooling/evals/run_output_evals.py
cp tooling/evals/test_assertions.py /tmp/prefix/tooling/evals/
cp plugins/dv/skills/cite/evals/evals.json /tmp/prefix/plugins/dv/skills/cite/evals/
python3 /tmp/prefix/tooling/evals/test_assertions.py    # exit 1: FAILED — 11 check(s)
```

Against HEAD the same file exits 0. Two runs, a few seconds, and the test is now known to be load-bearing rather than assumed to be.

### Live-run findings that reading could not produce

**Before** (inherited verbatim from the recovered probe): the cron-failure query filtered to jobs whose `last_run_at` fell inside a 24h window and skipped jobs that had never run at all, under a section named `HERMES_CRON_FAILURES_24H`. A job that fails and then stops running entirely — precisely the silent-failure class the section exists to catch — ages out of the window and is reported as healthy. On the first live run it printed `(no cron failures in past 24h)` while a Friday bill-pay job had been failing since 2026-07-31, 161 hours earlier, with `status=error` (per PR #30's fix commit).

**After** (`plugins/dv/skills/vps-health/SKILL.md:44-61`), age-independent, with the age surfaced rather than used as a filter:

```python
for j in data.get("jobs", []):
    ...
    if not last_run:
        issues.append(f"  {jname:40s} NEVER RUN")
        continue
    ...
    if last_status != "ok" or deliv_err:
        issues.append(f"  {jname:40s} age={age_h:6.1f}h status={last_status} err={last_err or deliv_err}")
print("\n".join(issues) if issues else "(no cron failures)")
```

The section was renamed to `HERMES_CRON_FAILURES` since it is no longer 24h-scoped, and the interpretation table now instructs the reader to read the `age=` column, because "failing" and "stopped running" are different diagnoses (`plugins/dv/skills/vps-health/SKILL.md:110-111`).

**Before**: `sudo -u axiom tmux ls`. **After** (`plugins/dv/skills/vps-health/SKILL.md:66-70`):

```bash
# axiom-tmux.service runs as User=node on the NAMED socket `-L axiom`, despite
# the service name. Checking `sudo -u axiom tmux ls` inspects uid 1001 on the
# DEFAULT socket, which can only ever error — and creates a stray
# /tmp/tmux-1001 as a side effect. Verified 2026-08-07 against the live unit.
sudo -u node tmux -L axiom ls 2>&1 | head -3
```

The old form could only ever report an error, so it was a permanent false alarm with a filesystem side effect, while Axiom was healthy the whole time. The service name implies the user; the unit file disagrees. No reading of the probe reveals that — only running it does. The live run also surfaced a case the interpretation table had missed entirely: the unit is `Type=forking`, so it can report `active` after its session dies, which is why an active service with an empty session list is now explicitly a failure (`plugins/dv/skills/vps-health/SKILL.md:112`).

### The environment mismatch

**Before**: `import yaml` at module scope in `tooling/evals/run_trigger_evals.py`, with a test docstring asserting the module was importable with nothing installed. Passed locally (this machine has pyyaml); failed on the clean CI runner the moment the always-on test step tried to import it.

**After** (`tooling/evals/run_trigger_evals.py:69-78`):

```python
def parse_frontmatter(skill_md: Path) -> dict:
    """Return the YAML frontmatter of a SKILL.md as a dict.

    yaml is imported here rather than at module scope — same pattern as
    `import anthropic` inside main(). It keeps this module's import surface
    stdlib-only, which is what lets the unit tests import it in CI with
    nothing installed. A top-level import made the always-on test step
    depend on pyyaml being present.
    """
    import yaml
```

Verified in a venv with neither pyyaml nor anthropic installed (PR #27) — the check that should have preceded the original stdlib-only claim. This one is the pleasant case: the always-on gate that the first instance motivated is what caught this one, one PR later. That is the compounding return on making the cheap layer always-on.

## Related

- PR #23 — `must_match_any` is any-of, not all-of; the `pats and` guard and the short-circuit-direction disclosure.
- PR #27 — always-on stdlib-only harness unit tests (`test_assertions.py`, `test_trigger_parsing.py`), the globbed CI step, trigger-harness hardening, and the lazy `import yaml` fix.
- PR #28 — follow-up: delegate retry to the SDK, exclude unparseable samples from rates. Closed issue #26, a scoring defect that sat in `run_trigger_evals.py` across releases for the same reason: no CI path executed the scoring function.
- PR #29 / issue #8 — the falsified Linux install diagnosis; the non-code instance of this rule.
- PR #30 — `dv:vps-health`, including the pre-merge fix commit for the two defects the first live run exposed.
- `docs/release-notes/dv--v0.2.2.md:12-18` — the earliest instance, the codex-cli stdout double-emission found by `dv:gauntlet`'s first live invocation.
- `docs/release-notes/dv--v0.3.0.md:37-73` — the vps-health live-run findings as shipped.
- `docs/plans/2026-07-24-001-feat-gauntlet-skill-plan.md:153` — states the rule ("Confirmation = the feature-specific runtime gate, not green unit tests") while its own acceptance criteria at `:445-446` accept a `--dry-run` and a skipped behavioral job. The tension this convention resolves.
- `tooling/evals/README.md` — eval methodology and the trigger/output split.
- Auto memory [claude], `behavioral-evals-deliberately-unfunded` — why the paid job has no API key. A standing decision, not an oversight; the response to it is an always-on cheap layer, not funding.
