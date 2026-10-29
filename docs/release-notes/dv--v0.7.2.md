# dv — v0.7.2

Patch release. It shortens `dv:pickup`'s kickoff. The other skills have no behaviour changes; their
version moves to `0.7.2` only because the suite is released as one plugin.

## Changed

### `dv:pickup`: the kickoff aims for 10 lines

The kickoff had seven sections, including a prose summary, every other session, CE artifacts and
every gotcha from the handoff. Coming back to a session after working in others, that was a wall
of text to read before starting. It now has a fixed layout: anchor line with its movers, drift (only if any),
next up, needs you (only if any), live sessions only, and only the gotchas that affect the next
step. CE artifacts are mentioned only when they bear on the next step. Everything else stays in the
handoff, behind "details?".

Ten lines is a budget, not a hard cap: movers, other sessions and CE artifacts show 3 and "+N more"
(sessions whose branch or focus points at the next step's area come first), but drift, unverified
claims, needs-you and the relevant gotchas are never cut, even when that runs past 10 lines. Step 2b now feeds only the relevant CE artifacts
to the kickoff. The kickoff ends with one offer of
the next step, the same as before.

Steps 1–2b and the drift cross-check are unchanged.
