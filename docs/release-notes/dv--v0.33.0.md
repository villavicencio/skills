# dv — v0.33.0

Minor release. `dv:groom` in `forks-only` mode now records a routine call under Decisions only
when the call changes the ticket or settles an open decision, a keep that settles one included. A
call that only keeps something no step 3 check or open Decisions line put in question (a title,
priority, label, section or line kept as it is) gets no Decisions line. The other
fifteen skills have no behaviour changes; their version moves to `0.33.0` only because the suite
is released as one plugin.

Numbering: 0.33.0 follows 0.32.0, which made `dv:ticket` and `dv:groom` put each ticket in a
project milestone.

Why: in a live forks-only run, grooming recorded "Title keeps its [scratch] prefix" as a Decisions
line, though nothing was decided. Lines like that bury the routine calls the user may want to
overrule, which is what the Decisions lines are for (VIL-927).

## Changed

- **`dv:groom`, "Forks-only mode", "Recording".** A routine call is recorded only when it changes
  the ticket or settles an open decision (one that step 3 collects, a spin-off, or the split),
  also when it settles one by keeping what is there. Any other call that leaves something as it
  was (a title, priority, label, section or line that no step 3 check or Decisions line put in
  question) is not recorded, even when the session weighed changing it. Verdicts stay recorded:
  - Size and its points are recorded when they are set or changed, and the no-split verdict is
    recorded unless the ticket already records the same verdict (for a ticket pointed 13, "no
    split" is the user's answer to a fork, as before). Each is a verdict, not a field left as it
    was.
  - A fork's answer is recorded in the default form whatever it is, a keep included.
  - A routine call that settles a Decisions line marked open replaces that line.
- **`dv:groom`, step 6 and the report.** Step 6's forks-only paragraph and the report's "Decided
  without asking" list follow the same rule: they cover the routine calls that "Recording" says to
  record, so the list and the Decisions lines stay the same set whenever the ticket's text is
  edited. When its text is left unchanged (the last Rules bullet), the calls are listed in the
  report and not recorded, as before.
- **README.** The `dv:groom` entry says which routine calls get a Decisions line, and the plugin
  table shows `0.33.0`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
