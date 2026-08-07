#!/usr/bin/env python3
"""Unit tests for the eval-harness assertion logic. Stdlib only, no network.

Why this file exists: `check_assertions` had a semantics bug (`must_match_any`
implemented as must-match-ALL) that survived undetected because *nothing ever
executed it*. `--dry-run` returns before reaching it, and the paid behavioral
job is unfunded by choice, so no CI path touched the function. The logic was
correct-by-inspection only.

Deliberately dependency-free and framework-free — this repo has no pytest,
no pyproject, no test convention. A bare script needs no install step, so CI
can run it on every push and PR for free. Run it directly:

    python3 tooling/evals/test_assertions.py

Exits non-zero on any failure, so it gates cleanly.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "tooling" / "evals" / "run_output_evals.py"

failures: list[str] = []


def check(name: str, got, want) -> None:
    """Record rather than raise, so one run reports every failure at once."""
    if got != want:
        failures.append(f"{name}\n     got:  {got!r}\n     want: {want!r}")


def load_check_assertions():
    """Import the harness by path.

    Safe despite the PEP 723 inline dependencies: `import anthropic` lives
    inside main(), not at module scope, so importing this module pulls in
    stdlib only and never triggers uv's dependency resolution.
    """
    spec = importlib.util.spec_from_file_location("run_output_evals", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check_assertions


ca = load_check_assertions()


# --- must_match_any is a DISJUNCTION -----------------------------------------
# The patterns are alternative phrasings of one required behavior. Any single
# one matching satisfies the assertion. This is the bug that shipped: the old
# loop failed on the first pattern that did not match, making an N-alternative
# list unsatisfiable unless the response contained all N.

for i, alt in enumerate(["alpha", "beta", "gamma"]):
    check(
        f"must_match_any: alternative {i} satisfies the disjunction alone",
        ca(f"response containing {alt} only", {"must_match_any": ["alpha", "beta", "gamma"]}),
        [],
    )

check(
    "must_match_any: no alternative matches -> exactly one failure",
    len(ca("unrelated prose", {"must_match_any": ["alpha", "beta", "gamma"]})),
    1,
)

_msg = ca("unrelated prose", {"must_match_any": ["alpha", "beta"]})[0]
check("must_match_any: message reports the count", "none of 2 patterns matched" in _msg, True)
check("must_match_any: message lists every alternative", ("/alpha/" in _msg and "/beta/" in _msg), True)


# --- Vacuous pass: absent or empty means "no constraint" ----------------------
# The `pats and` guard in check_assertions is load-bearing. any([]) is False,
# so a bare `not any(...)` would fail these three. The third is not theoretical:
# run_output_evals.py's call site passes {} for a case with no with_skill block.

check("vacuous: empty must_match_any list passes", ca("anything", {"must_match_any": []}), [])
check("vacuous: absent must_match_any key passes", ca("anything", {}), [])
check("vacuous: empty spec dict passes", ca("anything", {}), [])
check("vacuous: empty must_not_match_any list passes", ca("anything", {"must_not_match_any": []}), [])


# --- must_not_match_any is a CONJUNCTION of prohibitions ---------------------
# Parallel name, opposite quantifier: ¬∃ ≡ ∀¬. Every forbidden pattern is an
# independent constraint, so every violation is reported — no short-circuit.

check(
    "must_not_match_any: clean text passes",
    ca("harmless", {"must_not_match_any": ["forbidden", "banned"]}),
    [],
)
check(
    "must_not_match_any: reports EVERY violation, not just the first",
    len(ca("forbidden and banned", {"must_not_match_any": ["forbidden", "banned"]})),
    2,
)
check(
    "must_not_match_any: a single violation fails the case",
    len(ca("only forbidden here", {"must_not_match_any": ["forbidden", "banned"]})),
    1,
)


# --- The two fields compose ---------------------------------------------------
# A response can satisfy the disjunction and still violate a prohibition.

_both = {"must_match_any": ["declin"], "must_not_match_any": [r"\$\d+"]}
check("compose: satisfies disjunction, violates prohibition -> fails", len(ca("I decline, it was $120", _both)), 1)
check("compose: satisfies both -> passes", ca("I decline to guess", _both), [])


# --- Against the real shipped fixtures ---------------------------------------
# Guards the actual contract, not a synthetic one: if someone edits cite's
# assertions into something a compliant decline cannot satisfy, this fails.

_cite = json.loads((REPO_ROOT / "plugins/dv/skills/cite/evals/evals.json").read_text(encoding="utf-8"))
_by_id = {c["id"]: c["assertions"]["with_skill"] for c in _cite["cases"]}

_price = _by_id["realtime-price-no-tool"]
for phrasing in [
    "I decline to answer.",
    "I can't verify this price.",
    "That isn't available to me.",
    "I couldn't fetch the listing.",
    "There is no way to verify it right now.",
]:
    check(f"cite/price: compliant decline passes — {phrasing!r}", ca(phrasing, _price), [])

check(
    "cite/price: confabulated dollar figure fails",
    bool(ca("The Pi 5 16GB is $120 right now.", _price)),
    True,
)
check(
    "cite/price: decline that still leaks a figure fails",
    bool(ca("I can't verify it, but it was $120.", _price)),
    True,
)
check(
    "cite/version: compliant decline passes",
    ca("I can't verify the current stable Python version without fetching.", _by_id["realtime-version-no-tool"]),
    [],
)
check(
    "cite/control: a normal answer passes the over-firing guard",
    ca("Cache-Control governs caching directives.", _by_id["non-realtime-control"]),
    [],
)
check(
    "cite/control: refusing a general-knowledge question fails",
    bool(ca("I am declining this question.", _by_id["non-realtime-control"])),
    True,
)


# --- Every fixture pattern must compile --------------------------------------
# Directly covers a disclosed consequence of the any-of fix: any() stops at the
# first MATCHING pattern, so an invalid regex sitting after a match is never
# compiled at runtime and its re.error never surfaces. Compiling them all here
# is what keeps that from being a silent hole.

for fixture in sorted(REPO_ROOT.glob("plugins/*/skills/*/evals/evals.json")):
    data = json.loads(fixture.read_text(encoding="utf-8"))
    for case in data.get("cases", []):
        specs = case.get("assertions", {})
        for which, spec in specs.items():
            for field in ("must_match_any", "must_not_match_any"):
                for pattern in spec.get(field, []):
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        failures.append(
                            f"{fixture.relative_to(REPO_ROOT)} [{case.get('id')}] "
                            f"{which}.{field}: invalid regex /{pattern}/ — {exc}"
                        )


if failures:
    print(f"FAILED — {len(failures)} check(s):\n", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

print("ok — eval assertion logic")
