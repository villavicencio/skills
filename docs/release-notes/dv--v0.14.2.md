# dv — v0.14.2

Patch release. `dv:groom` and `dv:ticket` recognise when Linear's text search has cut a search off
at 100 results, and finish it with a scan of every title in the team. The other twelve skills have
no behaviour changes; their version moves to `0.14.2` only because the suite is released as one
plugin.

Why: Linear's `list_issues` with a `query` returns only its first 100 matches, and at 100 it says
`hasNextPage: false` even though more matched. A `state` or `project` filter does not get past this:
it filters those 100, not every match. Checked on 2026-11-20 on team VIL with query "the":

- `limit: 50` paged 50 + 50 and stopped; `limit: 100` and `limit: 250` each returned exactly 100;
- adding `state: completed` returned 52 and `state: unstarted` returned 12, every one of them from
  the same first 100.

Listing with no `query` pages normally (`limit: 250`, cursor honoured). In the VIL-813 fixture run of
2026-11-20 on dv 0.14.1, all three of groom's overlap searches returned exactly 100 and were reported
as finished. 0.14.1's rule ("finished only at `hasNextPage: false`") cannot catch this, because the
reply says there is nothing more.

## Changed

- **`dv:groom` step 1, "Overlapping work"**:
  - asks for `limit: 100`, since a text search never returns more;
  - a search that returns 100 is cut off. Groom finishes it with a title scan: it lists the team's
    issues with no `query`, every page, and picks out the titles that hold the search's words. The
    scan runs once per run and serves every capped search. A capped search whose scan finished
    counts as finished, with "capped at 100; titles scanned: N issues" in its tally, and
    "descriptions beyond the first 100 matches" goes under what was not checked. If the scan stops
    early, the search is incomplete, and 0.14.1's rule applies: it rules nothing out and the ticket
    is not reported ready.
  - Step 5's spin-off duplicate search follows the same rule, since it reads pages as step 1 does.
- **`dv:ticket` File step 3, "Existing tickets"**: a duplicate search that returns 100 is finished
  the same way, by listing the team's issues with no `query` and reading the titles.

Refs VIL-813.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
