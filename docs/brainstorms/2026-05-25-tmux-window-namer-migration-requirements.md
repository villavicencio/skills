---
date: 2026-05-25
topic: tmux-window-namer-migration
---

# tmux-window-namer Marketplace Migration

## Summary

Migrate the `tmux-window-namer` skill into the `villavicencio/skills` marketplace as a standalone, project-scoped plugin, so the marketplace becomes a complete inventory of the user's skills. The skill content moves in; its tmux persistence scripts and `client-attached` hook stay in dotfiles (a plugin can't install them), and the skill preflight-checks for that dependency and bails cleanly when it's missing.

---

## Problem Frame

`villavicencio/skills` shipped its first plugin (`pickup-handoff--v0.1.0`) and is intended to be the single place the user manages and discovers their skills. But `tmux-window-namer` currently lives only in the dotfiles repo (`claude/skills/tmux-window-namer/`, symlinked into `~/.claude/skills/`). Any skill that lives only in dotfiles is invisible to the marketplace inventory — the user has to remember it exists and where it is. As more skills accumulate, that blind spot grows.

`tmux-window-namer` is harder to migrate than `pickup-handoff` was: it's not self-contained. It's a thin orchestration layer over dotfiles-installed infrastructure — two persistence shell scripts and a tmux `client-attached` hook that restores per-window glyph/color metadata from a JSON sidecar across server restarts. A plugin cannot ship a tmux hook or install those scripts. So migrating the skill necessarily means accepting that the plugin depends on dotfiles infrastructure being present — and an inventory that lists a skill which silently half-works without that infrastructure would mislead.

---

## Requirements

**Packaging**
- R1. `tmux-window-namer` ships as a standalone plugin in the `villavicencio/skills` marketplace — not bundled with other skills.
- R2. The plugin contains the skill's `SKILL.md` and its two reference files; plugin version `0.1.0`; released independently as tag `tmux-window-namer--v0.1.0` (decoupled from `pickup-handoff`'s version).

**Infrastructure boundary**
- R3. The tmux persistence scripts and `client-attached` hook remain in dotfiles. The plugin does not attempt to ship, install, or reference them by a plugin-relative path.

**Dependency honesty**
- R4. The skill preflight-checks for its dotfiles-installed dependency before applying any window styling.
- R5. When the dependency is absent, the skill stops and explains what's missing, rather than applying state the hook can never restore.

**Installation**
- R6. The plugin installs project-scoped to the dotfiles repo, not user-scope — it should only appear in the picker when working in dotfiles.
- R7. The project-scope enablement is committed to the dotfiles repo so it travels with that repo across machines.

---

## Acceptance Examples

- AE1. **Covers R4, R5.** Given the dotfiles tmux scripts and hook are NOT installed (e.g., a fresh machine, or installed project-scoped somewhere that isn't dotfiles), when the skill is invoked, it reports the missing dependency and stops without modifying any tmux window state.
- AE2. **Covers R4.** Given the dependency IS present, when the skill is invoked, it proceeds with the normal name / glyph / color flow unchanged from the current dotfiles behavior.
- AE3. **Covers R6.** Given the plugin is installed project-scoped to dotfiles, when the user opens a Claude Code session in an unrelated project, `tmux-window-namer` does not appear in that project's picker.

---

## Success Criteria

- The marketplace inventory includes `tmux-window-namer`; no skill the user actively uses lives only in dotfiles outside the marketplace index.
- Invoking the skill without the dotfiles infrastructure fails safe — clear message, no orphaned sidecar/window state — rather than silently half-working.
- Behavior with the infrastructure present is identical to the current dotfiles skill (no regression in the name/glyph/color flow).
- `ce-plan` can execute the migration without re-deciding the A/B/C boundary, the plugin grain, or the dependency-handling strategy — all settled here.

---

## Scope Boundaries

- **Not** bundling into a `dotfiles-tools` plugin now — deferred until a second dotfiles-native skill appears (same tripwire pattern v0.1.0 used for the marketplace decision).
- **Not** moving the persistence scripts or hook into the plugin (the rejected "option B" — a hook referencing a versioned cache path that changes every release is brittle).
- **Not** keeping the skill dotfiles-native / unmigrated (the rejected "option C" — perpetuates the inventory blind spot this work exists to close).
- **Not** making the skill runtime-independent of dotfiles — impossible; plugins can't install tmux hooks.
- **Not** migrating other dotfiles-local commands (e.g., `ticket.md`) in this work — they're separate decisions.

---

## Key Decisions

- **Direction A (skill → plugin; scripts + hook stay in dotfiles) over B and C.** The "single inventory" motivation makes C a non-starter. B's versioned-cache-path hook reference is brittle. A accepts the dotfiles coupling permanently and honestly. Rationale: the value being bought is inventory completeness, not self-containment — so the design optimizes for "in the marketplace + honest about its dependency," not "runs anywhere."
- **Preflight-self-check-and-bail over document-only dependency declaration.** The moment-of-invocation is where silent half-working actually happens; a runtime check protects that layer. Plugin metadata stays minimal (a one-line dependency mention in the description is optional polish, not required).
- **Standalone plugin grain over a bundle.** One skill doesn't justify a `dotfiles-tools` bundle (YAGNI). Revisit grain when the second dotfiles-native skill arrives.

---

## Dependencies / Assumptions

- Depends on dotfiles continuing to install the tmux persistence scripts (`tmux/scripts/save-window-meta.sh`, `restore-window-meta.sh`) and the `client-attached` hook (`tmux/tmux.general.conf`). Verified present in the dotfiles repo as of 2026-05-25.
- Assumes a project-scoped plugin enablement can be committed to the dotfiles repo and travels with it. This is the standard Claude Code `--scope project` mechanism; exact declaration file to be confirmed during planning.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R4][Technical] Exact preflight check — what to test for (presence of the persistence scripts, registration of the `client-attached` hook, or both) and how to probe it portably.
- [Affects R2][Technical] `allowed-tools` frontmatter — the current skill declares it. Confirm `agentskills validate` accepts the key and decide whether to keep it as-is or refine the tool list.
- [Affects R3][Technical] Whether the skill's hardcoded `$HOME/.config/tmux` script path stays hardcoded or becomes configurable via the plugin's `userConfig` mechanism.
- [Affects R7][Needs research] Whether project-scoped enablement committed to dotfiles auto-fetches the plugin into the user cache on a fresh machine, or whether an explicit `claude plugins install` is still required first.
