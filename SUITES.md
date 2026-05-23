# Suites

A **suite** is a set of skills that always release together. Suite membership is declared in each skill's frontmatter as `metadata.suite`; this file is the human-readable manifest.

Members of the same suite must carry matching `metadata.version` values. CI enforces this (`.github/workflows/validate.yml` — suite-version-parity step).

Release tags for suites are suite-grain: `<suite>-v<semver>`. Skill-grain tags are used only for skills that don't belong to any suite.

## Active suites

### `pickup-handoff`

End-of-session and start-of-session companions. `/handoff` writes a structured `HANDOFF.md`; `/pickup` reads it the next time around. They share a data contract (the HANDOFF.md shape), so they must release together — bumping one's version requires bumping the other's.

| Member | Path | Version |
| --- | --- | --- |
| `pickup` | [`skills/pickup/`](skills/pickup/) | `0.1.0` |
| `handoff` | [`skills/handoff/`](skills/handoff/) | `0.1.0` |

**Release policy:** members ship together with matching `metadata.version` values. The release tag is suite-grain: `pickup-handoff-v<semver>`.
