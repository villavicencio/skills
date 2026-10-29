# dv — v0.7.2

Patch release. It shortens `dv:pickup`'s kickoff. The other skills have no behaviour changes; their
version moves to `0.7.2` only because the suite is released as one plugin.

## Changed

### `dv:pickup`: the kickoff aims for 10 lines

The kickoff had seven sections, including a prose summary, every other session, CE artifacts and
every gotcha from the handoff. Coming back to a session after working in others, that was a wall
of text to read before starting. It now has a fixed layout: anchor line, drift (only if any),
next up, needs you (only if any), live sessions only, and only the gotchas that affect the next
step. CE artifacts are mentioned only when they bear on the next step. Everything else stays in the
handoff, behind "details?".

Ten lines is a budget, not a hard cap: longer lists show 3 items and "+N more", but drift and
needs-you are never cut, even when that runs past 10 lines. The kickoff ends with one offer of
the next step, the same as before.

Steps 1–2b and the drift cross-check are unchanged.
