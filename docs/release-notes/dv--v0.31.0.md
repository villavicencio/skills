# dv — v0.31.0

Minor release. The rules for what a ticket waits on now live once, in a new "Prerequisites"
section of the shared rules file (`plugins/dv/skills/ticket/references/ticket-format.md`) that
`dv:ticket` and `dv:groom` both read. Each skill keeps a pointer and only what is its own. The
rules say the same as `dv:ticket`'s copy did; `dv:groom` gains the parts its copy lacked. The other
fourteen skills have no behaviour changes; their version moves to `0.31.0` only because the suite
is released as one plugin.

Numbering: 0.31.0 follows 0.30.0, which made `dv:groom` add the `groomed` label when grooming
leaves a ticket ready, and 0.29.0, which made `dv:ticket` set Linear's blocked-by relation when a
filed ticket waits on another.

Why: since 0.29.0 the two skills' copies disagreed in two places. `dv:groom` read a PR with a bare
`gh pr view` and listed none of the unclear cases `dv:ticket` asks about, so grooming could set a
blocked-by that filing would refuse. And `dv:groom` gave a spin-off `relatedTo` the groomed ticket
and `blockedBy` any open ticket its pull condition names, so a spin-off that waits on the groomed
ticket named it in both, which Linear refuses ("Two issues can have only one relation") (VIL-966).

## Changed

- **Shared rules, new "Prerequisites" section.** Find, check, tell a prerequisite from a reference,
  map and ask, moved from `dv:ticket` File step 4 without changing what they say:
  - **Check** reads a PR with `gh pr view <N> -R <owner>/<repo> --json state,mergedAt,headRefName,body`.
  - **Unclear cases** go to a question with no relation set: a prerequisite ticket that is
    Canceled or a Duplicate, a PR closed without merging, an open PR whose ticket is Done,
    Canceled or a Duplicate, a state that can't be read, and a wait that maps to no issue or to
    more than one.
  - **One relation per pair.** Linear allows one relation between two issues, so a ticket that is
    blocked by another is not also set as related to it. `blockedBy` wins. An id in the ticket's
    text adds no second relation: a save that sets `blockedBy` to an issue the text names sets
    only the blocked-by, and adding `blockedBy` to a ticket already related to that issue
    replaces the related link (both seen in Linear on 2026-11-24).
- **`dv:ticket`, File step 4, "Prerequisites".** Points to the shared section. It keeps the draft
  (a met prerequisite is named, a related ticket is listed and linked in step 7, "Blocked by
  VIL-N"), asking before the draft is shown (also under "Filing without my confirmation"), and the
  Backlog fallback when the answer names no issue. The sentences that called the unclear cases
  File mode's own and asked the reader to keep two copies alike are gone.
- **`dv:ticket`, "Filing without my confirmation".** The "unless step 4 makes it a Blocked by"
  rule for the source ticket now points to the one-relation rule.
- **`dv:groom`, steps 1 and 3, "Prerequisites".** Step 1 finds waits with the shared signs. Step 3
  applies the shared section, so it now reads a PR's merge state with the full command and treats
  the unclear cases as open decisions. It keeps its own add and remove items for relations.
- **`dv:groom`, forks-only.** The fork for a prerequisite now covers every case the shared rules
  send to a question, not only one that maps to no issue or to several.
- **`dv:groom`, step 7, "Order of writes" item 2.** A spin-off gets `relatedTo` the groomed ticket
  unless it is blocked by it, so a spin-off that waits on the groomed ticket files with
  `blockedBy` alone.
- **"Before anything else" in both skills.** The list of what the shared file holds names the
  prerequisite and relation rules.
- **Output evals.** `tooling/evals/run_output_evals.py` injects a skill's `references/*.md` after
  its `SKILL.md` body in the with-skill run, so `dv:ticket`'s evals still see the rules they test,
  which now live in the shared file. Only `dv:ticket` has both evals and a `references/` directory.
- **README.** The `dv:ticket` and `dv:groom` entries describe the same prerequisite rules, and the
  plugin table shows `0.31.0`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
