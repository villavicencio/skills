# villavicencio/skills

Personal [Agent Skills](https://agentskills.io/specification) library — spec-conformant, versioned per-skill, with suite-grain releases when skills ship together.

[![validate](https://github.com/villavicencio/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/villavicencio/skills/actions/workflows/validate.yml)

## What's inside

| Skill | Description | Version | Suite |
| --- | --- | --- | --- |
| [`pickup`](skills/pickup/) | Pick up where you left off at the start of a new session — reads `HANDOFF.md`, surfaces in-flight context, proposes a next action. | `0.1.0` | `pickup-handoff` |
| [`handoff`](skills/handoff/) | Generate a session `HANDOFF.md` at the repo root capturing what was built, decisions, what's next, and gotchas. | `0.1.0` | `pickup-handoff` |

See [`SUITES.md`](SUITES.md) for the full suite manifest.

## Install — Claude Code

Clone the repo to a stable location — these examples use `~/Projects/skills`, substitute your own path if you prefer somewhere else:

```bash
git clone https://github.com/villavicencio/skills.git ~/Projects/skills
```

Then symlink each skill into `~/.claude/skills/`:

```bash
ln -s ~/Projects/skills/skills/pickup  ~/.claude/skills/pickup
ln -s ~/Projects/skills/skills/handoff ~/.claude/skills/handoff
```

Restart your Claude Code session if needed so it picks up the new directories. Invoke as `/pickup` and `/handoff`.

To update later, `git pull` in the clone — the symlinks resolve to the new content with no further action.

## Install — Hermes

Hermes has a first-class `skills` subcommand. Register this repo as a tap, then install individual skills:

```bash
hermes skills tap add villavicencio/skills
hermes skills install villavicencio/skills/pickup
hermes skills install villavicencio/skills/handoff
hermes skills list   # confirm both appear at version 0.1.0
```

The tap mechanism reads from this repo's `skills/` subdirectory, so the install identifier is `<owner>/<repo>/<skill>` rather than `<owner>/<repo>/skills/<skill>`. If you skip the tap and resolve directly, the path includes `skills/` (see plan U1 spike).

## Inventory programmatically

The reference CLI ships with `agentskills to-prompt`, which generates an `<available_skills>` XML block from a directory of skills — useful when wiring this library into other agent harnesses:

```bash
pip install 'skills-ref==0.1.1'
agentskills to-prompt skills/*
```

The PyPI package `skills-ref` installs a binary named `agentskills`. Do **not** substitute the same-named npm package — it is by a different author and explicitly demo-only.

## Versioning

- Each skill carries its own `metadata.version` in `SKILL.md` frontmatter, following [semantic versioning](https://semver.org/).
- Skills that always release together form a **suite**. Members of a suite must share the same `metadata.version`; CI enforces this (`.github/workflows/validate.yml`).
- Release tags use the form `<suite-or-skill>-v<semver>` — suite-grain (`pickup-handoff-v0.1.0`) when a suite exists, skill-grain otherwise.

## Spec conformance

Every PR and every push to `main` runs `agentskills validate` against every skill, plus a suite-version-parity check that fails when members of the same suite drift apart. See [`.github/workflows/validate.yml`](.github/workflows/validate.yml).

For the underlying spec, see [agentskills.io/specification](https://agentskills.io/specification).

## License

[Apache-2.0](LICENSE).
