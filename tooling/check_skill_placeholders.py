#!/usr/bin/env python3
"""Fail if any skill's SKILL.md contains `$` followed by a digit.

Claude Code treats `$0`, `$1`, ... in a skill as argument placeholders. When a
skill is run with text after its command (`/dv:pickup some words`), each
`$<digit>` is replaced with one of those words, everywhere in the file: prose,
inline code and fenced shell or awk blocks alike. A shell `$1`, an awk `$0` or
a price like `$1.99` then silently becomes one of the user's words. VIL-517:
that replaced the key in dv:pickup's frontmatter reader with an argument word,
so every field read blank, and emptied every worktree path in its listing.

Claude Code's pattern is `\\$(\\d+)(?!\\w)`; this check is stricter and flags
any `$` followed by a digit, so an escaped `\\$1` (which shows its backslash
when the skill runs without arguments) is flagged too. Write awk's whole-line
field as `$(0)`, pass a shell function its input some other way, and write
amounts as `USD 350`. `$ARGUMENTS` itself is fine where it is meant.

Stdlib only, like the eval-harness unit tests, so CI runs it with nothing
installed:

    python3 tooling/check_skill_placeholders.py [repo-root]

Exits non-zero, listing file:line:column for each hit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\$[0-9]+")


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    skills = sorted(root.glob("plugins/*/skills/*/SKILL.md"))
    if not skills:
        print(f"::error::No plugins/*/skills/*/SKILL.md under {root}")
        return 1

    hits = 0
    for path in skills:
        rel = path.relative_to(root)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in PLACEHOLDER.finditer(line):
                hits += 1
                print(
                    f"::error file={rel},line={lineno},col={m.start() + 1}::"
                    f"{rel}:{lineno}:{m.start() + 1}: `{m.group()}` is an argument "
                    f"placeholder in Claude Code: {line.strip()}"
                )

    if hits:
        print(f"{hits} placeholder hit(s) in {len(skills)} SKILL.md file(s).")
        return 1
    print(f"OK: no `$` followed by a digit in {len(skills)} SKILL.md file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
