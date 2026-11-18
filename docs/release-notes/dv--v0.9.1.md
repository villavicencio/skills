# dv — v0.9.1

Patch release. It changes the line `dv:manager-mode` suggests a project put in its `CLAUDE.md` or
`AGENTS.md`: the line gains a second sentence, and the sentence after it says "two sentences" instead
of "that line". The other ten skills have no behaviour changes; their version moves
to `0.9.1` only because the suite is released as one plugin.

`0.9.0` was merged but never tagged or published as a GitHub release, so this is the first release
since `0.8.0`. It also carries `0.9.0`'s breaking change, `dv:gauntlet`'s removal (see below).

## Changed

### `dv:manager-mode`: the suggested standing line is stronger

The skill suggested this line for a project that wants the mode on in every session:

> At the start of every session, invoke `dv:manager-mode`.

It now suggests:

> At the start of every session, invoke `dv:manager-mode`. Do it before your first reply, whatever the first message asks; don't ask first.

Why: on 2026-11-17 a fresh headless Sonnet session got a neutral question as its first message in a
repository whose `CLAUDE.md` had only the old line. It quoted the line and did not invoke the skill.
With the second sentence added, it invoked the skill (one run each, so this is a single observation,
not a measured rate).

The skill's behaviour once invoked is unchanged. A project that already has the old line keeps
working as before; to get the stronger wording it copies the new line over the old one.

## Also in this release, from 0.9.0

### Removed: `dv:gauntlet`, PR #63 (VIL-799)

**Breaking change:** anything that invokes `dv:gauntlet` no longer has a skill to run. That covers
prompts, scripts and other skills that name it, and `dv:gauntlet report`.

MergeWren is the PR reviewer, with no stand-in. The rules live in the dotfiles repo,
`docs/agents/code-review.md`, and are not repeated here. Release notes for earlier versions that
mention `dv:gauntlet` are left as written.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
