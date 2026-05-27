# review-claudemd — v0.1.0

The third plugin in `villavicencio/skills`. Migrates the `/review-claudemd` command out of personal dotfiles and into the marketplace as a standalone, versioned skill.

## What's in v0.1.0

The `review-claudemd` plugin packages a single skill:

- **`review-claudemd`** — mines recent conversation history to keep `CLAUDE.md` honest. It extracts the project's session transcripts, fans out to parallel Sonnet subagents that compare what actually happened against both the global (`~/.claude/CLAUDE.md`) and local (`./CLAUDE.md`) instruction files, and surfaces four buckets: **rules that were violated** (need stronger wording), **missing LOCAL patterns**, **missing GLOBAL patterns**, and **stale entries**. Findings are presented for approval; only accepted changes are applied, and it never auto-commits.

Where `pickup`/`handoff` bracket a session and `tmux-window-namer` styles the terminal, `review-claudemd` is a **compounding loop**: lived experience in the transcripts becomes sharper standing instructions, instead of those lessons evaporating.

## Install

```bash
# One-time: register this repo as a plugin marketplace
claude plugin marketplace add villavicencio/skills

# Install the plugin
claude plugin install review-claudemd@villavicencio-skills
```

## Changelog

This is the initial release of the plugin (skill migrated from dotfiles **and hardened** — the port surfaced a latent correctness bug worth fixing before first publish):

- **Fixed a silent extraction bug (correctness).** The original `jq` did `"USER: " + .message.content`, which crashes on array-form message content (`string and array cannot be added`) and — with `2>/dev/null` — silently drops those records. Measured against a real transcript: **241 user records, only 27 extracted**, losing genuine user-typed messages (the exact signal the skill mines). The rewrite handles both `string` and array content, keeps user+assistant **text** while dropping `tool_result`/`tool_use`/`thinking` noise, and recovers the lost messages with zero errors.
- **Preflight + empty guards.** Bails cleanly when the project has no transcripts (or only the live session) instead of launching subagents on nothing; falls back to a basename search if the encoded project-dir path doesn't resolve.
- **Implements "skip the current session."** The original documented this in Notes but never did it; Step 2 now excludes the live transcript (avoids circular self-reference and half-written turns).
- **Safer scratch handling.** Extracted transcript text (which can contain secrets) now lands in a `mktemp -d` dir (mode `0700`, unpredictable name) with an explicit cleanup step, instead of a guessable world-readable `/tmp/claudemd-review-<epoch>`.
- **Sharper subagent prompt (signal quality).** Each finding must cite evidence (session + quote); new rules are proposed only when a pattern **recurs (≥2 instances)**; violations are diagnosed by cause (reword vs reinforce); already-captured patterns (existing `CLAUDE.md` / `MEMORY.md`) are skipped. Findings are de-duplicated and ranked by recurrence.
- **House-style frontmatter added.** The dotfiles original was a bare command with no frontmatter; the skill gains `name`, `description`, `license: Apache-2.0`, and `metadata.author` / `metadata.version` to match the marketplace's other skills and satisfy the spec.
- **No `allowed-tools`.** The skill launches subagents and issues many distinct Bash commands (`jq`, `ls`, `sed`, `mkdir`, `rm`, …) plus file reads/edits; a parameterized allowlist would be fragile and incomplete (the lesson from the `tmux-window-namer` port). It runs under the session's normal permission flow, matching `pickup-handoff`.
- **Genuinely portable.** Unlike the private-repo skills, this one has no personal coupling — its only dependency is `jq` plus Claude Code's own session transcripts, so it belongs in the public factory.
- **CI parity for free.** The validate workflow globs `plugins/*/skills/*`, so this skill is spec-validated and version-parity-checked independently, with its own version gate.

## Known limitations

- **Requires `jq`** (in the Brewfile) for transcript extraction.
- **Reads Claude Code session transcripts** at `~/.claude/projects/<project>/*.jsonl` — if a project has no recorded sessions yet, there's nothing to mine.
- **Subagent analysis is advisory.** It proposes `CLAUDE.md` edits; you decide what lands. By design it asks before editing and never commits.

## Versioning

Released independently of the other plugins as tag `review-claudemd--v0.1.0`. Plugin and skill share `metadata.version: 0.1.0`; CI enforces the parity.

## Acknowledgements

- Anthropic's [Agent Skills spec](https://agentskills.io/specification) and the [`skills-ref`](https://pypi.org/project/skills-ref/) reference CLI.
