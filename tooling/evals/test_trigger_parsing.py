#!/usr/bin/env python3
"""Unit tests for the trigger-eval harness's parsing and retry classification.

Stdlib only, no network, no third-party packages — same contract as
test_assertions.py, and for the same reason: logic that CI never executes is
logic whose bugs nobody finds.

That contract constrains the harness under test, not just this file. Three
things keep `run_trigger_evals.py` importable with nothing installed:
`import anthropic` lives inside main(), `import yaml` inside
parse_frontmatter(), and `_retryable` classifies by exception *name* rather
than isinstance against anthropic's types. A module-scope third-party import
in that file breaks this suite — which is not hypothetical: a top-level
`import yaml` did exactly that, and CI caught it because the always-on test
step installs nothing.

    python3 tooling/evals/test_trigger_parsing.py

Exits non-zero on any failure.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "tooling" / "evals" / "run_trigger_evals.py"

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}\n     got:  {got!r}\n     want: {want!r}")


spec = importlib.util.spec_from_file_location("run_trigger_evals", HARNESS)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

parse_choice = harness.parse_choice
UNPARSEABLE = harness.UNPARSEABLE

NAMES = ["cite", "critique", "gauntlet", "handoff", "pickup", "reddit",
         "review-claudemd", "tmux-window-namer", "twitter"]


# --- A clean selection resolves to the catalog name --------------------------

check("parse: bare name", parse_choice("cite", NAMES), "cite")
check("parse: trailing newline and case", parse_choice("Cite\n", NAMES), "cite")
check("parse: hyphenated name", parse_choice("review-claudemd", NAMES), "review-claudemd")
check("parse: explicit none", parse_choice("none", NAMES), "none")
check("parse: none with punctuation", parse_choice("None.", NAMES), "none")


# --- UNPARSEABLE is NOT 'none' ------------------------------------------------
# This is the bug being fixed. A refusal, an empty completion, or a
# response-format change previously scored as a legitimate "correctly did not
# trigger", quietly inflating the no_trigger pass rate. A should-trigger query
# is unaffected either way (neither is the target), but a should-NOT-trigger
# query would pass for entirely the wrong reason.

for label, text in [
    ("refusal", "I'm sorry, I can't help with that."),
    ("empty completion", ""),
    ("whitespace only", "   \n  "),
    ("truncated json", '```json\n{"skill":'),
    ("prose with no verdict", "This depends on what the user is trying to do."),
]:
    check(f"parse: {label} is UNPARSEABLE, not 'none'", parse_choice(text, NAMES), UNPARSEABLE)

check("parse: UNPARSEABLE sentinel is distinct from 'none'", UNPARSEABLE == "none", False)
check("parse: UNPARSEABLE sentinel is not a catalog name", UNPARSEABLE in NAMES, False)


# --- Retry is delegated to the SDK -------------------------------------------
# The hand-rolled retry loop was removed: it stacked on the SDK's own retries
# and its blind backoff ignored Retry-After, which the SDK honors. What remains
# testable without the anthropic package is *structural* — that the client is
# still constructed with an explicit, raised retry budget. Asserted via AST
# rather than a string search so reformatting cannot silently defeat it.

check("retry: budget is raised above the SDK default of 2", harness.MAX_RETRIES > 2, True)
check("retry: budget is not absurd", harness.MAX_RETRIES <= 10, True)

_src = ast.parse(HARNESS.read_text(encoding="utf-8"))
_anthropic_calls = [
    node for node in ast.walk(_src)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and node.func.attr == "Anthropic"
]
check("retry: exactly one Anthropic client is constructed", len(_anthropic_calls), 1)
if _anthropic_calls:
    _kwargs = {kw.arg for kw in _anthropic_calls[0].keywords}
    check("retry: client passes max_retries explicitly", "max_retries" in _kwargs, True)
    _val = next(kw.value for kw in _anthropic_calls[0].keywords if kw.arg == "max_retries")
    check("retry: max_retries is wired to the MAX_RETRIES constant",
          isinstance(_val, ast.Name) and _val.id == "MAX_RETRIES", True)

# The removed loop must stay removed — a reintroduced wrapper would re-stack.
check("retry: no hand-rolled retry helper remains", hasattr(harness, "_retryable"), False)


# --- Scoring excludes unparseable samples from the denominator ---------------
# The defect this closes (issue #26): dividing by every run let a malformed
# response drag a no_trigger query's rate toward 0 and thereby pass it.

score = harness.score_query
T = "cite"
U = UNPARSEABLE

# The exact regression from the issue. Strict `<` in evaluate() is what makes
# 1/2 fail where 1/3 passed, so this pair is the whole point.
_rate, _passed, _unp, _parse = score([T, "none", U], T, "no_trigger", 0.5)
check("score: unparseable excluded -> rate is 1/2, not 1/3", _rate, 0.5)
check("score: that no_trigger query now FAILS (it used to pass)", _passed, False)
check("score: unparseable counted", _unp, 1)
check("score: parseable counted", _parse, 2)

# Same samples with no garbage must be untouched — the fix must not move
# verdicts for clean runs.
check("score: clean no_trigger below threshold still passes",
      score([T, "none", "none"], T, "no_trigger", 0.5)[1], True)
check("score: clean trigger above threshold still passes",
      score([T, T, "none"], T, "trigger", 0.5)[1], True)
check("score: clean rate is unchanged when nothing is unparseable",
      score([T, T, "none"], T, "trigger", 0.5)[0], 2 / 3)

# All-unparseable is indeterminate, NOT a clean 0.0 no_trigger pass.
_rate, _passed, _unp, _parse = score([U, U, U], T, "no_trigger", 0.5)
check("score: all-unparseable rate is None (indeterminate)", _rate, None)
check("score: all-unparseable FAILS rather than passing on no data", _passed, False)
check("score: all-unparseable reports zero parseable", _parse, 0)
check("score: all-unparseable also fails a trigger query",
      score([U, U], T, "trigger", 0.5)[1], False)

# A single surviving sample still scores, on the reduced denominator.
check("score: one parseable selection out of three -> 1.0",
      score([T, U, U], T, "trigger", 0.5)[0], 1.0)
check("score: one parseable non-selection -> 0.0",
      score(["none", U, U], T, "trigger", 0.5)[0], 0.0)


if failures:
    print(f"FAILED — {len(failures)} check(s):\n", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

print("ok — trigger parsing and retry classification")
