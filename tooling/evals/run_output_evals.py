#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "anthropic>=0.40",
# ]
# ///
"""Output-quality evals for dv skills.

For each case, runs the model twice:
  * WITH the skill — the SKILL.md body injected as the system prompt
  * WITHOUT the skill — a neutral baseline system prompt

Then applies code-checkable regex assertions to the WITH-skill response and
captures the baseline for human comparison. Per the cheat-sheet rule, assertions
are mechanical (regex match / non-match), never "is it good".

Cases run with NO tools available. For cite that is the point: on a realtime
fact with no fetch path, the contract is to DECLINE, not to quote a remembered
value — so a bare API call (no network) deterministically exercises the
decline-vs-confabulate decision the skill governs.

Usage:
  export ANTHROPIC_API_KEY=sk-...
  ./run_output_evals.py cite
  ./run_output_evals.py cite --json
  ./run_output_evals.py cite --dry-run     # no API calls; print plan

Exit code is non-zero if any case fails (real runs only).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_PLUGIN_ROOT = "plugins/dv"
BASELINE_SYSTEM = "You are a helpful, knowledgeable assistant. Answer the user's question concisely."
MAX_TOKENS = 500


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def load_skill_body(skill_md: Path) -> str:
    """SKILL.md with the YAML frontmatter stripped — the instructions the agent reads."""
    text = skill_md.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text.strip()


def check_assertions(text: str, spec: dict) -> list[str]:
    """Return a list of failure messages ([] == all assertions passed).

    The two fields quantify differently, despite the parallel names:
      * must_match_any     — at least ONE pattern must match. The patterns are
                             alternative phrasings of a single required
                             behavior, not N independent requirements.
      * must_not_match_any — NO pattern may match. Each is an independent
                             prohibition, so every violation is reported.
    Both are optional; an absent key or an empty list is no constraint.
    """
    failures = []
    pats = spec.get("must_match_any", [])
    # The `pats and` guard is load-bearing, not stylistic: any([]) is False, so
    # dropping it would fail every case that omits the key or lists no
    # alternatives — and the call site passes {} for a case with no with_skill
    # assertions at all.
    if pats and not any(re.search(p, text) for p in pats):
        alts = ", ".join(f"/{p}/" for p in pats)
        failures.append(f"must_match_any unsatisfied: none of {len(pats)} patterns matched: {alts}")
    for pat in spec.get("must_not_match_any", []):
        if re.search(pat, text):
            failures.append(f"must_not_match_any violated: matched /{pat}/")
    return failures


def call(client, model, system, prompt):
    msg = client.messages.create(
        model=model, max_tokens=MAX_TOKENS, system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    return text, msg.usage.input_tokens, msg.usage.output_tokens


def main() -> int:
    ap = argparse.ArgumentParser(description="Run output-quality evals for a dv skill.")
    ap.add_argument("skill", help="skill name (e.g. cite) or path to an evals.json")
    ap.add_argument("--plugin-root", default=DEFAULT_PLUGIN_ROOT)
    ap.add_argument("--model", default=None, help="override model (else evals.json, else default)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plugin_root = Path(args.plugin_root)
    if args.skill.endswith(".json"):
        evals_path = Path(args.skill)
        skill_name = evals_path.parent.parent.name
    else:
        skill_name = args.skill
        evals_path = plugin_root / "skills" / skill_name / "evals" / "evals.json"
    if not evals_path.exists():
        raise SystemExit(f"Evals not found: {evals_path}")

    evals = json.loads(evals_path.read_text(encoding="utf-8"))
    model = args.model or evals.get("model") or DEFAULT_MODEL
    skill_md = plugin_root / "skills" / skill_name / "SKILL.md"
    skill_body = load_skill_body(skill_md)
    cases = evals["cases"]

    if args.dry_run:
        log("=== DRY RUN — no API calls ===")
        log(f"skill        : {skill_name}")
        log(f"model        : {model}")
        log(f"skill body   : {len(skill_body)} chars injected as with-skill system prompt")
        log(f"cases        : {len(cases)}  (each runs with-skill + baseline = {len(cases) * 2} calls)")
        for c in cases:
            asrt = c.get("assertions", {}).get("with_skill", {})
            log(f"\n  [{c['id']}] {c['prompt']}")
            log(f"    intent: {c.get('intent','')}")
            for k in ("must_match_any", "must_not_match_any"):
                for p in asrt.get(k, []):
                    log(f"    {k}: /{p}/")
        if args.json:
            print(json.dumps({"dry_run": True, "skill": skill_name, "model": model,
                              "cases": [c["id"] for c in cases]}, indent=2))
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set (use --dry-run to test without it)")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    log(f"Running {len(cases)} cases (with-skill + baseline) against {model} ...")
    results = []
    tok_in = tok_out = 0
    for c in cases:
        with_text, ai, ao = call(client, model, skill_body, c["prompt"])
        base_text, bi, bo = call(client, model, BASELINE_SYSTEM, c["prompt"])
        tok_in += ai + bi
        tok_out += ao + bo
        failures = check_assertions(with_text, c.get("assertions", {}).get("with_skill", {}))
        passed = not failures
        results.append({
            "id": c["id"], "passed": passed, "failures": failures,
            "with_skill_response": with_text, "baseline_response": base_text,
        })
        mark = "PASS" if passed else "FAIL"
        log(f"  [{mark}] {c['id']}")
        for fl in failures:
            log(f"         {fl}")

    summary = {
        "skill": skill_name, "model": model,
        "n": len(results), "passed": sum(r["passed"] for r in results),
        "tokens": {"input": tok_in, "output": tok_out},
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n=== output evals: {skill_name} (model {model}) ===")
        print(f"passed: {summary['passed']}/{summary['n']}")
        print(f"tokens: {tok_in} in / {tok_out} out")
        for r in results:
            if not r["passed"]:
                print(f"\nFAIL {r['id']}:")
                for fl in r["failures"]:
                    print(f"  {fl}")
                print(f"  with-skill : {r['with_skill_response'][:200]!r}")
                print(f"  baseline   : {r['baseline_response'][:200]!r}")

    return 0 if summary["passed"] == summary["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
