# dv — v0.9.0

Minor release, and a breaking one. It removes one skill, `dv:gauntlet`. The other eleven skills have
no behaviour changes; their version moves to `0.9.0` only because the suite is released as one plugin.

## Removed

### `dv:gauntlet`, PR #63 (VIL-799)

**Breaking change:** anything that invokes `dv:gauntlet` no longer has a skill to run. That covers
prompts, scripts and other skills that name it, and `dv:gauntlet report`.

MergeWren is the PR reviewer, with no stand-in. The rules live in the dotfiles repo,
`docs/agents/code-review.md`, and are not repeated here.

Release notes for earlier versions that mention `dv:gauntlet` are left as written.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
