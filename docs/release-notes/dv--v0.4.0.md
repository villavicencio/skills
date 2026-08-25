# dv — v0.4.0

Minor release. `dv:handoff` and `dv:pickup` — the pair that brackets a session — stop guessing at
freshness and start proving it. The handoff now writes a commit anchor, redacts before it writes,
and points at artifacts instead of restating them; pickup anchors staleness on that commit rather
than the file's age, and leads with whatever the handoff got wrong. No behavior changes to the
other eight skills — their version moves to `0.4.0` only because the suite releases at the plugin
grain.

Four adoptions from a review of the installed `ce-handoff` skill (2026-08-24). The verdict there
was that the dv ritual stays — repo-tracked, PR-reviewed, zero-question pickup — but that four of
`ce-handoff`'s ideas were worth taking piecemeal. `ce-handoff` remains installed and is the right
tool for cross-boundary transfers; these are complementary, not competing.

## What's new

### Commit-anchored handoffs (`dv:handoff` + `dv:pickup`)

`/handoff` writes YAML frontmatter above the header carrying `created_at` (ISO-8601 with offset),
`branch`, and `head` (short sha), copied verbatim from a new anchor block in Step 1. A new optional
argument, `/handoff focus: <text>`, records `resume_focus` — the one thing the next session should
pick up first.

`/pickup` parses that block and reports `git log <head>..HEAD`: "written at `<head>`; now at
`<sha>`, N commits since", plus the movers. It recognizes the handoff's own `docs: update handoff`
commit and does not count it as drift. Where the anchor is missing, unreachable, or not an ancestor
of HEAD — rebased, reset, squashed, or a different clone — it says so explicitly and falls back to
`created_at`, never reporting a misleading count. Pre-0.4.0 handoffs with no frontmatter keep
working on the old mtime heuristic, which now announces itself as such.

This replaces the wall-clock guessing that the global instructions carried a standing warning
about. Staleness is measured in commits.

### Drift leads the orientation (`dv:pickup`)

The handoff is now treated as untrusted context to verify, not truth to recite. Before summarizing,
`/pickup` cross-checks its load-bearing claims — open PRs, clean or dirty tree, branch, "nothing is
blocking" — against what it actually gathered, and any mismatch **leads** the output under
`Drift since handoff:`, naming claim versus reality.

Claims land in one of three buckets, and they are deliberately not interchangeable: verified match,
verified drift, and **unable to verify**. Absence of evidence is never reported as a match — `gh`
may be missing, there may be no remote, and even a successful `gh pr list` returns PR identity
only, saying nothing about pending review comments or blocked status. A clean-sounding match built
on data that was never gathered launders a stale handoff into a confirmed one, so the skill must
name what it could not check and why.

Explicitly **not** adopted: `ce-handoff`'s stop-and-ask-before-acting ceremony. Surface the drift
and proceed — the zero-question orient is what makes the skill worth invoking.

### Redaction pass before writing (`dv:handoff`)

`HANDOFF.md` is committed and pushed by the skill's own Notes step in most repos, so whatever the
draft contains leaves the machine. Step 2 now scans the draft for secrets, credentials, tokens,
internal hostnames and IPs, and personal information the next session does not need — and
**generalizes rather than deletes**: "the API key" not the key, keeping *which* credential rotated
and where it now lives.

The rule is explicit that the pre-commit scanner does not cover this. Gitleaks and friends match
token *shapes* in staged diffs; a credential described in prose, a hostname inside a pasted
command, or a name in a decisions bullet all pass straight through. Repos that gitignore
`HANDOFF.md` still get the pass — local-only today is not local-only forever.

### Pointer-first bodies (`dv:handoff`)

Handoffs run long by restating what git history and merged PRs already hold, and a restatement
drifts from its artifact the moment either changes — the handoff being the copy that goes stale.
Every bullet now names its artifact (PR number, `file:line`, doc path) plus one clause on what
matters *there*.

The carve-out matters as much as the rule: anything with no artifact to point at — a decision made
in conversation, a dead end that produced no commit, a gotcha found while debugging — still gets
written in full, because it exists nowhere else. That is most of "Decisions Made" and "Gotchas",
and a pointer-first rule applied blindly would gut them.

## Repo-level changes (not shipped in the plugin)

- **`dv:handoff` gained output evals.** `plugins/dv/skills/handoff/evals/evals.json` plants a
  credential value and a personal phone number among facts the next session genuinely needs, so it
  discriminates redaction from deletion in both directions. Since the paid behavioral job is
  unfunded by choice, the fixture is guarded offline instead: `tooling/evals/test_assertions.py`
  runs its real assertions against hand-written compliant and leaking responses on every push.
- **The prohibition tests were vacuous and are not any more.** Their leaking inputs also failed the
  positive matcher, so they passed whether or not the prohibitions did anything — deleting
  `must_not_match_any` entirely would not have failed the suite. Every case now starts from a
  response that *satisfies* the positive matcher, injects one leak, and asserts the positive
  matcher still passes. Verified by gutting the prohibitions and watching the suite go red.
- **`.coderabbit.yaml` added.** `auto_incremental_review: false` stops a review being spent on
  every intermediate push; re-review is requested deliberately. The review allowance is
  per-developer across all repos, so this is a fleet-level saving, not a repo-level one.
- **CodeRabbit procedure de-duplicated.** `AGENTS.md` now points at the Code Review section of the
  global instructions rather than restating it — three repos had drifted into disagreeing copies.

## Upgrading

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The marketplace clone is never auto-fetched, so the two-step order matters. An update applies on
the next session restart. Plugin installs are per-machine — every other install needs the same two
commands run there.
