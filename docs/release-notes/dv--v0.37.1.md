# dv — v0.37.1

Patch release. `dv:groom`'s story-points table no longer ties the 8 row to the number of repos,
and a stale note about team VIL's scale is dropped. The other fifteen skills have no behaviour
changes; their version moves to `0.37.1` only because the suite is released as one plugin.

Why: the 8 row read "a change that touches several modules or two repos", so a trivial change in
two repos was pointed at 8. Since 2026-11-24 team VIL's Linear scale stores 13 as 13, so the
"13 stored as 8 (team VIL, 2026-11-23)" example no longer holds.

## Changed

- **`dv:groom`, story-points table.** The 8 row now reads "a large change across several modules,
  with a lot of work in many files". A sentence after the table says points follow the amount of
  work, not the number of repos or PRs, and that needing PRs in more than one repo that can
  merge on their own is a split signal (see "Split verdict", which is unchanged).
- **`dv:groom`, read-back of the estimate.** The sentence keeps the general point that a team whose
  scale stops at 8 stores 13 as 8, and no longer names team VIL as one. The comparison and the
  clearing steps are unchanged.
- **README.** The version.
