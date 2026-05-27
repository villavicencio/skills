# villavicencio/skills

Personal [Agent Skills](https://agentskills.io/specification) library, distributed as a [Claude Code plugin marketplace](https://github.com/anthropics/claude-plugins-official). Each plugin bundles a related set of skills that release together with a single version.

[![validate](https://github.com/villavicencio/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/villavicencio/skills/actions/workflows/validate.yml)

## Plugins

| Plugin | Version | Skills | Description |
| --- | --- | --- | --- |
| [`pickup-handoff`](plugins/pickup-handoff/) | `0.1.0` | `pickup`, `handoff` | Session-bracket companions for Claude Code. `/pickup` hydrates context at session start; `/handoff` serializes session state at the end. |
| [`tmux-window-namer`](plugins/tmux-window-namer/) | `0.1.1` | `tmux-window-namer` | Style tmux windows with a glyph, title, and palette color, persisted across server restarts. Depends on dotfiles-installed tmux scripts + a `client-attached` hook; preflight-checks and bails cleanly when absent. |
| [`review-claudemd`](plugins/review-claudemd/) | `0.1.0` | `review-claudemd` | Mine recent conversation history to improve `CLAUDE.md` — surface violated rules, missing patterns (scoped local vs global), and stale entries, then apply approved changes. Requires `jq`. |

## Install

The same flow works for any Claude Code instance — your Mac, a remote VPS session, anywhere `claude` is installed.

```bash
# One-time: register this repo as a plugin marketplace
claude plugins marketplace add villavicencio/skills

# Install a plugin from this marketplace
claude plugins install pickup-handoff@villavicencio-skills
```

To update later:

```bash
claude plugins update pickup-handoff
```

To uninstall:

```bash
claude plugins uninstall pickup-handoff
```

### Installing `tmux-window-namer` (project-scoped)

`tmux-window-namer` depends on tmux persistence infrastructure that lives in a dotfiles repo (two scripts plus a `client-attached` hook — a plugin can't ship those). It's therefore meant to be installed **project-scoped** to that repo, so it only appears in the picker when you're working there:

```bash
# One-time per machine: register the marketplace
# (defaults to --scope user; add --scope project to scope it to dotfiles too)
claude plugin marketplace add villavicencio/skills

# From inside the dotfiles repo, install project-scoped
claude plugin install tmux-window-namer@villavicencio-skills --scope project
```

The project-scoped enablement is written to `.claude/settings.json` and can be committed to the dotfiles repo so it travels across machines.

> **Fresh-machine note.** A committed `.claude/settings.json` *declares* the enablement but does **not** auto-fetch the plugin. On a machine where the marketplace was never registered, the one-time `marketplace add` + `install --scope project` above is still required before the committed enablement takes effect. If the persistence scripts and hook aren't present, the skill preflight-checks, reports what's missing, and stops without touching any window.

### Migrating from a single-file setup

If you previously had `pickup.md` or `handoff.md` at `~/.claude/commands/` (either as direct files or as symlinks into a dotfiles repo), **remove them after installing the plugin** — otherwise the picker will keep showing both the old and new entries.

The reason is subtle: Claude Code discovers user commands by globbing `~/.claude/commands/*.md`, and the glob matches on filename, not on whether the file actually resolves. A symlink whose target was renamed or deleted still satisfies the glob, so the picker keeps offering an entry that errors when invoked.

```bash
# Remove the old single-file commands (or symlinks) if they exist
rm -f ~/.claude/commands/pickup.md ~/.claude/commands/handoff.md
```

If your old files lived in a dotfiles repo and you want a rollback window, rename them to `.md.deprecated` in dotfiles *and* delete the symlinks at `~/.claude/commands/` — the symlinks themselves aren't load-bearing for rollback, only the source files are.

### Linux Claude Code instances with older git

`claude plugins marketplace add <owner/repo>` may fail with `ERR_STREAM_PREMATURE_CLOSE` on Linux Claude Code running git ≤ 2.43. This is an upstream `claude` CLI bug; track [issue #8](https://github.com/villavicencio/skills/issues/8) for the fix. Workaround until then:

```bash
git clone --depth 1 https://github.com/villavicencio/skills.git ~/.local/share/villavicencio-skills
claude plugins marketplace add ~/.local/share/villavicencio-skills
claude plugins install pickup-handoff@villavicencio-skills
```

Updates on those instances need an extra step:

```bash
git -C ~/.local/share/villavicencio-skills pull
claude plugins marketplace update villavicencio-skills
claude plugins update pickup-handoff
```

## Versioning

- Each plugin carries its own `version` in `.claude-plugin/plugin.json`, following [semantic versioning](https://semver.org/).
- Every skill inside a plugin shares the plugin's version via `metadata.version` in its `SKILL.md` frontmatter. CI enforces this — a skill version that drifts from its plugin's version fails the build.
- Release tags use the form `<plugin-name>--v<semver>` (double-dash) per the Claude Code plugin convention. v0.1.0 of `pickup-handoff` ships as `pickup-handoff--v0.1.0`.

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
