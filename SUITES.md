# Suites → Plugins

**As of v0.1.0, suite grain = plugin grain.** Skills that ship together live inside the same plugin under `plugins/<plugin-name>/skills/`, and the plugin's version applies to every skill it contains. CI enforces this.

The older "suite" concept (skills declaring `metadata.suite` in their `SKILL.md` frontmatter and a separate `SUITES.md` manifest) has been folded into the plugin model — there is no longer a separate suite-grain identity to track.

## Active plugins

See [`README.md`](README.md) for the canonical plugin table and install procedure.
