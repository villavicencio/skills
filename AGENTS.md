# villavicencio/skills

Personal Agent Skills library, spec-conformant per `agentskills.io/specification`,
distributed as a Claude Code plugin marketplace. Originating plan:

  /Users/dvillavicencio/Projects/openclaw/docs/plans/2026-05-22-001-feat-skills-library-foundation-plan.md

Source requirements doc (Proof):
  https://www.proofeditor.ai/d/7bcoylxb?token=60d0bd1b-17ba-42fb-abaa-78ac0603efca

**Scope shift (2026-05-23):** v0.1.0 pivoted to the plugin marketplace layout
(`.claude-plugin/marketplace.json` + `plugins/<name>/`) instead of the original
symlink-install model. The plan's "v0.2+ tripwire" for plugin distribution was
pulled forward. Hermes-side install via `hermes skills tap add` was dropped
entirely — Mac-style session-bracket /pickup-handoff is an anti-pattern for
persistent agents, and Atlas already has its own runtime-correct variant via
the openclaw canonicals/ deploy. v0.1.0 ships for Claude Code only (Mac +
Axiom). Multi-runtime support (`.codex-plugin/`, `.cursor-plugin/` siblings)
is deferred to v0.2+ if/when the need surfaces.

## Workflow
- Branch-first for substantive work; small doc/typo updates may commit directly to main
- Each plugin release ideally lands as one PR
- CI gates (`.github/workflows/validate.yml`):
  - `agentskills validate plugins/*/skills/*` — spec conformance per skill
  - Per-plugin skill-version-parity — skills in the same plugin must share a version
  - plugin.json ↔ skill version-parity — plugin manifest version must match skills'

## Conventions
- Push to main is NOT pre-authorized on this repo — confirm before `git push origin main`
- All file paths in docs are repo-relative
- Apache-2.0 root LICENSE; no per-skill LICENSE/CHANGELOG in v0.1.0
- Release tag format: `<plugin-name>--v<semver>` (double-dash, per `claude plugin tag` convention)
- AGENTS.md is the canonical project-instructions file; CLAUDE.md is a thin pointer kept for older Claude Code tooling that hasn't migrated

## Install (canonical procedure)
```bash
# Register this repo as a marketplace (one-time per Claude Code instance)
claude plugins marketplace add villavicencio/skills

# Install a plugin from the marketplace
claude plugins install pickup-handoff@villavicencio-skills
```
