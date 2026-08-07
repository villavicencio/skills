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


# --- Retry classification -----------------------------------------------------
# Transient failures get another attempt; permanent ones must raise immediately
# rather than burning the retry budget on something that cannot succeed.

class _Fake(Exception):
    """Stand-in for an anthropic error, matched by class name or status_code."""

    def __init__(self, name: str = "Fake", status: int | None = None):
        super().__init__(name)
        self.__class__.__name__ = name
        self.status_code = status


for name in ["APIConnectionError", "APITimeoutError", "RateLimitError",
             "InternalServerError", "OverloadedError"]:
    check(f"retry: {name} is retryable", harness._retryable(_Fake(name)), True)

for status in [408, 409, 429, 500, 502, 503, 529]:
    check(f"retry: HTTP {status} is retryable", harness._retryable(_Fake("APIStatusError", status)), True)

for status in [400, 401, 403, 404, 422]:
    check(f"retry: HTTP {status} is NOT retryable", harness._retryable(_Fake("APIStatusError", status)), False)

check("retry: unknown exception with no status is NOT retryable",
      harness._retryable(ValueError("boom")), False)


# --- Retry budget is bounded --------------------------------------------------

check("retry: MAX_ATTEMPTS is bounded", 1 < harness.MAX_ATTEMPTS <= 6, True)
check("retry: backoff base grows", harness.BASE_BACKOFF > 1, True)


if failures:
    print(f"FAILED — {len(failures)} check(s):\n", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

print("ok — trigger parsing and retry classification")
