---
name: new-project
description: "Bootstrap a new project on David's personal Mac in one run: a local repo at ~/Projects/<name> with a minimal bootstrap commit, a private GitHub repository (visibility read back before anything is pushed; a read-back other than PRIVATE fails the run), the Orca registration, a scriptorium vault section with the harness memory linked into it, the project's Linear project, and a MergeWren onboarding ticket. Runs its checks before the first write and stops there only on a collision (a target the checks can't show is this project's) or a check that can't run, does not pause for approval, and is safe to run again (it does only what is missing, or stops and says why). --dry-run prints every action in order and writes nothing. Use when the user says \"new project\", \"bootstrap a project\", \"set up a new repo\" or runs dv:new-project <name> --section <section>. NOT for projects that live on hal, NOT for project-specific setup (toolchain, orca.yaml: that is dv:orca-setup, the first feature ticket)."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.24.0"
---

# /new-project — bootstrap a new project on the personal Mac

One run takes a project from a name to: a checkout, a private GitHub repository, an Orca
project, a vault section with the harness memory in it, a Linear project and a MergeWren
onboarding ticket. A project brief then needs only the product and the tracker links.

<new_project_args>
#$ARGUMENTS
</new_project_args>

## Arguments

`<name> --section <section> [--linear-project <name>] [--description <text>] [--owner <login>] [--dry-run]`

- `<name>`: the repository and folder name (`~/Projects/<name>`, `github.com/<owner>/<name>`).
- `--section`: the scriptorium section. Required. Without it, stop before any check or write
  and tell the user the command line needs it. Don't guess a section name.
- `--linear-project`: an existing Linear project to use. Without it the run uses, or creates,
  a project named `<name>`.
- `--description`: one line for the README, AGENTS.md, GitHub and the Linear project.
- `--owner`: the GitHub owner. Default: the account `gh` is logged in as.
- `--dry-run`: print every action in order and write nothing, in Linear too.

## Rules

- **Invoking the skill with a name is the approval.** Don't stop to ask. The run stops only on a
  collision, or when a check can't run. A collision is anything at a target that belongs to
  another project, or that the checks can't show is this project's. Step 2 says what counts as
  proof for each target.
- **The checks run before the first write.** Step 1 checks Linear, and the script checks the
  rest before it writes anything. The one check that needs a write first is GitHub's
  visibility, which only exists once the repository does: see the next rule.
- **A second run is safe.** Each step that is already done is skipped. After a failure, fix the
  cause and run the same command again; it does only what is missing, or stops on what it
  can't place. One such case: `gh repo create` exited non-zero after GitHub made the
  repository, so there is no receipt (Step 2, item 2); the stop message gives the command.
- **The repository is private.** The script creates it with `--private`, without pushing, and
  reads visibility back. Only a `PRIVATE` read-back lets it push. Anything else fails the run
  with nothing pushed: tell the user at once.
- **The rules live in dotfiles, not here.** Read them at origin `master` when a step needs more
  than this file says:
  - the vault, its sections and the memory link: `docs/agents/obsidian-vaults.md`, "New-project bootstrap";
  - Orca projects and worktrees: `docs/reference/orca-worktrees.md`;
  - MergeWren onboarding and what a repo without a reviewer may merge: `docs/agents/code-review.md`;
  - the ticket format: `docs/agents/tickets.md`.
- **Personal Mac only.** On hal the vault check stops the run, since hal has no vault. hal
  projects are separate work.

## Step 1 — Check Linear (read only)

Load the tools: ToolSearch `select:mcp__linear__list_projects,mcp__linear__list_issues,mcp__linear__get_issue,mcp__linear__save_project,mcp__linear__save_issue`.

1. **The Linear project.** With `--linear-project`, find it with `list_projects`; if it doesn't
   exist, stop. Without the flag, look for a project named `<name>`. None: Step 3 creates it.
   One whose description names `github.com/<owner>/<name>` and `dv:new-project`: an earlier run
   made it, so use it. Any other project with that name: stop, and tell the user to pass
   `--linear-project <name>` if it is this project's.
2. **The onboarding ticket.** Search the MergeWren project with `list_issues` for
   `<owner>/<name>`. An open or done ticket that onboards this repository means Step 4 is done.

## Step 2 — Run the script

The script does the checkout, GitHub, Orca, the section and the memory link. It lives in this
skill's base directory (Claude Code names it when the skill loads), under `scripts/`. Put the
real values in place of the angle-bracket placeholders:

```bash
python3 "<skill base dir>/scripts/new_project.py" "<name>" --section "<section>"
```

Pass on any of the optional arguments the user gave, each as one quoted value:
`--linear-project`, `--description`, `--owner`, `--dry-run`.

It prints the plan (each step `done, skip`, `todo`, `would` or `STOP`), then does the `todo`
steps in order, then a report. Python 3.9 or later, stdlib only. Exit codes:

| Exit | Meaning | Do |
|---|---|---|
| 0 | done, or the dry run's plan | Go on to Step 3 (after a dry run, print Steps 3 and 4 as plans and stop) |
| 1 | a check couldn't run, or a step or read-back failed | Report the error and what was done before it. Fix the cause and rerun |
| 2 | usage error (no `--section`, a bad name, `--section david`) | Report it; nothing was checked or written |
| 3 | collision: the `STOP` lines name each one | Report them; nothing was written |

What it does, in order:

1. **Checkout.** `~/Projects/<name>`, which must not exist yet on a first run (an empty folder
   there is a collision too), built in a temp folder beside it and moved into place,
   with one commit: `AGENTS.md` (with a `## Vault` section naming the section), `CLAUDE.md`
   (imports AGENTS.md, so the two stay in step), `README.md`, `.gitignore`,
   `docs/discovery.md`. No feature code. The commit carries the lines
   `Bootstrapped-by: dv:new-project` and `Project: <name>`. A rerun takes an existing checkout
   as its own only when every ref except the stash and notes reaches one root commit, that
   commit has both lines, and any section named in AGENTS.md and any `origin` match this run.
2. **GitHub.** `gh repo create <owner>/<name> --private`. Once the create returns success, the
   script writes a receipt into the checkout's git config (`dv-new-project.created`). Then
   `gh repo view` checks that GitHub answered with this repository (name and URL) and that it
   is `PRIVATE`. Only then does it add `origin` and push, and it pushes the bootstrap commit
   alone. After the push it reads back the default branch and checks that the repository holds
   the commit. An existing repository counts as this project's only when the checkout is this
   tool's, the repository is PRIVATE, and it holds the bootstrap commit, or is empty while the
   checkout holds the receipt. Anything else is a collision, including an existing repository
   that isn't private and an empty one with no receipt (after a `gh repo create` that exited
   non-zero, even once GitHub made the repository, the next run stops there, and the stop
   message gives the command that writes the receipt by hand).
3. **Orca.** `orca repo add --path <checkout> --kind git --json`, read back with
   `orca repo list --json`. The check before and the read-back after use one rule: exactly one
   entry at the checkout path, of kind git, for this repository (or with no remote known yet),
   and no entry for this repository at another path. The read-back also needs the id that
   `repo add` returned. Name and icon are set in the Orca app, not the CLI.
4. **Section.** `<section>/memory` and `<section>/inbox` in `~/Obsidian/scriptorium`, after
   checking that the vault is a real folder with `.obsidian/`. If it isn't, stop: setting up
   the vault is Scribe's work. There is no `.obsidian` step; the vault already has one. An
   existing section is this project's when this project's memory already links to it, or when
   it holds nothing but an empty `memory/` and an empty `inbox/`. Anything else in it, a Finder
   `.DS_Store` included, is a collision, and so is a section another project's memory links to.
5. **Memory link.** The harness project folder under `~/.claude/projects/` is named after the
   checkout's path, with each character that isn't a letter or digit turned into `-`, so other
   paths can share the name (`~/Projects/foo_bar` or `~/Projects/foo/bar` for `foo-bar`). An
   existing folder that shares it is a collision. When the folder is missing (it doesn't exist
   until a session has run in the new folder), the script creates it and links its `memory` to
   the section's `memory/`, and removes the folder again if the link fails. An existing folder
   is this project's only when the checkout already exists too, no session in it started
   elsewhere, and either its `memory` already links to the section or it holds a session that
   started in this checkout. A real `memory/` folder there replaces the section's empty
   `memory/` in one rename before the link is made. If the link fails, the folder moves back
   and the section gets its empty `memory/` again. If the section's `memory/` holds anything,
   that is a collision.

## Step 3 — The Linear project

Skip if Step 1 found it. Otherwise `save_project` in team VIL, named `<name>` (or the
`--linear-project` value), with a description of the `--description` line, then
`Repository: https://github.com/<owner>/<name>` and `Created by dv:new-project on <date>`.
A failed save can hide a write that landed: read before you retry.

## Step 4 — The MergeWren onboarding ticket

Skip if Step 1 found one. Otherwise read the model, `get_issue` VIL-537, and file a ticket in
the MergeWren project, team VIL, in the format of dotfiles `docs/agents/tickets.md`:

- Title: `Onboard <owner>/<name> (posting on)`.
- Why: the repository is new and has no reviewer until it is onboarded.
- Want: the model's list as it reads at filing time (adoption record, OCR rule, plan decision,
  posting lists, allowlist, pin test). Copy it from the model, not from this file.
- Profile: a note that fits the project's language and risks, taken from the description or
  the brief (for example credentials, launchd jobs, user data, network calls).
- Done means: a real MergeWren verdict on a PR in the new repository.

**Filing the ticket is not adoption.** The repository has no reviewer until that verdict is
seen on a PR. Until then dotfiles `docs/agents/code-review.md` decides what may merge, and the
new repository's AGENTS.md says the same.

## Step 5 — Report

Reply in the user's layout (answer line first). Include:

- repository URL and visibility, local path, Orca id, section;
- the Linear project and the onboarding ticket, each as a markdown link;
- what the run did, and what it skipped as already done;
- what is still open: the Orca name and icon (set in the app), MergeWren adoption, the
  repository's `orca.yaml` (`dv:orca-setup`) and the first feature ticket.
