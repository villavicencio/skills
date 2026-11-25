# dv — v0.32.0

Minor release. `dv:ticket` and `dv:groom` now put a ticket in one of its Linear project's
milestones when one fits. Filing gives a ticket the milestone the request names, or else the
existing milestone whose goal it serves, shown in the draft; proposes a new milestone only when the
project has open milestones and none fits, and creates it only on the user's yes; and otherwise
files it with none and says so. Grooming checks the milestone a ticket has, under the same rules.
The rules both skills follow live once, in a new "Milestones" section of the shared rules file
(`plugins/dv/skills/ticket/references/ticket-format.md`). The other fourteen skills have no
behaviour changes; their version moves to `0.32.0` only because the suite is released as one
plugin.

Numbering: 0.32.0 follows 0.31.0, which moved the prerequisite rules both skills share into the
same shared rules file.

Why: no dv skill mentioned milestones. Every milestone so far was set by hand, from a memory only
the skills repo's sessions can read, so tickets filed elsewhere landed with none (VIL-995).

## Changed

- **Shared rules, new "Milestones" section.**
  - How to read a project's milestones (`list_milestones`) and a ticket's (`get_issue`,
    `projectMilestone`).
  - A milestone at 100% progress is finished: it gets no new ticket, and an open ticket left in
    one is asked about.
  - A ticket fits the milestone whose stated goal its work serves, with a one-line reason; a loose
    fit counts as none. The milestone is set with `save_issue`'s `milestone` field.
  - A Decisions line that records "No milestone" keeps a ticket out of milestones; a ticket that
    records it but has a milestone anyway is asked about, not changed.
  - A new milestone is proposed only as a question (a name and one line on what done means),
    created only on a yes with `save_milestone`, and never with a target date. A path that skips
    the yes never creates one.
  - "Re-read before the save", for `dv:groom`: just before the first child or spin-off filing
    that uses the milestone step 3 settled, and before the groomed ticket's own save (each time
    before any new milestone is created), the milestones and the groomed ticket's milestone are
    read again. If that milestone has finished, gone or changed its goal since step 3, or the
    groomed ticket's milestone changed, the save stops and goes back to the user, in `forks-only`
    mode too. `dv:ticket` keeps its own re-read in File step 7.
  - "Creating an approved milestone", one rule both skills point to: create it last, right
    before the first save that sets it and after every re-read that can stop the run; just before
    creating, reuse an open milestone with that name only when its description states the
    approved goal, and otherwise (or when only a finished one has the name) ask again; after a
    failed create, read `list_milestones` back and do not retry; and if the save that sets it then
    fails or its reply is lost, stop, do not retry, read back what landed and report that the
    milestone now exists.
- **`dv:ticket`, new File step 2b, "Milestone".** It lists the project's milestones, then takes
  the first case that applies:
  - The request names a milestone: use it if it matches one in the list; if it matches none, or
    only a finished one, say so and ask.
  - The project has no milestones, or only finished ones: the draft says so and proposes none.
  - One fits: the draft (step 6) shows it with its one-line reason.
  - The project has open milestones, but none fits: the interview proposes a new milestone, with
    "file with no milestone for now" and "keep it out of milestones" (recorded as "No milestone")
    as the other options.

  Step 7 reads the milestones again: one that has since finished or gone sends the draft back to
  step 2b (or, without confirmation, the ticket is filed with none). After its checks it creates an
  approved new milestone right before `save_issue`, under the shared "Creating an approved
  milestone" rule, sets the milestone in the `save_issue` call, and reads it back. Step numbering:
  the step is "2b" so that File steps 3 to 7, which `dv:groom` and the shared rules cite by number,
  keep their numbers.
- **`dv:ticket`, "Filing without my confirmation".** A spin-off or closeout item takes its source
  ticket's milestone. When the source has none, or a finished one, it is filed with none and the
  report says so; no milestone is ever created on this path.
- **`dv:groom`, step 3, new "Milestone" check.** It takes the first case that applies:
  - A Done, Canceled or Duplicate ticket: left as it is.
  - Decisions records "No milestone" and the ticket has none: nothing proposed. If it has a
    milestone anyway: asked, take it out or keep it.
  - No milestone, and the project has no milestones or only finished ones: nothing proposed.
  - An open ticket with no milestone, and one fits: setting it is an add item (a routine call in
    `forks-only` mode).
  - No milestone and none fits: the field stays empty, the report says so, and a new milestone is
    an open decision (a fork).
  - Its goal no longer fits its milestone, or that milestone is finished: asked (a fork) whether to
    move it (to the milestone that fits, or out of milestones), put it in a new milestone when no
    other one fits (created only on a yes), or keep it. Grooming never moves a ticket out of a
    milestone as a routine call.

  From a worktree session, a fork that offers a new milestone comes straight to the user, not to
  the Director.
- **`dv:groom`, splits and spin-offs.** A split's children take the parent's milestone, and a
  spin-off filed in the groomed ticket's project takes the groomed ticket's, as the approved edit
  list leaves it ("Order of writes" item 2); with none or a finished one, they get none. A spin-off
  filed in another project takes the existing milestone File step 2b picks there, or none. Item 2
  creates no milestone itself; an approved new milestone, which children and spin-offs in the
  groomed ticket's project take, is created under the shared "Creating
  an approved milestone" rule: right before the first save in "Order of writes" that sets it (a
  filing in item 2, or the groomed ticket's change in item 4), after the re-reads before that save;
  a failed save after it is not retried. The split proposal and each spin-off line show the
  milestone.
- **`dv:groom`, edit list, report and rules.** The milestone is an edit-list item; the report
  gives the milestone as read back; a milestone is created only on a yes; and a ticket whose text
  needs no edits may still get the milestone item beside the `groomed` label item.
- **Both skills' "Linear tools" lists** name `list_milestones` and `save_milestone`.
- **README.** The `dv:ticket` and `dv:groom` entries describe the milestone rules, and the plugin
  table shows `0.32.0`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
