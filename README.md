# villavicencio/skills

Personal [Agent Skills](https://agentskills.io/specification) library, distributed as a [Claude Code plugin marketplace](https://github.com/anthropics/claude-plugins-official). The whole suite ships as one plugin — `dv` — whose skills release together under a single version.

[![validate](https://github.com/villavicencio/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/villavicencio/skills/actions/workflows/validate.yml)

## The `dv` plugin

One plugin, invoked `dv:<skill>` — modeled on how `compound-engineering` holds its whole `ce-*` family under a single namespace and version.

| Plugin | Version | Skills | Description |
| --- | --- | --- | --- |
| [`dv`](plugins/dv/) | `0.2.1` | `pickup`, `handoff`, `review-claudemd`, `tmux-window-namer`, `reddit`, `twitter`, `critique`, `cite`, `gauntlet` | Personal skill suite. Session brackets (`dv:pickup` / `dv:handoff`), `CLAUDE.md` hygiene (`dv:review-claudemd`), tmux styling (`dv:tmux-window-namer`), Reddit / X fetchers (`dv:reddit` / `dv:twitter`), parallel plan critique (`dv:critique`), a re-fetch-or-decline freshness contract for realtime facts (`dv:cite`), and a staged adversarial code-review loop (`dv:gauntlet`). |

### Skills at a glance

- **`dv:pickup`** — read `HANDOFF.md` and orient: surface git/PR state and recent compound-engineering artifacts, then propose a next action. Use at session start.
- **`dv:handoff`** — write a `HANDOFF.md` serializing the session (what shipped, decisions, what's next, gotchas). Pairs with `dv:pickup`.
- **`dv:review-claudemd`** — mine recent conversation history to improve `CLAUDE.md`: surface violated rules, missing patterns, and stale entries, then apply approved changes. Requires `jq`.
- **`dv:tmux-window-namer`** — style tmux windows with a glyph, title, and palette color. Depends on dotfiles-installed tmux persistence infra; preflight-checks and bails cleanly when absent (so it simply no-ops outside that repo).
- **`dv:reddit`** — fetch and summarize a Reddit post with comments via the public `.json` API (curl + jq, no auth). WebFetch can't reach reddit.com.
- **`dv:twitter`** — fetch and summarize an X/Twitter post (and long-form Articles) via the public `api.fxtwitter.com` endpoint (no auth). WebFetch can't reach x.com.
- **`dv:critique`** — stress-test a plan with three parallel critique subagents (Skeptic / Simplifier / Historian), then synthesize a revised plan.
- **`dv:cite`** — for realtime-fact queries, re-fetch the source and either ground the quote with a URL + timestamp or decline with a typed reason. Freshness is the trigger; ground-or-decline is the point.
- **`dv:gauntlet`** — run a code change through a staged, cost-tiered adversarial review loop (find → refute → fix → verify) driven to convergence. Bare invocation fixes and commits on your current feature branch across a bounded round budget, presenting only at the terminal; `report` gives a single report-only round that never touches your tree. Uses the Codex CLI for cross-provider review when present, self-contained Claude subagents otherwise.

## Install

The same flow works for any Claude Code instance — your Mac, a remote VPS session, anywhere `claude` is installed.

```bash
# One-time: register this repo as a plugin marketplace
claude plugin marketplace add villavicencio/skills

# Install the suite
claude plugin install dv@villavicencio-skills
```

To update later:

```bash
# The marketplace clone is not auto-fetched — refresh it first
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The update target must be **fully qualified**: bare `claude plugin update dv` reports "not found". An update applies on the next session restart.

To uninstall:

```bash
claude plugin uninstall dv
```

> **`dv:tmux-window-namer` note.** This skill depends on tmux persistence infrastructure that lives in a dotfiles repo (two scripts plus a `client-attached` hook — a plugin can't ship those). It ships inside the user-scoped `dv` suite, so it's present everywhere, but it preflight-checks for that infra and **bails cleanly when it's absent** — outside the dotfiles repo it simply does nothing. No separate project-scoped install is needed.

### Migrating from a single-file setup

If you previously ran any of these as single-file commands at `~/.claude/commands/*.md` (e.g. `pickup`, `handoff`, `reddit`, `twitter`, `critique`) or as a standalone skill under `~/.claude/skills/` (e.g. the former `verify-cite`, now `dv:cite`), **remove the old copies after installing the plugin** — otherwise the picker keeps showing both the old and new entries.

The reason is subtle: Claude Code discovers user commands by globbing `~/.claude/commands/*.md`, and the glob matches on filename, not on whether the file actually resolves. A symlink whose target was renamed or deleted still satisfies the glob, so the picker keeps offering an entry that errors when invoked.

```bash
# Remove the old single-file commands (or symlinks) if they exist
rm -f ~/.claude/commands/{pickup,handoff,reddit,twitter,critique}.md

# Then inspect the old skill before touching it — a real directory and a
# symlink need different treatment (e.g. the former verify-cite → dv:cite)
ls -ld ~/.claude/skills/verify-cite
```

If your old files lived in a dotfiles repo and you want a rollback window, rename them to `.md.deprecated` in dotfiles *and* delete the symlinks at `~/.claude/commands/` — the symlinks themselves aren't load-bearing for rollback, only the source files are.

The same applies to skills, and **the destination matters**: a directory set aside inside `~/.claude` is outside version control, so the rollback window it was meant to provide never actually existed — and it will sit there unnoticed indefinitely. Where it goes depends on what `ls -ld` just told you.

**If it's a real directory**, move it into a dotfiles checkout you already have. Substitute your own path — don't let `mkdir -p` invent one, or you've just built a fresh untracked orphan and solved nothing. The `rev-parse` guard makes the whole chain a no-op unless the target really is a repo:

```bash
DOTFILES=~/path/to/your/dotfiles          # substitute; this default is not real

git -C "$DOTFILES" rev-parse --git-dir >/dev/null 2>&1 &&
  mkdir -p "$DOTFILES/claude/skills/.deprecated" &&
  mv ~/.claude/skills/verify-cite "$DOTFILES/claude/skills/.deprecated/" &&
  git -C "$DOTFILES" add claude/skills/.deprecated/verify-cite

# Staging is not archiving. Review, then commit — until you do, the copy
# exists only in your index: absent from history, and from every clone.
git -C "$DOTFILES" status
git -C "$DOTFILES" commit -m "chore(claude): retire verify-cite (superseded by dv:cite)"
```

**If it's a symlink**, moving it accomplishes nothing: you relocate a pointer — breaking it outright if the link is relative — while the real source and whatever installs it both survive to recreate the duplicate on the next bootstrap. Retire it at the source instead, which takes all three of: delete the live symlink, remove the declaration that recreates it (the `install.conf.yaml` entry, if you use dotbot), and `git mv` the tracked source to a `.deprecated` name inside the repo. Miss the middle step and the next `./install` puts the duplicate right back.

If you don't keep a dotfiles repo at all, delete the old directory outright — a copy you can't restore from isn't a backup.

### Linux Claude Code instances with older git

`claude plugin marketplace add <owner/repo>` may fail with `ERR_STREAM_PREMATURE_CLOSE` on Linux Claude Code running git ≤ 2.43. This is an upstream `claude` CLI bug; track [issue #8](https://github.com/villavicencio/skills/issues/8) for the fix. Workaround until then:

```bash
git clone --depth 1 https://github.com/villavicencio/skills.git ~/.local/share/villavicencio-skills
claude plugin marketplace add ~/.local/share/villavicencio-skills
claude plugin install dv@villavicencio-skills
```

Updates on those instances need an extra step:

```bash
git -C ~/.local/share/villavicencio-skills pull
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

## Versioning

- The plugin carries its `version` in `.claude-plugin/plugin.json`, following [semantic versioning](https://semver.org/).
- Every skill in the plugin shares that version via `metadata.version` in its `SKILL.md` frontmatter. CI enforces this — a skill version that drifts from the plugin's version fails the build. (One suite, one version: a fix to any skill bumps the whole plugin.)
- Release tags use the form `<plugin-name>--v<semver>` (double-dash) per the Claude Code plugin convention. v0.1.0 of `dv` ships as `dv--v0.1.0`.

## Spec conformance

Every PR and every push to `main` runs:

- `agentskills validate` against each skill directory under `plugins/*/skills/*` ([Agent Skills spec](https://agentskills.io/specification)).
- A per-plugin skill-version-parity check (skills in the same plugin must share `metadata.version`).
- A plugin-manifest-↔-skill-version-parity check (each plugin's `plugin.json` version must match the skill versions inside).

The marketplace manifest (`.claude-plugin/marketplace.json`) and each plugin manifest (`.claude-plugin/plugin.json`) can also be validated locally with `claude plugin validate <path>`.

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json              # marketplace declaration
├── plugins/
│   └── <plugin-name>/
│       ├── .claude-plugin/
│       │   └── plugin.json           # plugin manifest
│       └── skills/
│           └── <skill-name>/
│               ├── SKILL.md          # spec-conformant skill
│               └── references/       # optional progressive-disclosure assets
├── .github/workflows/validate.yml    # CI gates
└── README.md
```

## License

[Apache-2.0](LICENSE).
