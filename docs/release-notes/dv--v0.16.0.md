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
  repository, created with `--private` (a receipt goes into the checkout once the create
  succeeds), and pushed (the bootstrap commit alone) only after the read-back names this
  repository and shows it private; the Orca registration, read back by the same rule as the
  check; the scriptorium section's `memory/` and `inbox/`; and the harness memory link,
  creating the harness project folder when it is missing.
- **One ownership rule per target, used by the check and the write.** The checkout is this
  project's when every ref except the stash and notes reaches one root commit, that commit
  carries `Bootstrapped-by: dv:new-project` and `Project: <name>`, and any section named in
  AGENTS.md and any `origin` match the run. The repository is when it is private
  and holds that commit, or is empty while the checkout holds the receipt of this tool's
  create. The Orca registration is when it is the one entry at the checkout path, of kind git,
  for this repository or with no remote known yet, and no entry for this repository is
  elsewhere. The section is when no other project's memory links to it, and this project's
  memory does or it holds nothing but an empty `memory/` and `inbox/` (a `.DS_Store` counts as
  content). The harness folder is when no other existing folder maps to its name (such as
  `~/Projects/foo_bar` or `~/Projects/foo/bar` for `foo-bar`), the checkout already exists, no
  session in it started elsewhere, and either its `memory` links to the section or a session in
  it started in this checkout.
- **The agent does Linear**: it checks for the Linear project before the script runs, creates it
  when none exists (or uses the one `--linear-project` names), and files the MergeWren onboarding
  ticket from the model ticket. Filing is not adoption: the repository has no reviewer until a
  real MergeWren verdict is seen on a PR.
- **No pause; a collision writes nothing.** The run doesn't ask for approval. Before any write
  it stops only on a collision (a target that belongs to another project, or that the checks
  can't show is this project's) or a check that can't run, with nothing written. A step that
  fails partway is put back where it can be: the checkout is built in a temp folder, a harness
  folder the run made is removed if its link fails, and a `memory/` folder whose link fails
  moves back while the section gets its empty `memory/` again. A rerun does only what is
  missing, or stops on what it can't place: after a `gh repo create` that exited non-zero once
  the repository existed, there is no receipt, and the stop message gives the command that
  records it. `--dry-run` prints every action in order and writes nothing.
- **Tested with stubs.** `tooling/evals/test_new_project.py` runs the script against temp folders
  with `gh` and `orca` stubbed, in the `validate` workflow. The first live run is the next real
  project.

Not covered: projects that live on hal (the vault check stops the run there), and anything
specific to one project (toolchain, `orca.yaml`, the first feature ticket).
