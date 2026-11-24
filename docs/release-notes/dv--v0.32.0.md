# dv — v0.32.0

Minor release. `dv:ticket` and `dv:groom` now put each ticket in one of its Linear project's
milestones. Picking an existing milestone is a routine call; a new milestone is proposed only to
the user and created only on their yes. The rules both skills follow live once, in a new
"Milestones" section of the shared rules file
(`plugins/dv/skills/ticket/references/ticket-format.md`). The other fourteen skills have no
behaviour changes; their version moves to `0.32.0` only because the suite is released as one
plugin.

Numbering: 0.32.0 follows 0.31.0, which moved the prerequisite rules both skills share into the
same shared rules file.

Why: no dv skill mentioned milestones. Every milestone so far was set by hand, from a memory only
the skills repo's sessions can read, so tickets filed elsewhere landed with none (VIL-995).

## Changed

- **Shared rules, new "Milestones" section.** How to read a project's milestones
  (`list_milestones`) and a ticket's (`get_issue`, `projectMilestone`); a milestone at 100%
  progress is finished and gets no ticket; a ticket fits the milestone whose stated goal its work
  serves, with a one-line reason, and a loose fit counts as none; the milestone is set with
  `save_issue`'s `milestone` field; a Decisions line that records "No milestone" keeps a ticket out
  of milestones; a new milestone is proposed only as a question (a name and one line on what done
  means), created only on a yes with `save_milestone`, never with a target date, looked for by
  name just before creating, and read back after an error instead of retried; a path that skips
  the yes never creates one.
- **`dv:ticket`, new File step 2b, "Milestone".** Lists the project's milestones and takes the one
  the request names, else the one that fits; the draft (step 6) shows it with its reason. When
  none fits, the interview proposes a new milestone, with "file with no milestone for now" and
  "keep it out of milestones" as the other options. When the project has no milestones, or only
  finished ones, the draft says so and proposes none. Step 7 creates an approved new milestone
  just before `save_issue`, sets the milestone in the `save_issue` call, and reads it back.
  Step numbering: the step is "2b" so that File steps 3 to 7, which `dv:groom` and the shared
  rules cite by number, keep their numbers.
- **`dv:ticket`, "Filing without my confirmation".** A spin-off or closeout item takes its source
  ticket's milestone. When the source has none, or a finished one, it is filed with none and the
  report says so; no milestone is ever created on this path.
- **`dv:groom`, step 3, new "Milestone" check.** A ticket whose Decisions records "No milestone"
  is left alone. An open ticket with no milestone, in a project that has milestones, gets the one
  that fits as an add item (a routine call in `forks-only` mode). When none fits, the field stays
  empty, the report says so, and a new milestone is an open decision (a fork). A ticket whose goal
  no longer fits its milestone is asked: move it or keep it; grooming never moves a ticket out of
  a milestone as a routine call. From a worktree session, a new milestone comes straight to the
  user, not to the Director.
- **`dv:groom`, splits and spin-offs.** A split's children take the parent's milestone and a
  spin-off takes the groomed ticket's, as the approved edit list leaves it ("Order of writes"
  item 2); with none or a finished one, they get none. An approved new milestone is created before
  "Order of writes" item 1, whether or not anything is filed. The split proposal and each spin-off
  line show the milestone. A Done, Canceled or Duplicate ticket's milestone is left as it is.
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
