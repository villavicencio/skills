# tmux-window-namer — v0.1.0

The second plugin in `villavicencio/skills`. Migrates the `tmux-window-namer` skill out of personal dotfiles and into the marketplace, so the marketplace becomes a complete inventory of the skills in active use — with one honest caveat about a dependency that can't move.

## What's in v0.1.0

The `tmux-window-namer` plugin packages a single skill:

- **`tmux-window-namer`** — styles a tmux window with a glyph, a title, and a palette-drawn glyph color. Three modes: **Suggest** (predict the window's context, offer live-previewed variations, apply the pick), **Direct** (a fully-specified request applies immediately), and **Tweak** (change only what's asked on already-styled windows). Result persists across tmux server restarts via a JSON sidecar.

Unlike `pickup-handoff`, this skill is **not self-contained**. It is a thin orchestration layer over infrastructure that lives in the dotfiles repo — two persistence scripts (`save-window-meta.sh`, `restore-window-meta.sh`) and a tmux `client-attached` hook that restores per-window metadata from the sidecar. A plugin cannot ship a tmux hook or install those scripts, so the dependency on dotfiles is permanent and intentional.

To keep the inventory honest, the skill runs a **graded preflight check** before touching any window:

- **Persistence scripts absent** → it stops, reports exactly what's missing, and modifies no window state.
- **Scripts present but the `client-attached` hook isn't detected** → it warns that styling applies now but won't survive a tmux server restart, then proceeds.
- **Scripts and hook both present** → it proceeds normally.

This prevents the skill from silently half-working (applying styling that nothing can restore) while staying robust to version-sensitive hook detection — a false negative degrades to a warning, never a refusal.

## Install

This plugin is intended to be scoped to the **dotfiles** project (its dependency only exists there), so install it project-scoped rather than user-wide:

```bash
# One-time per machine: register the marketplace (defaults to user scope;
# add --scope project to scope the registration to dotfiles too)
claude plugin marketplace add villavicencio/skills

# From inside the dotfiles repo, install project-scoped
claude plugin install tmux-window-namer@villavicencio-skills --scope project
```

The project-scoped enablement is written to `.claude/settings.json` and can be committed to the dotfiles repo so it travels.

> **Fresh-machine note.** Committed `.claude/settings.json` enablement *declares* intent but does not auto-fetch. On a machine where the marketplace has never been registered, the one-time `marketplace add` + `install --scope project` above is still required before the committed enablement does anything.

## Changelog

This is the initial release of the plugin (skill migrated from dotfiles):

- **Faithful migration.** `SKILL.md` and both reference files (`references/glyphs.md`, `references/palettes.md`) move in byte-for-byte; the reference files contain Nerd Font private-use-area glyphs that are preserved exactly. Behavior with the dotfiles infrastructure present is identical to the pre-migration skill.
- **Two corrections during the port:** house-style frontmatter (`license`, `metadata.author`, `metadata.version`) added to match the marketplace's other skills, and the `save-window-meta.sh` path made XDG-aware (`${XDG_CONFIG_HOME:-$HOME/.config}`) to match the dotfiles scripts' own convention — fixing a latent `$HOME/.config`-only assumption.
- **`allowed-tools` dropped.** The dotfiles original carried a parameterized allowlist (`Bash(tmux *)`, etc.) that omitted commands the core apply/persist path needs (`python3` for PUA-safe glyph writes, `bash` for the persistence script) and could not reliably cover the skill's compound commands and heredocs. Rather than maintain a fragile, incomplete allowlist, the migrated skill declares no `allowed-tools` and runs under the session's normal permission flow — matching `pickup-handoff`'s skills.
- **Graded preflight dependency-guard** added (the one behavioral addition over the dotfiles original).
- **CI parity for free.** The validate workflow globs `plugins/*/skills/*`, so this skill is spec-validated and version-parity-checked independently of `pickup-handoff`, with its own version gate.

## Known limitations

- **Permanent dotfiles dependency.** The persistence scripts and `client-attached` hook stay in dotfiles by design; the plugin is honest about it but cannot remove it. On any environment without that infrastructure, the skill fails safe rather than working.
- **Hook detection is best-effort.** The `client-attached` probe is tmux-version-sensitive; a false negative produces a spurious "won't survive restart" warning but never blocks the skill.
- **Scoped to dotfiles.** Installed project-scoped, the skill appears in the picker only when working in the dotfiles project — by design.

## Versioning

Released independently of `pickup-handoff` as tag `tmux-window-namer--v0.1.0`. Plugin and skill share `metadata.version: 0.1.0`; CI enforces the parity.

## Acknowledgements

- Anthropic's [Agent Skills spec](https://agentskills.io/specification) and the [`skills-ref`](https://pypi.org/project/skills-ref/) reference CLI.
- Nerd Fonts for the glyph set the skill draws from, and the One Dark palette the curated colors harmonize with.
