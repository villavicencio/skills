# pickup-handoff — v0.1.0 (Foundation Release)

The first release of `villavicencio/skills`. Ships the `pickup-handoff` plugin — a pair of session-bracket skills for Claude Code — and establishes the repo's plugin-marketplace shape that future plugins will follow.

## What's in v0.1.0

The `pickup-handoff` plugin packages two skills that pair end-to-end:

- **`/pickup`** — reads `HANDOFF.md` at the repo root, surfaces in-flight context (open PRs, branch state, recent compound-engineering artifacts when those conventions exist), and proposes a concrete next action. Used at the start of a Claude Code session to get oriented within a minute.
- **`/handoff`** — writes a structured `HANDOFF.md` capturing what was built this session, decisions made, what's next, and gotchas. Used at the end of a session so the next `/pickup` (yours or someone else's) can resume cold.

Both skills come from years of single-file `~/.claude/commands/{pickup,handoff}.md` use in personal dotfiles; v0.1.0 promotes them to spec-conformant Agent Skills, versions them properly, and distributes them via the standard Claude Code plugin marketplace mechanism.

## Install

```bash
# Register this repo as a marketplace (one-time per Claude Code instance)
claude plugins marketplace add villavicencio/skills

# Install the plugin
claude plugins install pickup-handoff@villavicencio-skills
```

On Linux Claude Code instances running older git (≤ 2.43), `marketplace add <owner/repo>` may fail with `ERR_STREAM_PREMATURE_CLOSE` due to an upstream CLI bug. Use the local-path workaround documented in [issue #8](https://github.com/villavicencio/skills/issues/8) until the upstream fix lands.

## Changelog

This is the initial release. Highlights from the build:

- **Spec-conformant skills** validated against `agentskills.io/specification` via the canonical PyPI `skills-ref==0.1.1` reference CLI (binary: `agentskills`). CI runs `agentskills validate` on every PR.
- **Plugin-marketplace distribution.** Repo declares a `.claude-plugin/marketplace.json` at root and ships `pickup-handoff` as a plugin under `plugins/pickup-handoff/`. The original v0.1.0 plan called for a symlink-install model; the plugin path was pulled forward from the v0.2+ tripwire after it became clear it was the right primitive for cross-instance install (Mac + Axiom both consume via the same `claude plugins install` command).
- **CI guardrails** — three checks gate every PR: per-skill spec validation, per-plugin skill-version-parity (skills inside a plugin must share `metadata.version`), and plugin.json↔skill version parity.
- **Portability hardening** during the v0.1.0 polish: dropped a hardcoded `~/.config/nvm/versions/node/v24.13.0/bin` PATH prepend, gated `gh` calls on `command -v`, gated git calls on `git rev-parse --git-dir`, auto-detected the default branch (instead of hardcoding `main`), and gated the compound-engineering artifact scan on directory existence so the skill is a clean no-op on non-CE projects.
- **Scope cleanup** — removed the original Step 2c VPS health snapshot from `/pickup`. It didn't belong in a session-bracket skill and coupled `/pickup` to a specific personal runtime. A dedicated `vps-health` skill is planned as a follow-up ([issue #7](https://github.com/villavicencio/skills/issues/7)).

## Known limitations

- **Linux git-clone bug** affects fresh installs on older Linux Claude Code instances. Workaround in [issue #8](https://github.com/villavicencio/skills/issues/8); will be tested against newer git versions before being closed.
- **Mac + Axiom (Linux Claude Code) only.** No `.codex-plugin/` or `.cursor-plugin/` siblings yet — multi-runtime distribution is deferred to v0.2+ if/when the need surfaces.
- **`/pickup` and `/handoff` are session-bracket tools** and assume a session model (cold start → work → serialize → end). They are not appropriate for persistent agents like Hermes-Atlas, which has its own runtime-correct equivalents via the openclaw `canonicals/` deploy. v0.1.0 intentionally ships for Claude Code only.

## Next planned release

`v0.2.0` is unscoped. Candidates from the foundation work:

- **`vps-health`** skill carved out of the original `/pickup` Step 2c — own plugin or part of an `openclaw-ops` bundle ([issue #7](https://github.com/villavicencio/skills/issues/7)).
- **Multi-runtime distribution** — `.codex-plugin/` + `.cursor-plugin/` siblings, if and when those runtimes become primary consumers.

## Acknowledgements

- Anthropic's [Agent Skills spec](https://agentskills.io/specification) and the [`skills-ref`](https://pypi.org/project/skills-ref/) reference CLI authored by Keith Lazuka.
- The Claude Code plugin marketplace conventions documented by [`anthropics/skills`](https://github.com/anthropics/skills) and demonstrated in practice by [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin).
