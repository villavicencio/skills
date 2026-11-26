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
- **Releases publish themselves (VIL-809).** `.github/workflows/release.yml` runs after
  `validate` passes on a push to `main`: for each plugin whose `plugin.json` version has no
  GitHub release yet, it creates the tag `<plugin>--v<version>` at that push's commit, publishes
  the release with `docs/release-notes/<plugin>--v<version>.md` as its notes, and starts
  `validate` on the tag. If `validate` didn't pass, the run fails naming the commit and the
  `validate` run, and nothing is released. A person still does three things: bump the version
  (plugin.json and every skill's `metadata.version`), write that notes file, and merge. Bump
  only when the change ships in a plugin (anything under `plugins/<plugin>/`). A change only to
  `tooling/`, `.github/` or `docs/` ships in no plugin, so it gets no bump and no notes file
  (skills PR 117, VIL-924). Don't tag or create a release by hand for a version the workflow will release; that races it.
  Logic and rules are in `tooling/release_plugins.py` (unit tests:
  `python3 tooling/test_release_plugins.py`, which both jobs run first). Its checks run before
  it creates anything; any of these fails the run with nothing tagged or released: a directory
  under `plugins/` without a readable `.claude-plugin/plugin.json`, a missing or empty notes
  file, a draft release on the tag, a malformed name or version, or a version below the
  plugin's highest release with no tag of its own. A tag with no release gets its release on
  that tag (`--verify-tag`, no `--target`, so the tag stays put); a version that already has a
  release is skipped. "Latest" goes only to a version above every earlier release of that
  plugin (with one plugin, that is the highest release).
  A run releases only the version in its own checkout's `plugin.json`, so a version gets no
  automatic release when it is replaced before a commit carrying it passes `validate`, or when
  two quick merges finish `validate` out of order and the newer version releases first (the
  older one is then refused as lower). To release such a version by hand, at a commit that
  carries it and passed `validate` (if none did, leave it unreleased), run from a checkout
  that has its notes file:
  `gh release create <plugin>--v<version> --repo villavicencio/skills --target <sha> --title "<plugin> v<version>" --notes-file docs/release-notes/<plugin>--v<version>.md --latest=false`
  If starting `validate` on the tag fails, the run fails and its error gives the
  `gh workflow run` command to start it by hand; a re-run will not retry it, since the release
  then exists. On a pull request the same workflow runs `release_plugins.py --dry-run` with a
  read-only token, so a release PR without its notes file fails before it merges; run that
  locally to see what a merge would publish.
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
- Live-checking a skill change before merge (VIL-908, 2026-11-22): in a throwaway clone of
  this repo, run `claude -p --plugin-dir <worktree>/plugins/dv --allowed-tools "Bash(git rev-parse:*)" -- "<prompt>"`.
  The branch's copy loads as `dv@inline` over the installed dv. The headless session needs
  every command the skill runs allowed with `--allowed-tools` (that check needed
  `git rev-parse`). Use a throwaway clone, not the main checkout, when the skill's behavior
  depends on which checkout it runs in. A skill whose fenced bash block is one compound command
  (`dv:closeout`'s Step 1 is one) is refused by the headless permission checker under a narrow
  `--allowed-tools` list (`Contains brace with quote character (expansion obfuscation)`;
  VIL-869, 2026-11-22): allow `Bash` in the throwaway clone (`--allowed-tools "Bash" -- "<prompt>"`) and say in the
  prompt which steps to skip. `--allowed-tools` takes every argument after it, so put the prompt after `--`.
- CI gates (`.github/workflows/validate.yml`):
  - `agentskills validate plugins/*/skills/*` — spec conformance per skill
  - `tooling/check_skill_placeholders.py` — no `$` followed by a digit in any SKILL.md: Claude Code replaces `$0`, `$1`, ... with the words typed after the skill command, code blocks included (VIL-517). Write awk's `$0` as `$(0)`, don't use shell `$1`, write prices as `USD 350`
  - Per-plugin skill-version-parity — skills in the same plugin must share a version
  - plugin.json ↔ skill version-parity — plugin manifest version must match skills'

## Conventions
- Head: Head of Skills, Orca address `bot:Head of Skills`, Linear handle `head-of-skills`. He runs this department for David, the CEO; `dv:director-mode`, `dv:manager-mode` and `dv:groom` (only in forks-only mode from a worktree session) route escalations to him as `dv:director-mode` ("The Head and the CEO's 1%") says, his answers advisory until verified Head decision delivery ships (VIL-1193), and `dv:closeout` follows in VIL-1191.
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
