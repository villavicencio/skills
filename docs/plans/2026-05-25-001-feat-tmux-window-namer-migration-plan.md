---
title: "feat: Migrate tmux-window-namer into the marketplace as a standalone plugin"
type: feat
status: completed
date: 2026-05-25
origin: docs/brainstorms/2026-05-25-tmux-window-namer-migration-requirements.md
---

# feat: Migrate tmux-window-namer into the marketplace as a standalone plugin

## Summary

Add `tmux-window-namer` as a standalone plugin under `plugins/`, mirroring the existing `pickup-handoff` layout. The SKILL.md and its two reference files are ported faithfully with two corrections (frontmatter normalization + XDG-aware path resolution), then a graded preflight dependency-guard is added on top so the skill fails honestly when its dotfiles-installed persistence infrastructure is absent. The persistence scripts and `client-attached` hook stay in dotfiles permanently.

---

## Problem Frame

`tmux-window-namer` currently lives only in the dotfiles repo (`claude/skills/tmux-window-namer/`), invisible to the marketplace inventory this repo exists to be. Unlike `pickup-handoff`, it is not self-contained: it is a thin orchestration layer over dotfiles-installed infrastructure — two persistence shell scripts plus a tmux `client-attached` hook that restores per-window glyph/color metadata from a JSON sidecar across server restarts. A plugin cannot ship a tmux hook or install those scripts, so migrating the skill means accepting a permanent dotfiles dependency — and listing a skill that silently half-works without that infrastructure would make the inventory lie. See origin for full framing: `docs/brainstorms/2026-05-25-tmux-window-namer-migration-requirements.md`.

---

## Requirements

- R1. `tmux-window-namer` ships as a standalone plugin in the marketplace — not bundled.
- R2. The plugin contains the skill's `SKILL.md` and its two reference files; plugin version `0.1.0`; released as tag `tmux-window-namer--v0.1.0`, decoupled from `pickup-handoff`'s version.
- R3. The tmux persistence scripts and `client-attached` hook remain in dotfiles. The plugin does not ship, install, or reference them by a plugin-relative path.
- R4. The skill preflight-checks for its dotfiles-installed dependency before applying any window styling.
- R5. When the dependency is absent, the skill stops and explains what's missing, rather than applying state the hook can never restore.
- R6. The plugin installs project-scoped to the dotfiles repo, not user-scope — it appears in the picker only when working in dotfiles.
- R7. The project-scope enablement is committed to the dotfiles repo so it travels across machines.

**Origin acceptance examples:** AE1 (covers R4, R5 — deps absent → report + stop, no state change), AE2 (covers R4 — deps present → normal flow unchanged), AE3 (covers R6 — project-scoped → absent from unrelated projects' pickers).

---

## Scope Boundaries

- **Not** bundling into a `dotfiles-tools` plugin now — deferred until a second dotfiles-native skill appears.
- **Not** moving the persistence scripts or hook into the plugin (rejected "option B" — a hook referencing a versioned cache path that changes every release is brittle).
- **Not** keeping the skill dotfiles-native / unmigrated (rejected "option C" — perpetuates the inventory blind spot).
- **Not** making the skill runtime-independent of dotfiles — impossible; plugins can't install tmux hooks.
- **Not** migrating other dotfiles-local commands (e.g., `ticket.md`).
- **Not** building an automated test harness for skill *prose* behavior — AE1/AE2/AE3 are verified manually; CI covers structural validation only.

### Deferred to Follow-Up Work

- **Dotfiles-side enablement commit (R6, R7)** — lands in the dotfiles repo, not this one. Captured as U5 with `**Target repo:** dotfiles` so the procedure is concrete, but it is a separate commit/PR in a separate repo.
- **Release tagging** (`tmux-window-namer--v0.1.0`) — a git tag operation performed at release time after the migration PR merges; see Operational / Rollout Notes.

---

## Context & Research

### Relevant Code and Patterns

- `plugins/pickup-handoff/.claude-plugin/plugin.json` — plugin manifest shape to mirror (name, version, author, homepage, repository, license, keywords).
- `plugins/pickup-handoff/skills/pickup/SKILL.md` frontmatter — house style for migrated skills: `name`, `description`, `license: Apache-2.0`, `metadata.author: villavicencio`, `metadata.version: "0.1.0"`. Note: neither pickup nor handoff declares `allowed-tools`.
- `.claude-plugin/marketplace.json` — `plugins[]` array; each entry has `name`, `description`, `author`, `homepage`, `repository`, `license`, `tags`, `source` (`./plugins/<name>`).
- `.github/workflows/validate.yml` — globs `plugins/*/skills/*/`, so the new skill is validated automatically; per-plugin and plugin.json↔skill version-parity checks apply to the new plugin independently.
- `docs/release-notes/pickup-handoff--v0.1.0.md` — release-notes doc shape.
- Source skill: `~/Projects/Personal/dotfiles/claude/skills/tmux-window-namer/` (`SKILL.md`, `references/glyphs.md`, `references/palettes.md`).

### Institutional Learnings

- `docs/solutions/` is currently empty — no prior learnings to carry forward.
- From the v0.1.0 README: a skill that lives only in dotfiles is an inventory blind spot; the marketplace is meant to be the single index.

### External References

- **agentskills.io spec** — `allowed-tools` (hyphenated) is a recognized top-level optional frontmatter key, marked *Experimental*, with a **space-separated** value. The current source skill uses a **comma-separated** value, which diverges from the spec form.
- **Validator acceptance — verified.** `agentskills validate` (skills-ref 0.1.1, the exact version CI pins) was run in an isolated venv during planning (by the feasibility reviewer): it returns exit 0 for a top-level `allowed-tools` key in space-separated, comma-separated, *and* absent forms, and `read-properties` correctly surfaces `metadata.version` for the parity gates. The validator additionally enforces `directory-name == skill-name`, which the planned path `plugins/tmux-window-namer/skills/tmux-window-namer/` satisfies. The CI risk does not materialize; the comma→space conversion is cosmetic spec alignment, not a CI requirement.
- **Claude Code plugin enablement (CLI 2.1.150, verified via `--help`)** — project-scoped enablement lives in `.claude/settings.json` under `extraKnownMarketplaces` (registers the marketplace source) and `enabledPlugins` (`"<plugin>@<marketplace>": true`). The load-bearing caveat: committing these to a repo **declares** intent but does **not** trigger any fetch on a fresh machine — the marketplace must be `add`-ed and the plugin `install`-ed once by an explicit command before enablement takes effect. `claude plugin marketplace add` defaults to `--scope user` but accepts `--scope project|local` (so the marketplace registration itself can also be declared project-scoped to dotfiles, not only user-global). `claude plugin install -s project` fetches into cache *and* writes `enabledPlugins`; `claude plugin enable -s project` toggles an already-installed plugin.

---

## Key Technical Decisions

- **Graded preflight check (chosen with user):** Hard-bail when the persistence scripts are absent (the skill calls `save-window-meta.sh` directly and cannot complete without it → satisfies AE1). When the scripts exist but the `client-attached` hook is not detected, warn that styling applies now but won't survive a tmux server restart until the hook is active, then proceed. Rationale: a false-negative hook probe (detection is tmux-version-sensitive) must not brick a skill whose infra is actually fine; warning keeps the half-working state from being *silent*, which is the actual failure mode the origin's "lying inventory" principle targets. AE1's scenarios (fresh machine, or installed somewhere that isn't dotfiles) are all scripts-absent states, so the graded design is fully AE1-compliant.
- **XDG-aware path, not `userConfig`:** Resolve the script path as `${XDG_CONFIG_HOME:-$HOME/.config}/tmux/scripts/...`, matching the dotfiles scripts' and hook's own convention, and fixing the source skill's latent `$HOME/.config`-only assumption. Chosen over a `userConfig` mechanism (YAGNI — the path is deterministic from XDG conventions the one consuming environment already follows; `userConfig` adds a per-install surface the user would have to populate). Keeps R3 satisfied: the path points at the dotfiles-installed location, never a plugin-relative path.
- **`allowed-tools` kept top-level (validator-verified):** Keep `allowed-tools` as a top-level key (spec-canonical, honored by Claude Code for tool restriction) and convert its value to space-separated form. Validated against skills-ref 0.1.1 during planning — it passes (see Context & Research). The fallback ladder (relocate under `metadata`, or drop) is retained as belt-and-suspenders but is provably unnecessary.
- **R7 is portable enablement, not zero-touch install:** Committing `extraKnownMarketplaces` + `enabledPlugins` to dotfiles makes enablement declarative and portable, but a fresh machine needs a one-time `marketplace add` + `install --scope project`. Documented as an accepted operational caveat.
- **Standalone plugin grain** (carried from origin) — one skill does not justify a `dotfiles-tools` bundle.
- **Independent versioning** — `0.1.0` / tag `tmux-window-namer--v0.1.0`, decoupled from `pickup-handoff`; CI's per-plugin parity check keeps it isolated.

---

## Open Questions

### Resolved During Planning

- **(a) Preflight shape & portability:** Test for both — scripts (hard gate) and hook registration (warn gate), per the graded decision above. Probe portability (`show-hooks` vs `show-options -g`, how `client-attached` renders) is tmux-version-sensitive; target is tmux `next-3.7` where `show-hooks` is available. Exact probe command deferred to implementation (see below).
- **(b) `allowed-tools`:** Recognized top-level spec key (Experimental), space-separated value. Keep top-level — **empirically verified** to pass skills-ref 0.1.1 (the CI-pinned validator) during planning. See Context & Research and Key Technical Decisions.
- **(c) Hardcoded path vs `userConfig`:** XDG-aware path resolution, not `userConfig`. See Key Technical Decisions.
- **(d) Fresh-machine auto-fetch:** No auto-fetch — committed project settings declare intent; one-time manual bootstrap required. See Context & Research and Operational Notes.

### Deferred to Implementation

- **Exact tmux hook-probe command** — verify the precise form that reliably detects the `client-attached` hook referencing `restore-window-meta.sh` against tmux `next-3.7` on the target machine (`show-hooks -g client-attached` vs `show-options -g | grep client-attached`). A false negative degrades to a warning only, so the cost of getting the exact form wrong is bounded. **Note:** the dotfiles hook resolves the restore script via bare `$XDG_CONFIG_HOME` (no `:-$HOME/.config` fallback), while the skill's preflight uses `${XDG_CONFIG_HOME:-$HOME/.config}`. On the target machine `XDG_CONFIG_HOME` is set so both resolve identically; if it were ever unset they would diverge — keep the probe tolerant of this.
- *(Resolved — no longer deferred.)* `allowed-tools` validator acceptance was confirmed empirically during planning (skills-ref 0.1.1, isolated venv). Moved to Context & Research / Resolved During Planning.

---

## Output Structure

    plugins/tmux-window-namer/
    ├── .claude-plugin/
    │   └── plugin.json
    └── skills/
        └── tmux-window-namer/
            ├── SKILL.md
            └── references/
                ├── glyphs.md
                └── palettes.md

---

## Implementation Units

### U1. Scaffold the plugin and register it in the marketplace

**Goal:** Create the plugin manifest and add the marketplace entry so the new plugin is discoverable and CI-validated.

**Requirements:** R1, R2

**Dependencies:** None

**Files:**
- Create: `plugins/tmux-window-namer/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

**Approach:**
- Mirror `plugins/pickup-handoff/.claude-plugin/plugin.json`: `name: tmux-window-namer`, `version: "0.1.0"`, author/homepage/repository/license matching the existing plugin, keywords drawn from the skill's domain (tmux, window styling, glyphs, palettes, claude-code, agent-skills).
- Append a `plugins[]` entry in `marketplace.json` with `source: "./plugins/tmux-window-namer"`, a description that states the skill's purpose and may optionally note the dotfiles dependency, and matching tags.
- Marketplace `metadata.version` stays `0.1.0` (marketplace-level, not plugin-level — unchanged by adding a plugin).

**Patterns to follow:**
- `plugins/pickup-handoff/.claude-plugin/plugin.json` and the existing `pickup-handoff` entry in `.claude-plugin/marketplace.json`.

**Test scenarios:**
- Test expectation: none (config/scaffolding) — validated by CI: `claude plugin validate` on the manifests, and the plugin.json↔skill version-parity gate (will pass only once U2 lands the skill at `0.1.0`).

**Verification:**
- `plugin.json` parses and carries `version: "0.1.0"`; `marketplace.json` lists the new plugin with a `source` pointing at the new directory.

---

### U2. Port the skill content with frontmatter normalization and the XDG path fix

**Goal:** Move `SKILL.md` + the two reference files into the plugin, faithfully preserving behavior, with frontmatter aligned to house style and the script path corrected — no new behavior yet.

**Requirements:** R2, R3

**Dependencies:** U1

**Files:**
- Create: `plugins/tmux-window-namer/skills/tmux-window-namer/SKILL.md`
- Create: `plugins/tmux-window-namer/skills/tmux-window-namer/references/glyphs.md`
- Create: `plugins/tmux-window-namer/skills/tmux-window-namer/references/palettes.md`

**Approach:**
- Copy the source skill verbatim, then apply exactly two corrections:
  1. **Frontmatter:** add `license: Apache-2.0`, `metadata.author: villavicencio`, `metadata.version: "0.1.0"` (matching pickup/handoff). Keep `name` and `description` from source. Keep `allowed-tools` as a top-level key but convert its value to space-separated form (spec-canonical).
  2. **Path:** replace the hardcoded `$HOME/.config/tmux/scripts/save-window-meta.sh` reference in Step 5 with the XDG-aware `${XDG_CONFIG_HOME:-$HOME/.config}/tmux/scripts/save-window-meta.sh`, matching the dotfiles scripts' own convention.
- Reference files (`glyphs.md`, `palettes.md`) copy unchanged.
- Preserve the load-bearing PUA-stripping guidance and the `\uXXXX`-escape examples exactly — do not let any editor round-trip resolve the escape sequences into rendered glyphs (the source SKILL.md warns about this explicitly).

**Patterns to follow:**
- `plugins/pickup-handoff/skills/pickup/SKILL.md` frontmatter block.

**Test scenarios:**
- Test expectation: none for behavior (faithful port) — validated by CI: `agentskills validate plugins/tmux-window-namer/skills/tmux-window-namer/` passes, and per-plugin + plugin.json↔skill version-parity pass at `0.1.0`.
- Manual check (behavioral parity, AE2): with the dotfiles infra present, the name/glyph/color flow behaves identically to the current dotfiles skill (no regression).

**Verification:**
- The three files exist under the plugin; `agentskills validate` passes; the only diffs from the source are the frontmatter additions, the `allowed-tools` value reformat, and the XDG path.

---

### U3. Add the graded preflight dependency-guard

**Goal:** Add the new dependency-honesty behavior — preflight-check-and-bail (graded) — so the skill refuses to apply un-restorable state and warns when persistence-on-restart isn't guaranteed.

**Requirements:** R4, R5

**Dependencies:** U2

**Files:**
- Modify: `plugins/tmux-window-namer/skills/tmux-window-namer/SKILL.md`

**Approach:**
- Add an early preflight step (before any window mutation — i.e., before Suggest/Direct/Tweak modes apply or persist anything) that:
  1. **Hard gate:** verifies `save-window-meta.sh` and `restore-window-meta.sh` exist and are executable at `${XDG_CONFIG_HOME:-$HOME/.config}/tmux/scripts/`. If either is missing → report exactly what's missing and stop, modifying no tmux window state (AE1).
  2. **Warn gate:** probes whether the `client-attached` hook is registered referencing the restore script. If not detected → emit a warning that styling will apply this session but won't survive a tmux server restart until the hook is active, then proceed.
- Frame the preflight as instructions to the agent (this is a prose skill), describing the checks and the two outcomes, not a committed shell script. The exact hook-probe command is deferred to implementation (see Open Questions).
- The hard gate runs before the existing "outside tmux → exit" check or alongside it — both are fail-fast guards; ordering should put the cheapest deterministic check first.

**Technical design** *(directional guidance for review, not implementation spec):*

    preflight (runs before any mutation):
      scripts present & executable?  ── no ──▶ report missing dep, STOP (no state change)   [AE1]
             │ yes
             ▼
      client-attached hook → restore script detected?
             │ no  ──▶ WARN "applies now, won't survive restart until hook active", continue
             │ yes
             ▼
      proceed to Suggest / Direct / Tweak  [AE2]

**Patterns to follow:**
- The source skill's existing "If the user runs this outside tmux, say so and exit" guard — same fail-fast posture, extended to the dependency check.

**Test scenarios:**
<!-- Skill is markdown instructions; "tests" are manual behavioral verifications against the AEs. -->
- Covers AE1. Manual — **scripts absent** (rename/move the dotfiles `scripts/` dir, or run on a machine without dotfiles): invoke the skill → it names the missing dependency and stops; `tmux show-options -wv @win_glyph` on the target window is unchanged and no `window-meta.json` entry is written.
- Covers AE1. Manual — **plugin present but scripts absent** (the "installed somewhere that isn't dotfiles" case): same outcome — report + stop, no state change.
- Covers AE2. Manual — **scripts present, hook present**: invoke → no warning, normal name/glyph/color flow proceeds and persists.
- Manual — **scripts present, hook absent** (comment out the `client-attached` line and reload tmux config): invoke → warning is shown, styling still applies to the live window and writes to the sidecar; skill does not hard-stop.
- Manual — **hook-probe false negative tolerance**: confirm that if the probe fails to detect a hook that is actually present, the only consequence is a spurious warning, never a refusal.

**Verification:**
- With infra absent, the skill stops cleanly and leaves no orphaned window/sidecar state (AE1). With infra present, behavior is unchanged from U2 (AE2). With scripts-but-no-hook, the user is warned and the skill still works for the current session.

---

### U4. Update README and add release notes

**Goal:** Reflect the new plugin in user-facing docs.

**Requirements:** R1, R2

**Dependencies:** U1, U2, U3

**Files:**
- Modify: `README.md`
- Create: `docs/release-notes/tmux-window-namer--v0.1.0.md`

**Approach:**
- Add a `tmux-window-namer` row to the README **Plugins** table (version `0.1.0`, skill name, description).
- Add an install snippet for the plugin under the **Install** section — and, because this plugin is intended to be project-scoped to dotfiles, document the project-scope install (`claude plugin install tmux-window-namer@villavicencio-skills --scope project` from within the dotfiles repo) and the one-time fresh-machine bootstrap caveat (marketplace must be `add`-ed first; committed settings declare but don't auto-fetch).
- Write `docs/release-notes/tmux-window-namer--v0.1.0.md` mirroring the `pickup-handoff--v0.1.0.md` shape: what shipped, the dotfiles-dependency note, and the install/bootstrap procedure.
- SUITES.md needs no change (it defers to README for the canonical plugin table).

**Patterns to follow:**
- `docs/release-notes/pickup-handoff--v0.1.0.md`; the existing README Plugins table and Install section.

**Test scenarios:**
- Test expectation: none (documentation) — verified by review.

**Verification:**
- README table lists both plugins; install + bootstrap procedure for the project-scoped plugin is present and accurate; release-notes doc exists.

---

### U5. Install project-scoped to dotfiles and commit enablement

**Goal:** Make the plugin available only in the dotfiles project and commit that enablement so it travels.

**Target repo:** dotfiles (`~/Projects/Personal/dotfiles`) — separate repo; paths below are dotfiles-relative.

**Requirements:** R6, R7

**Dependencies:** U1–U4 merged and the `tmux-window-namer--v0.1.0` tag released (so the marketplace serves the plugin).

**Files:**
- Create or modify: `.claude/settings.json` (in the dotfiles repo)

**Approach:**
- One-time per machine: `claude plugin marketplace add villavicencio/skills` (defaults to `--scope user`; can be `--scope project` to scope the marketplace registration to dotfiles too). Required even with committed settings — committed config never auto-fetches.
- From within the dotfiles repo: `claude plugin install tmux-window-namer@villavicencio-skills --scope project` — fetches into cache and writes the project-scoped enablement.
- Commit the resulting `.claude/settings.json` (`extraKnownMarketplaces` registering `villavicencio-skills`, `enabledPlugins` with `"tmux-window-namer@villavicencio-skills": true`) to the dotfiles repo so enablement travels.
- Note the accepted limitation in dotfiles' own docs/README if appropriate: a fresh clone still needs the one-time `marketplace add` + `install --scope project` before the committed enablement does anything.

**Patterns to follow:**
- The Claude Code project-scope mechanism documented in Context & Research.

**Test scenarios:**
- Covers AE3. Manual — open a Claude Code session in an **unrelated** project: `tmux-window-namer` does **not** appear in that project's picker.
- Manual — open a session in the **dotfiles** project: the skill appears and is invokable.
- Manual (fresh-machine caveat) — on a machine where the marketplace was never added, confirm the committed settings alone do **not** make the plugin available until `marketplace add` + `install --scope project` are run once.

**Verification:**
- The skill is enabled only in dotfiles; `.claude/settings.json` enablement is committed; the bootstrap caveat is understood/documented.

---

## System-Wide Impact

- **CI parity (this repo):** `.github/workflows/validate.yml` globs `plugins/*/skills/*/`, so the new skill is validated and version-parity-checked automatically and independently of `pickup-handoff`. No workflow change needed.
- **Marketplace surface:** Adding a `plugins[]` entry is additive; existing `pickup-handoff` install/update flows are unaffected.
- **Unchanged invariants:** `pickup-handoff` plugin, its version, and the marketplace `metadata.version` (`0.1.0`) are untouched. The dotfiles tmux scripts and `client-attached` hook are unchanged — the plugin only reads/depends on them.
- **Cross-repo:** U5 mutates a *different* repo (dotfiles). No code in this repo depends on it; it is the install step that realizes R6/R7.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| ~~`agentskills validate` rejects top-level `allowed-tools` → CI red~~ — **retired:** verified to pass skills-ref 0.1.1 during planning | Fallback ladder (relocate under `metadata`, or drop) retained as belt-and-suspenders, but the risk is closed. |
| tmux hook-probe is version-sensitive and may false-negative | Graded design makes a false negative degrade to a *warning only*, never a refusal. Exact probe form verified at implementation against tmux `next-3.7`. |
| `XDG_CONFIG_HOME` set to a non-default location | Path uses `${XDG_CONFIG_HOME:-$HOME/.config}`, matching the scripts and hook — resolves correctly in both cases (and fixes the source skill's latent `$HOME/.config`-only bug). |
| PUA-escape examples mis-transcribed during the port (editor resolves `\uXXXX` into a rendered glyph) | U2 explicitly preserves the escape sequences verbatim; the source SKILL.md's own `xxd` self-check guidance is retained for the implementer. |
| Fresh-machine expectation that committed settings auto-install | Documented as an accepted caveat in README/release notes (U4) and the dotfiles step (U5): one-time `marketplace add` + `install --scope project` required. |

---

## Documentation / Operational Notes

- **Release tagging:** After the migration PR merges to `main`, create the `tmux-window-namer--v0.1.0` tag (double-dash convention, per AGENTS.md / `claude plugin tag`). This is the gate that makes the marketplace serve the plugin for U5's install.
- **Branch + PR:** Push to `main` is NOT pre-authorized (AGENTS.md) — this lands as a branch + PR + squash-merge. The untracked origin requirements doc (`docs/brainstorms/2026-05-25-tmux-window-namer-migration-requirements.md`) should be committed alongside (or just before) this work so the plan has a tracked source.
- **Fresh-machine bootstrap (R7 caveat):** committed `.claude/settings.json` declares enablement but does not auto-fetch; document the one-time `claude plugin marketplace add villavicencio/skills` + `claude plugin install tmux-window-namer@villavicencio-skills --scope project`.

---

## Sources & References

- **Origin document:** [docs/brainstorms/2026-05-25-tmux-window-namer-migration-requirements.md](docs/brainstorms/2026-05-25-tmux-window-namer-migration-requirements.md)
- Existing plugin pattern: `plugins/pickup-handoff/`, `.claude-plugin/marketplace.json`, `.github/workflows/validate.yml`
- Source skill: `~/Projects/Personal/dotfiles/claude/skills/tmux-window-namer/`; dotfiles infra: `tmux/scripts/{save,restore}-window-meta.sh`, `client-attached` hook in `tmux/tmux.general.conf`
- agentskills spec: https://agentskills.io/specification (`allowed-tools` — Experimental, space-separated, top-level)
- Claude Code plugin enablement: `.claude/settings.json` `extraKnownMarketplaces` + `enabledPlugins`; CLI 2.1.150 `plugin install/enable -s project`, `marketplace add` (user-global)
