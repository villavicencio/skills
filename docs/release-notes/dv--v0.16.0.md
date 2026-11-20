# dv — v0.16.0

Minor release. It adds one skill, `dv:new-project`. The other fourteen skills have no behaviour
changes; their version moves to `0.16.0` only because the suite is released as one plugin.

Numbering: 0.15.0 is claimed by another open PR (`dv:director-mode`). If that PR has not merged
when this one does, the home session may renumber this release.

## Added

### `dv:new-project`: bootstrap a new project on the personal Mac (VIL-780)

`dv:new-project <name> --section <section>` takes a project from a name to everything around it,
so a project brief only needs the product and the tracker links.

- **A script for the local and GitHub steps** (`scripts/new_project.py`, stdlib Python 3.9+):
  the checkout at `~/Projects/<name>` with one bootstrap commit (`AGENTS.md` with a `## Vault`
  section, `CLAUDE.md` importing it, `README.md`, `.gitignore`, `docs/discovery.md`); the GitHub
  repository, created with `--private` and read back before anything is pushed, then the
  bootstrap commit alone is pushed; the Orca registration with a read-back; the scriptorium
  section's `memory/` and `inbox/`; and the harness memory link, creating the harness project
  folder when it is missing.
- **The agent does Linear**: it checks for the Linear project before the script runs, creates it
  when none exists (or uses the one `--linear-project` names), and files the MergeWren onboarding
  ticket from the model ticket. Filing is not adoption: the repository has no reviewer until a
  real MergeWren verdict is seen on a PR.
- **No pause, no partial overwrite.** The run doesn't ask for approval. It stops only on a
  collision (anything at a target this tool didn't make, or that belongs to another project),
  with nothing written. A rerun does only what is missing. `--dry-run` prints every action in
  order and writes nothing.
- **Tested with stubs.** `tooling/evals/test_new_project.py` runs the script against temp folders
  with `gh` and `orca` stubbed, in the `validate` workflow. The first live run is the next real
  project.

Not covered: projects that live on hal (the vault check stops the run there), and anything
specific to one project (toolchain, `orca.yaml`, the first feature ticket).
