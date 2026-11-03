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

## Where the working copy lives
Since 2026-10-21 the working copy is on hal, as the `david` account: `/Users/david/Projects/skills`,
Orca project `skills` on the `hal-svc` environment. The Mac checkout is archived, so do the work
there. Installing the plugin (below) still pulls from GitHub on every machine and needs no local
checkout.

## Workflow
- Branch-first for substantive work; small doc/typo updates may commit directly to main
- Each plugin release ideally lands as one PR
- **PR review: MergeWren (review-stack) is the gate, since 2026-11-03.** It reviews every new
  head of a non-draft PR here on its own (onboarded with posting on, VIL-540); there is no
  trigger and no quota, so pushing a fix starts the next round. Wait for its verdict with
  `mergewren_review <N>` from dotfiles `bin/lib/mergewren-review.sh`; the procedure is
  "Merging on a MergeWren review" in dotfiles `docs/agents/code-review.md`. Fix each finding
  or decline it with the reason on the thread and in the PR body, resolve the threads, and
  merge with the unresolved-threads check empty. **Don't request CodeRabbit here**:
  `@coderabbitai review` spends the per-developer quota that other repos still use, and a
  CodeRabbit check or comment that shows up anyway is informational. (`.coderabbit.yaml` sets
  `auto_review.enabled: false`, so CodeRabbit reviews only when asked.)
  Repo-specific: **`validate` going green is not the merge signal** (it is the spec/parity
  gate, not a review). Why the switch: CodeRabbit's free plan allows 1 review an hour shared
  across every repo, and on #56 it found nothing actionable while MergeWren found two real bugs.
  (History: 2026-08-24, #33 merged on `validate` 52 s before CodeRabbit posted four valid
  findings; that is the origin of the global "never merge on a green CI gate" rule.)
- Validating a skill locally before pushing: `python3` on the Mac is Xcode's 3.9 but
  `skills-ref==0.1.1` requires **≥3.11**, so `pip install skills-ref` fails with "no matching
  distribution". Use `uv venv --python 3.11 <dir> && uv pip install --python <dir>/bin/python
  'skills-ref==0.1.1'`, then `<dir>/bin/agentskills validate plugins/dv/skills/<name>`.
  **In an Orca worktree this is already done:** `orca.yaml`'s setup script builds `.venv`
  (Python 3.12, matching CI), so run `.venv/bin/agentskills validate plugins/dv/skills/<name>`.
  The script copies no files. Orca itself copies the gitignored files `.worktreeinclude`
  names (`.compound-engineering/config.local.yaml`, `.claude/settings.local.json`; not
  `HANDOFF.md`) before setup runs. It reads `.worktreeinclude` from the main checkout, takes
  literal paths only (it skips any line with `*`, `?` or a leading `!`), and copies a path only
  if it exists there and this repo ignores it, so list each file literally and ignore it in
  `.gitignore`. Keep anything that changes state other checkouts depend on out of the script
  (uv's shared cache is fine); `dv:orca-setup` covers how to change it.
- CI gates (`.github/workflows/validate.yml`):
  - `agentskills validate plugins/*/skills/*` — spec conformance per skill
  - `tooling/check_skill_placeholders.py` — no `$` followed by a digit in any SKILL.md: Claude Code replaces `$0`, `$1`, ... with the words typed after the skill command, code blocks included (VIL-517). Write awk's `$0` as `$(0)`, don't use shell `$1`, write prices as `USD 350`
  - Per-plugin skill-version-parity — skills in the same plugin must share a version
  - plugin.json ↔ skill version-parity — plugin manifest version must match skills'

## Conventions
- Push to main is NOT pre-authorized on this repo — confirm before `git push origin main`
- All file paths in docs are repo-relative
- Apache-2.0 root LICENSE; no per-skill LICENSE/CHANGELOG in v0.1.0
- Release tag format: `<plugin-name>--v<semver>` (double-dash, per `claude plugin tag` convention)
- AGENTS.md is the canonical project-instructions file; CLAUDE.md is a thin pointer kept for older Claude Code tooling that hasn't migrated
- **`HANDOFF.md` is gitignored in this repo** — it is local-only session state, never committed. `dv:handoff`'s auto-commit step is therefore a no-op here (expected, not a failure), and the file can silently drift from reality between sessions, so treat `git`/`gh` state as the source of truth over a stale handoff
- **Issue tracking lives in the Linear project `Argus — Skills & Agent Infrastructure`** (renamed from `Skills`; same project, workspace `Villavicencio`, team `VIL`; https://linear.app/villavicencio/project/skills-47ce141de4bc) as of 2026-08-24. Tools resolve it by its current name or id `P-VIL-5`, not by the old name. Don't open new GitHub issues here. Mark the Linear issue Done at merge time
- `docs/solutions/` — documented solutions to past problems (bugs, best practices, workflow patterns), organized by category with YAML frontmatter (`module`, `tags`, `problem_type`). Relevant when implementing or debugging in a documented area
- `CONCEPTS.md` — shared domain vocabulary (entities, named processes, status concepts) with project-specific meaning. Relevant when orienting to the repo or discussing domain concepts

## Install (canonical procedure)
```bash
# Register this repo as a marketplace (one-time per Claude Code instance)
claude plugin marketplace add villavicencio/skills

# Install the plugin from the marketplace
claude plugin install dv@villavicencio-skills

# Update after a release (both steps; the marketplace clone is not auto-fetched)
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

`dv` is the only plugin — all skills were consolidated into it (PR #16). The
per-skill plugins (`pickup-handoff`, `tmux-window-namer`, `review-claudemd`) no
longer exist as install targets. Note the update command needs the **fully
qualified** `dv@villavicencio-skills`; bare `claude plugin update dv` reports
"not found". A plugin update applies on the next session restart.

## Vault

This project owns the Obsidian vault `~/Obsidian/skills/` (per-agent-vault standard,
2026-07-15). It holds durable cross-session notes plus the live agent memory
(`memory/` — the harness memory dir symlinks there). Manage it as this project sees
fit; read other vaults when helpful, write to them only when asked.
