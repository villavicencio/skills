# dv — v0.14.3

Patch release. `dv:groom` and `dv:ticket` treat a ticket id written into a description or comment
as a relation, because Linear makes it one. The other twelve skills have no behaviour changes; their
version moves to `0.14.3` only because the suite is released as one plugin.

Why: Linear relates every ticket whose id (`VIL-N`) appears in a description or comment, with no
`relatedTo` call. In a groom fixture run on 2026-11-20 (dv 0.14.2), David approved items 1, 3 and 4
of an edit list and declined item 2, a related link to another ticket. Item 1, a new description,
named that ticket, so Linear related it anyway, and related a second ticket the text cited as an
example. The report then said the declined link was "not applied", because it never read the
relations back.

## Changed

- **Shared rules (`plugins/dv/skills/ticket/references/ticket-format.md`)**: a new section, "Ticket ids in text".
  Writing an id is writing a relation. Before saving text, name each id it adds that the ticket is
  not yet related to. When a relation is not wanted, write the PR, repo, file or title instead of
  the id. After saving, read the relations back. `dv:ticket` and `dv:groom` both read this file.
- **`dv:groom` step 7**: an edit-list item whose text names a ticket the ticket is not yet related
  to says so ("and relates VIL-N"). If David declines a relation, no saved text may name that
  ticket's id.
- **`dv:groom` step 8**: the report reads the ticket again with relations included. It reports
  relations as they now stand, and names any that Linear added from an id in the text.

Refs VIL-813.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
