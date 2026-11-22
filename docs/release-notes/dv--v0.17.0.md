# dv — v0.17.0

Minor release. `dv:manager-mode` can now be followed from a Codex session: each hire runs on a named
Codex model and reasoning effort instead of inheriting the manager's. The other fourteen skills have no
behaviour changes; their version moves to `0.17.0` only because the suite is released as one plugin.

Why: the tier table named only Haiku, Sonnet and Opus, and the expected-setting warning relied on
`${CLAUDE_EFFORT}` and `/model opus`. Codex's `spawn_agent` takes GPT models, Codex reads `SKILL.md`
raw so `${CLAUDE_EFFORT}` stays as literal text, and Codex has no `/model opus`. A Codex hire therefore
ran on whatever model it inherited (VIL-800).

## Changed

- **`dv:manager-mode`, "Choosing the effort": a new "Under Codex" block** with four rules.
  - **Tier by role.** Haiku is Codex's fast, affordable model, Sonnet its balanced coding model, Opus
    its most capable model. The manager lists the models with a `codex debug models` command piped
    through `jq` that keeps only the models whose `visibility` is `list`, and only their `slug`,
    `description` and `supported_reasoning_levels` (the raw catalog is about 165,000 tokens). Haiku and
    Sonnet take the slug whose `description` fits the role best. Opus takes the first model on that
    list, Codex's default: in the live test a description match picked a previous-generation model,
    because the newest model's description reads "efficient". Each brief names the slug and a one-line
    reason. There is no table of slugs, because the list changes with each Codex release.
  - **Effort.** Codex's `reasoning_effort` uses the same names as the effort table (`low` to `max`). If
    the effort the table calls for is not in the chosen model's `supported_reasoning_levels`, the
    manager takes the nearest level below it and says so in the brief.
  - **Names.** Where the skill says the Agent tool, `model` or `effort`, a Codex session reads
    `spawn_agent`, `model` or `reasoning_effort`, and `ListAgents` as `list_agents`, which lists only
    that session's agents. Other sessions are in the interactive `codex agents` browser, which a manager
    cannot drive, so under Codex the ticket check cannot return `ready`; it is `ready with caveats` or
    `blocked`. The brief's "Tier and effort" line carries the slug.
  - **Fork rule.** Every Codex hire passes `model` and `reasoning_effort` with `fork_turns` set to
    `"none"` or a count. A full-history fork (`fork_turns` omitted or `"all"`) inherits the parent's
    model and effort and ignores both settings.
- **`dv:manager-mode`, "Expected setting": a Codex form of the warning.** Under Codex (the agent tool
  is `spawn_agent`) the mode expects Codex's most capable model (the first on that list) at `high` effort, or `xhigh` on a
  safety boundary. The model and effort come from what the session's context says, and are `unknown`
  where it says nothing; the warning names the model by slug and points at Codex's `/model` picker. It
  does not use `${CLAUDE_EFFORT}` or `/model opus`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

Codex's installed copy of dv is refreshed separately, and this release does not change how. `codex plugin marketplace upgrade` refreshes configured Git marketplace snapshots; `codex plugin add` is the separate install step (checked with `--help` on Codex CLI 0.159.2; not run).

The new version takes effect in a new session.
