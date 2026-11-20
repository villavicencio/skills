# dv — v0.14.2

Patch release. `dv:groom` and `dv:ticket` recognise when Linear's text search has cut a search off
at 100 results, and narrow the search instead of treating it as complete. The other twelve skills
have no behaviour changes; their version moves to `0.14.2` only because the suite is released as
one plugin.

Why: Linear's `list_issues` with a `query` returns at most 100 matches in all, and at 100 it says
`hasNextPage: false` even though more matched. Checked on 2026-11-20 on team VIL with query "the":
`limit: 50` paged 50 + 50 and stopped; `limit: 100` and `limit: 250` each returned exactly 100. In the
VIL-813 fixture run of 2026-11-20 on dv 0.14.1, all three of groom's overlap searches returned
exactly 100 and were reported as finished. 0.14.1's rule ("finished only at `hasNextPage: false`")
cannot catch this, because the reply says there is nothing more.

## Changed

- **`dv:groom` step 1, "Overlapping work"**:
  - asks for `limit: 100`, since a text search never returns more;
  - a search whose pages add up to 100 has been cut off. Groom narrows it with more specific words,
    or splits it with a `state` filter (one search per state type) or a `project` filter, until it
    returns fewer than 100, and tallies each narrowed search on its own. A search still at 100 after
    two narrowings is reported as capped and counts as incomplete, so it rules nothing out and the
    ticket is not reported ready (0.14.1's rule for an incomplete search).
  - Step 5's spin-off duplicate search follows the same rule, since it reads pages as step 1 does.
- **`dv:ticket` File step 3, "Existing tickets"**: a duplicate search that returns 100 was cut off,
  and is narrowed until it returns fewer.

Refs VIL-813.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
