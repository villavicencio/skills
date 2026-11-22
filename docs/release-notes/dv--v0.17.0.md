# dv — v0.17.0

Minor release. `dv:manager-mode` can now be followed from a Codex session: each hire runs on a named
Codex model and reasoning effort instead of inheriting the manager's. The other fourteen skills have no
behaviour changes; their version moves to `0.17.0` only because the suite is released as one plugin.

Why: the tier table named only Haiku, Sonnet and Opus, and the expected-setting warning relied on
`${CLAUDE_EFFORT}` and `/model opus`. Codex's `spawn_agent` takes GPT models, Codex reads `SKILL.md`
raw so `${CLAUDE_EFFORT}` stays as literal text, and Codex has no `/model opus`. A Codex hire therefore
ran on whatever model it inherited (VIL-800).

## Changed

- **`dv:manager-mode`, "Choosing the effort": a new "Under Codex" block** with three rules.
  - **Tier by role.** Haiku is Codex's fast, affordable model, Sonnet its balanced coding model, Opus
    its most capable model. Before the first hire the manager reads `codex debug models` (the models
    whose `visibility` is `list`), picks the slug whose `description` fits the role best, and names the slug and a one-line
    reason in each brief. There is no table of slugs, because the list changes with each Codex release.
  - **Effort.** Codex's `reasoning_effort` uses the same names as the effort table (`low` to `max`). If
    the effort the table calls for is not in the chosen model's `supported_reasoning_levels`, the
    manager takes the nearest level below it and says so in the brief.
  - **Names.** Where the skill says the Agent tool, `model` or `effort`, a Codex session reads
    `spawn_agent`, `model` or `reasoning_effort`; the brief's "Tier and effort" line carries the slug.
  - **Fork rule.** Every Codex hire passes `model` and `reasoning_effort` with `fork_turns` set to
    `"none"` or a count. A full-history fork (`fork_turns` omitted or `"all"`) inherits the parent's
    model and effort and ignores both settings.
- **`dv:manager-mode`, "Expected setting": a Codex form of the warning.** Under Codex (the agent tool
  is `spawn_agent`) the mode expects Codex's most capable model at `high` effort, or `xhigh` on a
  safety boundary. The model and effort come from what the session's context says, and are `unknown`
  where it says nothing; the warning names the model by slug and points at Codex's `/model` picker. It
  does not use `${CLAUDE_EFFORT}` or `/model opus`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

For Codex: `codex plugin marketplace upgrade`, then `codex plugin list` shows the new version.

The new version takes effect in a new session.
