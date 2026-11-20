# dv — v0.14.1

Patch release. `dv:groom` reads every page of its overlap and spin-off duplicate searches, and the
report shows how many pages each search read. The other thirteen skills have no behaviour changes;
their version moves to `0.14.1` only because the suite is released as one plugin.

Why: in the VIL-813 fixture runs on 2026-11-19 and 2026-11-20, three of six grooms (VIL-845, VIL-847
and VIL-848) read only the first page of their `list_issues` searches. The skill already said to
follow the cursor. `list_issues` returns 50 results a page by default, so a broad search on team
VIL often runs past one page, and nothing in the report showed when a search had stopped early.

## Changed

- **`dv:groom` step 1, "Overlapping work"**, now spells out how to read a search to its end:
  - ask for `limit: 250` and `fields: ["id", "title", "status"]`. Short rows make a full search
    usually fit on one page; on 2026-11-20 a 98-result search on team VIL came back in one page.
    Candidates are read in full later with `get_issue`;
  - while a reply says `hasNextPage: true`, call again with the same arguments and its `cursor`. A
    search is finished only at `hasNextPage: false`, and one that stops before that is reported as
    incomplete;
  - keep a tally per search: its words, pages read and results.
- **`dv:groom` step 5**: the spin-off duplicate search reads every page and keeps the same tally.
- **`dv:groom` step 6**: the overlapping-work findings open with one tally per search, so a search
  that stopped early shows in the report.

Refs VIL-813.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
