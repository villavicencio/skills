#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "anthropic>=0.40",
#   "pyyaml>=6.0",
# ]
# ///
"""Trigger evals for dv skills.

Measures whether a skill is *selected* from the full dv catalog for a set of
queries — the Anthropic "Agent Skills" trigger-eval pattern:

  * render every skill's (name, description) into an <available_skills> catalog
  * for each query, ask the model which single skill applies (or `none`)
  * run each query N times, trigger_rate = selections / N
  * a should-trigger query passes if rate > threshold; should-not if rate < threshold
  * report train and val splits separately (tune the description on train
    failures; pick the best iteration by val pass rate — do not overfit the
    description to keywords from specific failed queries)

This is a *proxy* for Claude Code's real skill selector: a forced single choice
against the catalog rather than a live multi-tool loop. It still surfaces the
two failures that matter — should-fire-but-doesn't (confabulation risk) and
shouldn't-fire-but-does (catalog collision).

Usage:
  export ANTHROPIC_API_KEY=sk-...
  ./run_trigger_evals.py cite                 # run cite's triggers.json
  ./run_trigger_evals.py cite --runs 5        # 5 samples per query
  ./run_trigger_evals.py cite --json          # machine-readable summary to stdout
  ./run_trigger_evals.py cite --dry-run       # no API calls; print catalog + plan

Exit code is non-zero if any query fails (real runs only), so it can gate CI.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import yaml

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_PLUGIN_ROOT = "plugins/dv"

# A response that is neither a catalog name nor `none`. It is NOT the same as
# `none`, and collapsing the two is a silent scoring error — see parse_choice.
UNPARSEABLE = "__unparseable__"

# Transient-failure retry. A paid run makes hundreds of calls; without this a
# single 429 aborts everything and forfeits the tokens already spent.
MAX_ATTEMPTS = 4
BASE_BACKOFF = 1.5


def log(msg: str) -> None:
    """Diagnostics go to stderr so --json keeps stdout clean."""
    print(msg, file=sys.stderr, flush=True)


def parse_frontmatter(skill_md: Path) -> dict:
    """Return the YAML frontmatter of a SKILL.md as a dict."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{skill_md}: no frontmatter (must start with '---')")
    # split into: '', frontmatter, body
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{skill_md}: unterminated frontmatter")
    data = yaml.safe_load(parts[1]) or {}
    if "name" not in data or "description" not in data:
        raise ValueError(f"{skill_md}: frontmatter missing name/description")
    return data


def load_catalog(plugin_root: Path) -> list[dict]:
    """Every skill in the plugin as {name, description}, sorted by name."""
    catalog = []
    for skill_md in sorted(plugin_root.glob("skills/*/SKILL.md")):
        fm = parse_frontmatter(skill_md)
        catalog.append({"name": fm["name"], "description": fm["description"]})
    if not catalog:
        raise SystemExit(f"No skills found under {plugin_root}/skills/*/SKILL.md")
    return catalog


def render_system_prompt(catalog: list[dict]) -> str:
    """Build the selector system prompt embedding the skill catalog."""
    lines = ["<available_skills>"]
    for s in catalog:
        lines.append(f'  <skill name="{s["name"]}">{s["description"]}</skill>')
    lines.append("</available_skills>")
    catalog_xml = "\n".join(lines)
    return (
        "You are the skill-selection component of an AI coding agent. Below is the "
        "catalog of skills available this session. Given the user's message, decide "
        "which SINGLE skill (if any) should activate to handle it.\n\n"
        f"{catalog_xml}\n\n"
        "Respond with EXACTLY one line containing only the `name` of the single "
        "best-matching skill, or the word `none` if no skill should activate. "
        "No punctuation, no explanation, no other text."
    )


def parse_choice(response_text: str, names: list[str]) -> str:
    """Map a model response onto a catalog name, 'none', or UNPARSEABLE.

    UNPARSEABLE is deliberately distinct from 'none'. Collapsing them scores a
    refusal, a truncated completion, or a response-format change as a
    legitimate "correctly did not trigger" — which silently inflates the
    no_trigger pass rate and hides the fact that the harness's contract with
    the model has broken.
    """
    text = response_text.strip().lower()
    # Prefer a whole-word match against a known skill name.
    for name in names:
        if re.search(rf"\b{re.escape(name.lower())}\b", text):
            return name
    if re.search(r"\bnone\b", text):
        return "none"
    return UNPARSEABLE


def _retryable(exc: Exception) -> bool:
    """Transient API failures worth another attempt; auth/validation errors are not.

    Classified by exception *name* rather than isinstance against anthropic's
    types on purpose: that keeps this function importable — and therefore
    unit-testable — without the anthropic package installed. CI runs the tests
    with stdlib only.
    """
    if type(exc).__name__ in (
        "APIConnectionError", "APITimeoutError", "RateLimitError",
        "InternalServerError", "OverloadedError",
    ):
        return True
    return getattr(exc, "status_code", None) in (408, 409, 429, 500, 502, 503, 529)


def run_one_call(client, model: str, system: str, query: str, names: list[str]):
    """One selector call, with bounded retry. Returns (choice, in_tokens, out_tokens).

    Retry exists because this runs inside a ThreadPoolExecutor whose results are
    collected with Future.result(): one unhandled 429 propagates out, aborts the
    entire run, and forfeits every token already paid for in earlier queries.
    A permanent failure (401, malformed request) still raises — retrying that
    would just burn attempts on something that cannot succeed.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=20,
                system=system,
                messages=[{"role": "user", "content": query}],
            )
            text = "".join(block.text for block in msg.content if block.type == "text")
            return parse_choice(text, names), msg.usage.input_tokens, msg.usage.output_tokens
        except Exception as exc:
            if attempt == MAX_ATTEMPTS or not _retryable(exc):
                raise
            delay = BASE_BACKOFF**attempt + random.uniform(0, 0.5)
            log(f"  transient {type(exc).__name__}, attempt {attempt}/{MAX_ATTEMPTS} — retrying in {delay:.1f}s")
            time.sleep(delay)


def evaluate(rate: float, expect: str, threshold: float) -> bool:
    return rate > threshold if expect == "trigger" else rate < threshold


def main() -> int:
    ap = argparse.ArgumentParser(description="Run trigger evals for a dv skill.")
    ap.add_argument("skill", help="skill name (e.g. cite) or path to a triggers.json")
    ap.add_argument("--plugin-root", default=DEFAULT_PLUGIN_ROOT)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--runs", type=int, default=None, help="override runs_per_query")
    ap.add_argument("--threshold", type=float, default=None, help="override pass_threshold")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--json", action="store_true", help="emit JSON summary to stdout")
    ap.add_argument("--dry-run", action="store_true", help="no API calls; print plan")
    args = ap.parse_args()

    plugin_root = Path(args.plugin_root)

    # Resolve fixtures: a path, or <plugin-root>/skills/<name>/evals/triggers.json
    if args.skill.endswith(".json"):
        fixtures_path = Path(args.skill)
    else:
        fixtures_path = plugin_root / "skills" / args.skill / "evals" / "triggers.json"
    if not fixtures_path.exists():
        raise SystemExit(f"Fixtures not found: {fixtures_path}")

    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    target = fixtures["skill"]
    runs = args.runs or fixtures.get("runs_per_query", 3)
    threshold = args.threshold if args.threshold is not None else fixtures.get("pass_threshold", 0.5)
    queries = fixtures["queries"]
    # Fail fast rather than dividing by zero later: with no queries, `overall`
    # summarizes to pass_rate None and the report's unguarded `:.0%` format
    # raises TypeError after the run has already been paid for.
    if not queries:
        raise SystemExit(f"{fixtures_path}: 'queries' is empty — nothing to evaluate")

    catalog = load_catalog(plugin_root)
    names = [s["name"] for s in catalog]
    if target not in names:
        raise SystemExit(f"Target skill '{target}' not in catalog {names}")
    system = render_system_prompt(catalog)

    if args.dry_run:
        log("=== DRY RUN — no API calls ===")
        log(f"target skill : {target}")
        log(f"catalog      : {', '.join(names)}")
        log(f"runs/query   : {runs}   threshold: {threshold}   model: {args.model}")
        log(f"queries      : {len(queries)} ({sum(q['expect']=='trigger' for q in queries)} trigger / "
            f"{sum(q['expect']=='no_trigger' for q in queries)} no_trigger)")
        log(f"planned calls: {len(queries) * runs}")
        log("\n--- rendered selector system prompt ---")
        log(system)
        log("\n--- queries ---")
        for q in queries:
            log(f"  [{q['split']:<5} {q['expect']:<10}] {q['q']}")
        if args.json:
            print(json.dumps({
                "dry_run": True, "skill": target, "catalog": names,
                "runs": runs, "threshold": threshold,
                "planned_calls": len(queries) * runs,
            }, indent=2))
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set (use --dry-run to test without it)")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    log(f"Running {len(queries)} queries x {runs} = {len(queries) * runs} calls "
        f"against model {args.model} ...")

    results = []
    tok_in = tok_out = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for q in queries:
            futs = [pool.submit(run_one_call, client, args.model, system, q["q"], names)
                    for _ in range(runs)]
            choices = []
            for f in futs:
                choice, ti, to = f.result()
                choices.append(choice)
                tok_in += ti
                tok_out += to
            selections = sum(c == target for c in choices)
            unparseable = sum(c == UNPARSEABLE for c in choices)
            rate = selections / runs
            passed = evaluate(rate, q["expect"], threshold)
            results.append({**q, "rate": rate, "selections": selections,
                            "runs": runs, "choices": choices, "passed": passed,
                            "unparseable": unparseable})
            mark = "PASS" if passed else "FAIL"
            warn = f"  [!] {unparseable}/{runs} unparseable" if unparseable else ""
            log(f"  [{mark}] rate={rate:.2f} ({q['expect']:<10} {q['split']:<5}) "
                f"picks={choices}  {q['q'][:60]}{warn}")

    def summarize(subset):
        if not subset:
            return {"n": 0, "passed": 0, "pass_rate": None}
        passed = sum(r["passed"] for r in subset)
        return {"n": len(subset), "passed": passed, "pass_rate": passed / len(subset)}

    summary = {
        "skill": target,
        "model": args.model,
        "runs_per_query": runs,
        "threshold": threshold,
        "overall": summarize(results),
        "train": summarize([r for r in results if r["split"] == "train"]),
        "val": summarize([r for r in results if r["split"] == "val"]),
        "tokens": {"input": tok_in, "output": tok_out},
        "unparseable": sum(r["unparseable"] for r in results),
        "failures": [
            {"q": r["q"], "expect": r["expect"], "split": r["split"], "rate": r["rate"]}
            for r in results if not r["passed"]
        ],
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        o, t, v = summary["overall"], summary["train"], summary["val"]
        print(f"\n=== trigger evals: {target} (model {args.model}, {runs} runs/query) ===")
        print(f"overall : {o['passed']}/{o['n']} passed ({o['pass_rate']:.0%})")
        print(f"train   : {t['passed']}/{t['n']} passed"
              + (f" ({t['pass_rate']:.0%})" if t["n"] else ""))
        print(f"val     : {v['passed']}/{v['n']} passed"
              + (f" ({v['pass_rate']:.0%})" if v["n"] else "")
              + "   <- select the best description iteration by this number")
        print(f"tokens  : {tok_in} in / {tok_out} out")
        if summary["unparseable"]:
            # Loud, because these are the samples most likely to be scored
            # wrongly: an unparseable response counts against a should-trigger
            # query correctly, but makes a should-NOT-trigger query look like
            # it passed for the right reason when it did not.
            print(f"WARNING : {summary['unparseable']} unparseable response(s) — "
                  f"no_trigger passes may be spurious; inspect `picks` above")
        if summary["failures"]:
            print("\nfailures:")
            for fl in summary["failures"]:
                print(f"  - [{fl['split']} {fl['expect']}] rate={fl['rate']:.2f}  {fl['q']}")

    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
