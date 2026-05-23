# villavicencio/skills

Personal [Agent Skills](https://agentskills.io/specification) library, distributed as a [Claude Code plugin marketplace](https://github.com/anthropics/claude-plugins-official). Each plugin bundles a related set of skills that release together with a single version.

[![validate](https://github.com/villavicencio/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/villavicencio/skills/actions/workflows/validate.yml)

## Plugins

| Plugin | Version | Skills | Description |
| --- | --- | --- | --- |
| [`pickup-handoff`](plugins/pickup-handoff/) | `0.1.0` | `pickup`, `handoff` | Session-bracket companions for Claude Code. `/pickup` hydrates context at session start; `/handoff` serializes session state at the end. |

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
