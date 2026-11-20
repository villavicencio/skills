---
name: new-project
description: "Bootstrap a new project on David's personal Mac in one run: a local repo at ~/Projects/<name> with a minimal bootstrap commit, a private GitHub repository (visibility read back before anything is pushed; a PUBLIC read-back fails the run), the Orca registration, a scriptorium vault section with the harness memory linked into it, the project's Linear project, and a MergeWren onboarding ticket. Runs its checks before the first write, stops only on a collision with something that belongs to something else, does not pause for approval, and is safe to run again (it does only what is missing). --dry-run prints every action in order and writes nothing. Use when the user says \"new project\", \"bootstrap a project\", \"set up a new repo\" or runs dv:new-project <name> --section <section>. NOT for projects that live on hal, NOT for project-specific setup (toolchain, orca.yaml: that is dv:orca-setup, the first feature ticket)."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.16.0"
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
  collision, or when a check can't run. A collision is anything at a target that this skill
  didn't make or that belongs to another project.
- **The checks run before the first write.** Step 1 checks Linear, and the script checks the
  rest before it writes anything. The one check that needs a write first is GitHub's
  visibility, which only exists once the repository does: see the next rule.
- **A second run is safe.** Each step that is already done is skipped. After a failure, fix the
  cause and run the same command again; it does only what is missing.
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

1. **Checkout.** `~/Projects/<name>`, which must not exist yet (an empty folder there is a
   collision too), built in a temp folder beside it and moved into place,
   with one commit: `AGENTS.md` (with a `## Vault` section naming the section), `CLAUDE.md`
   (imports AGENTS.md, so the two stay in step), `README.md`, `.gitignore`,
   `docs/discovery.md`. No feature code. The commit carries `Bootstrapped-by: dv:new-project`,
   which is how a rerun knows the checkout is its own.
2. **GitHub.** `gh repo create <owner>/<name> --private`, then `gh repo view` reads back the
   repository's name, URL, visibility and default branch. Only after a `PRIVATE` read-back does
   it add `origin` and push, and it pushes the bootstrap commit alone. An existing
   repository counts as this project's only when the checkout is this tool's, the repository is
   PRIVATE, and it is empty or holds the bootstrap commit. Anything else is a collision,
   including an existing repository that isn't private.
3. **Orca.** `orca repo add --path <checkout> --kind git --json`, read back with
   `orca repo list --json`. Name and icon are set in the Orca app, not the CLI.
4. **Section.** `<section>/memory` and `<section>/inbox` in `~/Obsidian/scriptorium`, after
   checking that the vault is a real folder with `.obsidian/`. If it isn't, stop: setting up
   the vault is Scribe's work. There is no `.obsidian` step; the vault already has one.
5. **Memory link.** Creates the harness project folder under `~/.claude/projects/` when it is
   missing (it doesn't exist until a session has run in the new folder), then links its
   `memory` to the section's `memory/`. A real `memory/` folder replaces the section's empty
   `memory/` in one rename before the link is made; if the section's `memory/` holds anything,
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
