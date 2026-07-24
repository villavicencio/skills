# Behavioral evals for `dv` skills

The CI `validate` job proves a skill is well-*formed* (frontmatter, version
parity). It says nothing about whether the skill *works*: does it fire when it
should, and does loading it actually change the agent's behavior in the right
direction? This directory adds that second layer.

Two harnesses, both following Anthropic's [Agent Skills](https://agentskills.io)
eval methodology:

| Harness | Question it answers | Fixture |
| --- | --- | --- |
| `run_trigger_evals.py` | Does the skill get *selected* when it should (and not when it shouldn't)? | `skills/<skill>/evals/triggers.json` |
| `run_output_evals.py` | Does loading the skill *change behavior* in the intended direction vs. a no-skill baseline? | `skills/<skill>/evals/evals.json` |

Fixtures live **next to the skill** (`plugins/dv/skills/<skill>/evals/`) so each
skill is self-describing; the runners are shared and live here. The
`agentskills` validator ignores the extra `evals/` subdir, so co-locating is
safe.

The runners are self-contained [PEP 723](https://peps.python.org/pep-0723/)
scripts — dependencies are declared inline and resolved by `uv run`. No project
virtualenv to manage.

## Running

```bash
# one-off, no API key needed — proves catalog/fixture parsing works
./run_trigger_evals.py cite --dry-run
./run_output_evals.py  cite --dry-run

# real run
export ANTHROPIC_API_KEY=sk-...
./run_trigger_evals.py cite            # human-readable summary
./run_trigger_evals.py cite --json     # machine-readable, for CI
./run_output_evals.py  cite
```

If you don't have `uv`, run under any Python ≥3.11 with the deps installed:
`pip install 'anthropic>=0.40' pyyaml && python run_trigger_evals.py cite`.

Both runners exit non-zero if any case fails, so they gate cleanly.

## Trigger evals — methodology

`triggers.json` holds ~10 should-trigger and ~10 should-not-trigger queries,
each tagged `train` or `val` (~60/40). The runner:

1. Renders every `dv` skill's `(name, description)` into an `<available_skills>`
   catalog (the same shape the agent sees).
2. For each query, asks the model which single skill applies — **N times**
   (default 3), because selection is stochastic.
3. Computes `trigger_rate = selections / N`.
4. A **should-trigger** query passes if `rate > threshold` (default 0.5); a
   **should-not-trigger** query passes if `rate < threshold`.

It reports `train` and `val` pass rates separately. The discipline:

- **Tune the description using `train` failures only.** Broaden it if
  should-trigger queries miss; add specificity if false-triggers occur.
- **Select the best description iteration by the `val` pass rate.** Holding out
  `val` is what stops you from overfitting the description to the exact wording
  of the queries you happened to write.
- **Don't paste failed-query keywords into the description.** That games the
  eval without improving real-world triggering.

The selector is a *proxy* for Claude Code's real skill picker — a forced single
choice against the catalog, not a live multi-tool loop. It still catches the two
failures that matter: should-fire-but-doesn't (the confabulation risk for
`cite`) and shouldn't-fire-but-does (catalog collision with the other skills).
The no-trigger set deliberately includes queries that belong to *other* dv
skills (reddit, twitter, handoff, tmux, critique) so collisions surface.

## Output evals — methodology

`evals.json` holds cases that each run twice: **with** the `SKILL.md` body
injected as the system prompt, and **without** (a neutral baseline). Assertions
are applied to the with-skill response and are strictly **code-checkable**
(regex match / non-match) — never "is it good". The baseline response is
captured so you can confirm the skill is actually doing work.

For `cite`, cases run with **no fetch tool**, which forces the exact
decline-vs-confabulate decision the skill governs and needs no network (so it's
deterministic and CI-safe):

- a realtime query → with-skill must **decline** and must not emit a remembered
  dollar figure; baseline typically confabulates one.
- a non-realtime control query → loading `cite` must **not** make the agent
  refuse a general-knowledge question (the over-firing guard).

## Adding evals for another skill

1. Create `plugins/dv/skills/<skill>/evals/triggers.json` (copy `cite`'s as a
   template). Aim for 8–10 should-trigger and 8–10 should-not-trigger queries
   with varied phrasing; tag ~60% `train`, ~40% `val`. Put realistic queries
   that belong to *other* skills in the no-trigger set to test collisions.
2. Optionally add `evals.json` with 2–3 output cases and regex assertions that
   express the behavior the skill is supposed to produce.
3. Run both with `--dry-run` to sanity-check parsing, then for real with a key.
4. CI picks them up automatically (see below) — no workflow edit needed.

## CI

The `behavioral-evals` job in `.github/workflows/validate.yml` runs these on
push/PR **only when an `ANTHROPIC_API_KEY` repo secret is present**. Without the
secret the job's steps skip cleanly, so forks and key-less runs stay green. The
always-on `validate` job (structure + version parity) remains the hard gate; the
behavioral layer is an additional gate wherever a key is configured.
