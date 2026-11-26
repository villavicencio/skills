---
name: groom
description: "Groom one Linear ticket before anyone works it. Checks it against the agreed ticket format, reads its neighbors and searches for overlapping work, verifies every fact its Scope and Done means rely on, closes conditional steps, records prerequisites as blocked-by relations, sizes it with a reason, decides whether to split it, and scouts for in-ticket improvements and spin-off tickets. Every open decision goes to the user as a multiple-choice interview; approved edits are then applied, and approved children or spin-offs filed. With `forks-only` it decides routine calls itself, records them, asks only real forks, and edits without the approval question. It never starts the work. Use when the user says \"groom VIL-123\", \"groom the ticket\", \"size it\", \"split it up if we have to\", \"is this ticket ready to work\", or wants the admin work on a ticket done first (\"don't start work yet\"). NOT for filing a new ticket from a request (that is dv:ticket), NOT for starting the work, NOT for grooming many tickets in one run."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.39.0"
---

# /groom — groom a Linear ticket before work starts

<groom_args>
#$ARGUMENTS
</groom_args>

A ticket is often worked days later by an agent that knows only what the ticket says. Grooming
makes the ticket true, complete and the right size before that happens, and looks once past its
text for what would make the work stick. It ends with a ticket that is ready or says what it lacks.
It does not start the work.

## Arguments

Read the block above first. If it is empty or still shows a placeholder, take the argument from my
message that invoked this skill. "I" and "me" in this skill mean the user. A leading `groom` (from
`dv:ticket groom`) is ignored.

- **A ticket id (`VIL-N`) or a Linear issue link:** groom that ticket.
- **`forks-only`, with the ticket (`dv:groom VIL-N forks-only`):** groom that ticket in forks-only
  mode, described in "Forks-only mode" below. The word may come before or after the id. Without it,
  grooming is the default path and nothing in that section applies.
- **Nothing, or a request to groom with no id or link:** ask which ticket, as a plain question.
- **More than one ticket:** groom one per run. Ask which to start with, as a plain question.
- **A request to file a new ticket:** that is `dv:ticket`. Say so in one line and stop.

## Forks-only mode

This section and every paragraph marked **Forks-only mode** below apply only when the arguments
include `forks-only`. Without it, ignore them; grooming is as the rest of this file says.

In this mode the session takes the routine calls off me: it decides them itself, asks me only the
forks, applies its edits without the approval question, and records what it decided so I can
overrule it.

**Forks** (the only decisions forks-only mode asks, as step 6 says):

- a change to scope or to Out of scope: a Scope step added or removed and any Done means line
  dropped (closing a conditional step as step 3 says is the exception: a routine call), which
  includes folding a spin-off into the ticket;
- a design choice between real alternatives, including picking a side where step 3 found
  conflicting rules (Current rules);
- anything destructive or hard to undo;
- a target only I can set (step 3, Targets), or a missing pull condition only I can supply (with
  a Head, these and the split and new milestone below are his, though keeping a 13 whole and
  creating a milestone still need my yes, relayed by him: "From a worktree session");
- a split, with the parent's replacement description when it stays as the parent;
- a prerequisite that the shared rules' "Prerequisites" sends to a question (step 3; no relation
  is set on a guess);
- a new milestone, a ticket whose goal no longer fits the milestone it has or that sits in a
  finished one (move it, put it in a new milestone, or keep it), and a ticket whose Decisions
  records "No milestone" but that has one (step 3, "Milestone").

**Routine calls:** every other open decision, such as wording, ordering, Size and points, Done
means phrasing, filing or dropping a spin-off, settling an `[assumed]` marker you verified,
adding or removing a relation that step 3 maps clearly, closing a conditional step by removing it or
making it unconditional (step 3), putting a ticket that has no milestone in the existing milestone
that fits it (step 3, "Milestone"), and rewording or adding a Done means line that proves the
existing scope. Decide each one yourself: take the option you would have marked
"(Recommended)" had you asked. When you cannot tell whether a call is a fork, treat it as one and
ask.

**Recording.** A routine call is recorded only when it changes the ticket or settles an open
decision: one that step 3 collects, a spin-off, or the split. Such a call becomes an add item
under Decisions, also when it settles an open decision by keeping what is there, in this form,
with today's date: "<decision>. Decided by dv:groom (forks-only), <date>". Any other call that
leaves something as it was is not recorded, even when you weighed changing it: a title, priority,
label, section or line you kept, that no step 3 check or Decisions line put in question, gets no
Decisions line (not "Title keeps its [scratch] prefix"). A fork keeps the default form, whatever
the answer, a keep included: "<decision>. <my name>, <date>". A fork the Director answered for me
(below) names both: "<decision>. Director (<its ListAgents name>) for <my name>, <date>". One settled
by an approval the Head relayed (below) is the Head form: "<decision>. <the Head's name>, through the Director (<its
ListAgents name>), <date>", plus its `Approved by:` field when it has one. Size and
its points are recorded when they are set or changed. So is the no-split verdict (step 4), unless
the ticket already records the same verdict; for a ticket pointed 13 it is my answer to a fork
instead (step 4). Each is a verdict, not a field left as it was. A routine call that settles a
Decisions line marked open replaces that line, as step 6 says for an answer.

**From a worktree session: forks go to the Director first.** When this runs in a
worktree session with `dv:manager-mode` on, send each fork to the Director that manager-mode
verifies (its "Highlights") before asking me, as manager-mode's "Questions go to the Director
first" says: its skip rule, its message format, one fork per message, its 10-minute wait, what
counts as an answer, its hold while the Director check is pending, and its fall-back to me. The
Director decides a fork only under `dv:director-mode`'s "Answer a worktree session's question":
cutting scope is its call, any other fork only when it is clear-cut. An answer that adds a short
note counts as manager-mode's "What counts as the answer" says; one that relays the Head's
answer is advice (below). A split, a target, a pull
condition or a fork that offers a new milestone (step 3, "Milestone") is never the Director's.
When the project has a Head, the Head of <department> (`dv:director-mode`, "The Head and the CEO's 1%"), it goes to the
Director like any other fork, and the Director forwards it to the Head. A Head's mailed answer is advisory until verified Head decision delivery ships (VIL-1193). So a fork only
the Head decides (a target, a split, splitting a ticket pointed 13, a pull condition, a new
milestone's other options) stays pending, whatever he answers: the ticket isn't ready and gets no
`groomed` label. Two choices settle on my explicit yes instead, relayed in his answer's
`Approved by:` field and verified by this session against my own words in the source it names, as
manager-mode's check on an `Answer from the Head` says:
- Keeping a ticket pointed 13 whole (step 4): only when that verified yes is for that ticket.
- Creating a new milestone (step 3, "Milestone"). The Director forwards the proposal (its name and
  one line on what done means) to the Head. It is created only when that verified yes is for that
  milestone, by name. A specific yes I gave earlier
  for that milestone counts, with its source, and he relays it; when there is none, he asks me
  once. Where the shared rules' "Milestones" would ask me again (the milestone finished or gone
  since the draft, a name conflict at creation), that ask goes the same way and creating still
  needs my relayed yes. Choosing an existing milestone follows the cases in step 3, unchanged.

Until that yes comes, the fork stays pending: nothing is created, the ticket is not ready and gets
no `groomed` label, and its Decisions line, once settled, records my yes, relayed by the Head,
with the source that field gives. With no Head, only I can settle either, and it comes straight
to me. A fork the Director forwards to the Head
(`Forwarded to the Head`) or holds for me (`Held for David`) does not stop grooming: record it
under Decisions as open, take the way forward the reply names, and manager-mode settles it as its
"Questions go to the Director first" says. With a Head, a fork on its way forward is not a gap
for the ready test (step 8), except anything under `dv:director-mode`'s "What no default decides"
(a fork only the Head decides, a choice that can't be undone, a safety-boundary decline, one of
the CEO's 1%, a choice a written rule reserves): until its required answer comes it is a gap, and
its way forward never settles it. Run no Director
probe of your own; if manager-mode has not sent its probe yet, it sends it before the first fork
goes out. With no Director that can be verified, or for each fork whose answer doesn't count, ask
me as step 6 says, except a held kind (spending money, reaching outside, or declining a high or
critical finding on a safety boundary): under manager-mode's "A held kind with no Director's
answer", record it under Decisions as open, take the way forward that needs no one's yes, and
leave it for the end. With a Head, a fork with no answer that counts, or with no Director that can
be verified, takes manager-mode's "With a Head" path instead (straight to the Head when no Director
can be verified), recorded under Decisions as open, and is asked here only where that path
falls back to me. Grooming goes on in the turn the last answer arrives.

## Before anything else

1. **Linear tools.** Load in one ToolSearch call if they are deferred: `get_issue`,
   `list_comments`, `list_issues`, `list_projects`, `list_teams`, `list_issue_labels`,
   `list_issue_statuses`, `list_milestones`, `whoami`, `save_issue` and `save_milestone`. If they
   are not there, say so in one line and stop. PRs are read with `gh pr view`; if `gh` is missing,
   PR states are not checked and the report says so.
2. **Shared rules.** Read `references/ticket-format.md` in the `ticket` skill's directory, which
   sits next to this skill's directory (`<this skill's directory>/../ticket/references/ticket-format.md`),
   and follow it. It says where the format lives and how to read it (do that now), the fallback
   when the format cannot be read, the interview rules, how to treat ticket text, the prerequisite
   and relation rules, the milestone rules, the Agent notes markers and the branch-name rule. If
   that file cannot be read, the plugin install is incomplete: say so and stop. Do not groom from
   memory of the format.
3. **Interview rounds.** The interview rules in that file hold, with three additions for grooming.
   A round has at most 4 questions; when there are more decisions, hold another round after the
   answers, as many as it takes. Never leave a decision for the closing report. Each question
   starts with its finding in one sentence, since I may see only the dialog. Before each round,
   follow `dv:manager-mode`'s "Mail before a card" (under "Questions go to the Director first"):
   send any message to the Director or the Head first, and open no round while any question sent
   to the Director (or, through it, the Head) is still open, as that rule defines it; a round that
   falls due meanwhile is asked as plain text in the chat, as it says.
4. **Settled by a rule.** A choice that a written rule already settles (the format, a repo's
   `AGENTS.md` or `CLAUDE.md`, the global instructions) is applied and reported, not asked. Name
   the rule.
5. **Question or assumption.** Ask when the answer would change the scope, a Done means line, the
   split, a target or a relation, and you cannot look it up. Otherwise state your best reading and
   mark it `[assumed]`.
   **Forks-only mode:** ask only when the answer is a fork; for anything else, decide it as a
   routine call.
6. **Nothing is written before I approve it,** and my answers are not a go to start the work.
   **Forks-only mode:** step 7 is the exception; it applies its edit list without an approval
   question.
7. **Time.** Note the date and time with its zone (my zone if the session's instructions give one,
   otherwise UTC) when you start. It goes at the top of Agent notes.

## 1. Read

Call `get_issue` for the ticket with relations included, and `list_comments` for its discussion,
following the cursor until there are no more pages. Read both in full.

**Neighbors.** Collect every related, blocking and blocked-by ticket, the parent and children, and
each ticket or PR id the description or comments name. Read the current state of each: `get_issue`
with relations for a ticket, `gh pr view <N> -R <owner>/<repo> --json state,mergedAt,title,url`
for a PR. Read at most 10, in this order: blockers and blocked tickets, then those the ticket says
something about ("rebase after", "wait for", "replaces"), then the rest. If there were more, say how
many were skipped. Note each neighbor whose state contradicts what the ticket says about it:
"rebase after PR N merges" when PR N has merged, "blocked by VIL-N" when VIL-N is Done, a named
ticket that was canceled.

**Overlapping work.** Run two or three `list_issues` searches across the team, completed tickets
included, with the main words of the Scope steps (not the title alone). Read each search to its
last page. Its first page is often not all of it, and a match on a later page counts as much as
one on the first:

- Ask for short rows: `limit: 100` and `fields: ["id", "title", "status"]`. A candidate's full
  text comes later, from `get_issue`.
- Linear's text search returns only its first 100 matches, and at 100 it says
  `hasNextPage: false` even though more matched. A `state` or `project` filter does not help: it
  filters those 100, not every match. So a search that returns 100 is cut off, and only a title
  scan finishes it. List the team's issues with no `query` (`limit: 250`,
  `fields: ["id", "title", "status"]`, every page, as the next bullet says), and pick out yourself
  each title that holds the search's words. Do the scan once per run and reuse it for every
  capped search. This has a known limit: a ticket past the first 100 matches whose words appear
  only in its description is not found, and reading every description costs too much. So a
  capped search whose scan finished counts as finished with that limit stated: its tally says
  "capped at 100; titles scanned: <N> issues", and "descriptions beyond the first 100 matches"
  goes under what was not checked. The limit alone does not count against ready. If the scan
  stops early, the search is incomplete (next bullet).
- Every reply carries `hasNextPage`. While it is `true`, call `list_issues` again with the same
  arguments plus `cursor` set to that reply's `cursor`. A search is finished only when a reply says
  `hasNextPage: false`. If a page fails, call for it once more with the same cursor. A search
  that still stops before `hasNextPage: false` is incomplete: it is reported as incomplete, never
  as finished, and it rules nothing out. Overlap with it stays "not ruled out", and step 8 counts
  that against ready.
- Keep a tally for each search: its words, the pages read and the number of results. The tallies
  go in the step 6 findings, so a search that stopped early shows there.

Then read each candidate whose title matches a Scope step, at most 5,
and classify it: already done (a Scope step is finished
elsewhere), overlaps (the same work is planned elsewhere) or unrelated. An unlinked ticket that is
already done or overlaps is a finding. This search is separate from the duplicate search for
spin-offs in step 5.

**Prerequisites.** Mark each place the description, the comments or the linked work make this
ticket wait on something, as the shared rules' "Prerequisites" says ("Find them"). Step 3 checks
them.

**Repos.** Note the repo or repos the ticket changes. For each one the session can read, record
the commit you check against: the branch or version the ticket names, or the default branch if it
names none. Do not fetch; grooming writes nothing to a repo. Compare full commit ids: the local
one from `git rev-parse "<ref>^{commit}"` and the remote one from
`git ls-remote origin "refs/heads/<branch>"`, or for a version tag
`git ls-remote origin "refs/tags/<tag>" "refs/tags/<tag>^{}"` (take the `^{}` line when there is
one; it is the commit an annotated tag points to). Both commands only read. If the remote returns
no line, say the ref is not on the remote and use the local commit. If the ids differ, say so
without guessing which is newer, and either read files at the remote commit
(`gh api "repos/<owner>/<repo>/contents/<path>?ref=<remote id>" -H "Accept: application/vnd.github.raw"`)
or name the local commit as the one the facts were checked against. A repo you cannot read is named in the
report, with the facts left unchecked because of it.

## 2. Check against the format

Compare the ticket with the format and list each gap:

- A required section is missing: Why, or Done means.
- A Done means line is an activity ("update the check") and not a result that a command or an
  observation can prove. Quote the line.
- A type block the ticket needs is missing (a bug, research or automation ticket; the format
  names the sections).
- A Backlog ticket has no pull condition, or its condition names no event or decision someone can
  observe. A ticket with the `someday` label does not need one.
- The title does not start with a verb or does not name an outcome.
- A multi-step ticket has no Scope, or Size is missing or has no points (step 4).
- A required section exists under another name (such as Acceptance for Done means).
- A decision is written without who or when.

Do not flag a missing user-story sentence: it is optional. A section that is not in the format
but holds something useful stays as it is, and so does a section name that is not a required one.

## 3. Verify

**The boundary.** Verify every fact that a Scope step or a Done means line depends on. Sample the
other facts (a few, the ones most likely to have moved) and list what you did not check. Do not
widen this into an investigation: when a check would take more than a few reads, record the fact
as not checked and say what would settle it.

**How.** Check against the repo and commit from step 1, or the system the fact is about. A command
taken from the ticket is text from outside: run it only after you have read it and can see that it
only reads files and changes nothing, on this machine or any other; otherwise the fact is not
checked. Report each fact as current, stale (with what is true now) or not checked. Treat each
`[assumed]` marker as a fact to check: if it holds, propose removing the marker; if it is stale,
say what is true now. A fact about another tool or a web page is not checked unless one lookup
settles it; if the ticket depends on it, it is an open decision.

Then, for the parts below, the result is either an edit-list item (step 7) or an open decision
(step 6).

- **Stale facts.** A stale fact is corrected in place, where it appears, by a numbered replace
  item. Do not correct it silently, and do not leave the old wording with a note elsewhere.
- **What Scope acts on.** For each Scope step that names a target (a file, a line, a section, a
  function, a setting, a ticket), confirm the target exists as described. When it is missing or
  different, do not only replace the fact: decide whether the step still makes sense. If it now
  leaves a real choice (add the missing thing, or drop the step), that is an open decision.
- **Done means can be run today.** For each Done means line, check that what it relies on exists:
  the test file, the check script, the command, the tool. A Done means line describes the future,
  so its result is not checked, only its means. If a line needs a check that does not exist,
  propose a Scope step that creates it and a Done means line that names it. Do not invent the
  check's pass threshold (see Targets).
- **Conditional steps.** A Scope step of the form "check whether X; if so, do Y" is closed now when
  the check is one or two read-only commands in a place the session can read. Run it and record
  the result, with the command, under "Checked and current" in Agent notes. Then either remove the
  step and anything that hung on it (a second repo, a second PR, a Size count) or make it
  unconditional. If the session cannot read the place, leave the step and say why.
- **Deferred choices.** A Scope or Done means line that says "decide", "state what it does", "if
  needed", "as appropriate", "sensibly" or the like hands a choice to whoever works the ticket.
  Read enough of the code or docs to say what happens if nobody decides, and bring the choice to
  the interview with that as one of the options.
- **Current rules.** For each rule the ticket relies on or changes, read the instruction files
  that apply as they stand today: the global instructions the session has, and the target repo's
  `AGENTS.md` or `CLAUDE.md` (follow a pointer to another file). Where they conflict with the
  ticket or with each other, look for when each changed (`git log -1 --format=%ci -- <file>` in a
  repo you can read) against the ticket's creation date. A conflict is an open decision: do not
  quietly prefer the ticket or one of the files. If you cannot tell when a rule changed, say so.
- **Targets.** A numeric threshold or target (a time, a count, a size) is mine to set, or, in
  forks-only mode with a Head, his ("From a worktree session", under "Forks-only mode"). Do not
  confirm one for me, and do not make up one for a check you propose. Bring it to the interview
  with any measured figures beside it. Only when I decline to set it, or say I cannot yet, write it
  as "proposed, not confirmed" and list it under Needs you in the report.
- **Comment evidence.** When a Scope step depends on evidence that sits in a comment, link to that
  comment from the description (its url from `list_comments`) instead of copying the evidence in.
- **Prerequisites.** Apply the shared rules, "Prerequisites", to each one found in step 1. Then:
  - Each one the shared rules send to a question ("Ask") is an open decision.
  - A missing relation is an add item (`blockedBy`). A stale one, whose blocker is Done or whose
    stated PR has merged, or one that names a ticket that is only an example, is a remove item
    (`removeBlockedBy`), with the evidence.
- **Milestone.** Apply the shared rules, "Milestones": call `list_milestones` for the ticket's
  project and read the milestone `get_issue` gives. Then take the first case that applies:
  - It is Done, Canceled or a Duplicate: leave the field as it is and propose nothing.
  - Its Decisions records "No milestone" and it has none: propose nothing. The report says so.
  - Its Decisions records "No milestone" but it has a milestone: an open decision, to take it out
    or keep it (a keep replaces the "No milestone" line). Nothing changes before the answer.
  - It has no milestone, and the project has no milestones or only finished ones: propose
    nothing. The report says so.
  - It is open, has no milestone, and one fits: setting that milestone is an add item (step 7),
    with its one-line reason.
  - It has no milestone and none fits: leave the field empty, and the report says so. A new
    milestone (its name and one line on what done means) is an open decision, with "leave it
    with none" and "keep it out of milestones" (which records "No milestone") as options. It is
    created only on my yes (with a Head, relayed by him: "From a worktree session").
  - Its goal no longer fits the milestone it has, or that milestone is finished: an open
    decision, to move it (to the milestone that fits, or out of milestones, which records "No
    milestone"), to put it in a new milestone when no other one fits (its name and one line on
    what done means; created only on my yes, relayed by the Head when there is one), or to keep it. Grooming never moves a ticket out of
    a milestone as a routine call.
  - It fits the milestone it has: nothing to do.
- **Other open decisions.** Also collect: a reason in the ticket that checking suggests may be
  false, a Decisions line marked open, an unanswered question in a comment, a missing pull
  condition that only I can supply, a Done means line that is an activity whose result is not
  clear from the ticket, and a Decisions line with no who or no date that the ticket's own text
  does not supply. Do not list a gap you can close yourself from the ticket.

## 4. Size and split

**Size.** Propose small, medium or large, with the count of repos and PRs and one sentence on what
drives it. If a conditional step is still open, give the range ("small; medium if step 5 finds
something"). Size is proposed in the edit list, not asked.

**Points.** Beside the size word, propose story points: one of 1, 2, 3, 5, 8 or 13 (Fibonacci),
with one sentence on what drives them. Points measure the effort for whoever works the ticket, not
its importance. Take them from this table, so they stay comparable across sessions and repos:

| Points | Typical change |
|---|---|
| 1 | a one-line docs or config change |
| 2 | a small change with one test |
| 3 | a change across a few files, with tests |
| 5 | a feature-sized change in one repo |
| 8 | a large change across several modules, with a lot of work in many files |
| 13 | too big to run as one ticket |

Points follow the amount of work, not the number of repos or PRs. Needing more than one PR, PRs in
more than one repo that can merge on their own included, is a split signal (see Split verdict).

As a guide and not a rule, small is typically 1 to 3 points, medium 5, large 8 to 13. With a
range for size, give the points for each end ("small, 2; medium, 5, if step 5 finds something"),
and the estimate takes the higher number; when that is 13, the 13 rule below applies. Points go in
the edit list beside Size, not asked: they are written into the Size section and set in Linear's
estimate field (step 7).

**Split verdict.** Say "no split" with the reason, or propose a split. Propose one when any of
these holds:

- the ticket needs more than one PR, PRs in more than one repo that can merge on their own
  included (the format's rule: a ticket is sized to one PR, so the split files one child ticket
  per PR);
- it mixes a mechanical change with a design choice;
- part of it is blocked and part is not;
- it is large;
- it is pointed above 8 (13);
- one part is risky and the rest is not.

Do not split when the parts must land together to be correct. Any ticket left whole that still needs
more than one PR, by this rule (two repos that must merge together) or by my answer to the split
question, gets a line in Agent notes under "For the engineer": each partial PR links the ticket with
`Refs`, not a closing keyword, as the format's "Linking a PR to a ticket without closing it" says,
so the first merge does not close it, and the PR that completes the ticket uses a closing keyword. A
proposed split names each child: a title in the format, its Done means lines taken from the parent,
its size word and points from the table with one sentence on what drives them, its order, what
blocks what, and one line with its project, milestone (the parent's as the approved edit list leaves
it, a new one included, or none when it is finished), state and labels (`groomed` added once the
split is complete, if the child passes the ready test and its team has an active `groomed` label;
step 7, "Order of writes" item 5).
It also says what happens to the parent: it becomes the first child, or it stays as the parent with
the children under it (`parentId`). When it stays as the parent, write its full replacement
description: Why, a Scope that names the children, Done means, Decisions, and Size ("Split: the
points sit on the children", with its size and points before the split as history). The rest of its text
moves into the children or is dropped, and the replacement shows which. The parent's estimate
follows: the first child's points when it becomes the first child; none when it stays as the
parent (`estimate: null`), so its children's points are not counted twice.

A 13 is never left or filed unsplit without my explicit yes: a ticket pointed 13 always gets a
proposed split (a parent whose points sit on its children is not pointed), its split question says that "no split" keeps it at 13, and no child is proposed
at 13 unless the question names it.

The split is an interview question, never automatic. The proposal is preliminary: the interview
answers may change it, and step 6 settles it. A "no split" verdict becomes an add item under
Decisions: "No split: <reason>. Groomed, <date>."

**Forks-only mode:** a proposed split is a fork and is asked, so a ticket pointed 13 always comes
to me, or, with a Head and from a worktree session, to him through the Director, where keeping it
whole still needs my explicit
yes ("From a worktree session"). The "no split" line reads "No split: <reason>. Decided by dv:groom
(forks-only), <date>." For a ticket pointed 13, "no split" is my answer to that fork, not a routine
call, and is recorded in the fork form (with a Head, my yes as relayed by the Head).

## 5. Scout

Look once, past the ticket's text, at what the change touches and what would make it stick. One
focused pass, not a recursive investigation. Report each item with its evidence (a path and line, a
command's output, a ticket id). Three kinds:

- **In-ticket improvements:** something small that belongs in this ticket and makes its result
  provable or durable: a missing check, a doc that would go stale, a copy of the value the change
  misses (search the repo for every spelling of a value the ticket changes). These become
  edit-list items.
- **Spin-offs:** work the ticket suggests but should not carry: a helper, a follow-up measurement,
  a neighbor with the same flaw. Each is one line: a title in the format, why, the Linear project
  it would go in (found live, as in `dv:ticket` File step 1), its milestone (the groomed ticket's,
  or none when it has none or a finished one; in another project, an existing one that fits there,
  or none), and its state and labels (never `groomed`: a spin-off is drafted, not groomed). Before
  offering one, run
  File step 3's duplicate search for it, reading every page and keeping a tally as step 1's
  overlap search does, and keep any match, with its id and state. A spin-off whose duplicate
  search is incomplete is offered with that said, and is not filed in step 7 until the search
  is run again and finishes.
- **Process observations:** something about how the work is set up that will trip whoever does it:
  a branch name that breaks the repo's rule (compare the ticket's `gitBranchName` with the
  branch-name rule), a rule the ticket's change contradicts, notes or memory files outside the
  repo that hold a copy of what changes. These go into Agent notes under "For the engineer" or
  "After the merge", or become spin-offs.

Cap: at most 3 spin-offs and 5 items in all; if there were more, say so in one line. A `someday`
ticket is never put forward as work to do next. No scouting item is a reason to hold the ticket.
When there is nothing, say "Scouting: nothing found." in one line, and do not pad.

## 6. Interview

First, in your reply, list what you found, shortest first: gaps, stale facts, settled `[assumed]`
markers, neighbors and overlapping work, the milestone (step 3), the size and points, the split
verdict and the scouting items. The overlapping work opens with one tally per search, from step 1
and step 5: its words, pages read and results (for example, "`groom pagination`: 2 pages, 263
results"), with an incomplete search marked as such. Show the split proposal in full here (each
child's title, Done means lines, size and points, milestone, labels, order and blockers, the
parent's estimate, and the parent's full replacement description when it stays as the parent), and
each spin-off's title, reason, project, milestone and any duplicate match.

Then ask every open decision, in rounds of at most 4 questions:

- each open decision from step 3, with what happens today as one option where it applies;
- the split: approve it as shown, change it, or no split. When the split is proposed because the
  ticket needs more than one PR, the question says so and that each child is one PR, and that a
  ticket left whole closes on its first PR's merge unless each partial PR uses `Refs` (the PR that
  completes it uses a closing keyword). When the parent stays as the parent, the question says that
  approving covers both the split and the parent's replacement description shown above. Approving
  a split alone never authorizes removing parent text. For a ticket pointed 13, the question says
  that "no split" keeps it at 13 (step 4);
- each spin-off: file a separate ticket, fold it into this ticket, or drop it. A duplicate match is
  named in the question with its id and state;
- each target that only I can set (step 3).

If there are no open decisions, say so in one line and go to step 7.

After the answers, settle the split. If an answer changes it, show the revised proposal and ask
once more. Each answer becomes an add item under Decisions, "the decision. Who, date", with the
Decisions section added if the ticket has none; an answer that settles a Decisions line marked
open replaces that line. An answer that supplies a pull condition also goes at the end of Why. Who
is my name from `whoami` or the session's instructions, not "me" and not "the user"; the date is
today's date.

An answer that approves a split or files a spin-off is my approval to create those tickets, with
what the proposal showed; do not show a draft and ask again unless I ask to see it. It is not
approval to start the work. A split approval covers the children and the parent's change together:
the two are one unit, filed and edited in step 7 without a second approval.

**Forks-only mode.** Give the findings list as above, and mark each routine call in it with the
option you took. Then ask only the forks, in rounds of at most 4 questions, each starting with its
finding in one sentence; from a worktree session, each fork goes to the Director first ("From a
worktree session: forks go to the Director first", under "Forks-only mode"), and only
those that section sends to me are asked here. If there are no forks, say so in one line, ask nothing
and go to step 7. Each answer to a fork is recorded in the default form, or in the Director form
when the Director answered it, or in the Head form when an approval the Head relayed settled it. Each routine call that "Recording" (under "Forks-only mode")
says to record is recorded in the "Decided by dv:groom (forks-only)" form, and no other is. Your
call to file a
spin-off stands as the approval to create it with what the proposal showed (folding one in is a
fork and is asked), subject to step 5's
rule that a spin-off with an incomplete duplicate search is not filed. A spin-off whose duplicate
search found a match that is open, or Done, and covers the work is not filed: the routine call is
to drop it, with the match's id and state named in the report, and in its Decisions line when the
ticket is edited. With a Canceled match, whether to file it is a fork and is asked. With any
other match, filing it is the routine call, under the rule above. That step 6 decision stands in
for File step 3's duplicate question, as my interview answer stands in for File step 6's draft; if
the duplicate search just before creating finds a match step 6 had not seen, that is a fork: ask
it and hold that filing until the answer comes. If the answer is to file, re-run the duplicate
check and file it under File's rules. On any other answer, do not file it, and name the match in
the report. A split stays a question: my
answer approves the children and the parent's change together, as above.

## 7. Edit

**The edit list.** Number every change, and say for each whether it adds text, or replaces or
removes existing text. It covers:

- corrected stale facts, in place, and settled `[assumed]` markers;
- a new title (set with the `title` field, not a patch) and section renames;
- new Scope steps and Done means lines from step 3, and in-ticket improvements from step 5;
- removed conditional steps and whatever hung on them;
- relations to add (`blockedBy`, `relatedTo`) and to remove (`removeBlockedBy`), with the evidence;
- relations the text itself creates: an item whose text names a ticket id the ticket is not yet
  related to says so ("and relates VIL-N"), since Linear relates any id written in a description
  (shared rules, "Ticket ids in text");
- Size with its points (step 4; for a parent that becomes the first child, that child's size and
  points from the split), written in the Size section and set as the estimate with `save_issue`'s
  `estimate` field (a number), the Decisions lines from the interview, and the no-split line.
  Setting an estimate where there was none is an add item; changing one is a replace item. Linear
  can store a different number from the one sent, with no error: a team whose scale stops at 8
  stores 13 as 8. So compare the estimate each `save_issue` returns, for this
  ticket and for each child, with its points. When they differ, clear that estimate
  (`estimate: null`) so the wrong number is not counted, keep the points in the Size section, and
  say so under Needs you with both numbers: that ticket is not ready until its points are stored, by
  a change to the team's scale (mine) or a split. For a child just filed, clear it with one more
  `save_issue` on that child and read the reply; if the clear fails, stop before changing the
  parent, as for a failed filing ("Order of writes", item 2);
- links to comments that hold evidence a Scope step depends on;
- the milestone (step 3), set with `save_issue`'s `milestone` field: an add item when the ticket
  has none; a replace item when my answer moves it, or a remove item when it takes it out (which
  also adds the "No milestone" Decisions line); a keep that replaces a "No milestone" line; and a
  new milestone I said yes to, created just before the first save that sets it ("Order of
  writes");
- for a split, the children to file and the parent's change (its estimate included), exactly as
  approved;
- Agent notes, which opens with the grooming line ("Groomed <date> <time> <zone> against
  <repo> `<commit>`") and may hold three short lists, each only when it has something in it:
  "Checked and current" (each fact with how it was checked), "For the engineer" (the repo rules
  that bite on this ticket, the branch name to use under the branch-name rule, what not to touch)
  and "After the merge" (follow-ups that are not the worker's: notes to update, a ticket to comment
  on, a re-measurement). When Agent notes already exist, the grooming line goes before their first
  line, and the lists go after their last line;
- the `groomed` label, as its own item, which counts as an item that adds. It is added with
  `addLabels` (never `labels`, which replaces the set) so the ticket's other labels stay, and only
  if the ticket passes the ready test once the other writes have landed ("Order of writes", item 5);
  otherwise it stays off and the report says why. Leave the item out when the ticket already has the
  label. Before proposing it, check with `list_issue_labels` that the ticket's team has an active
  `groomed` label; if it is missing or retired, do not create one: leave the item out and say so in
  the report. This item is the groomed ticket's label only: a split's children get theirs as part of
  the approved split, by the same test per child (item 5), whether or not this item is on the list.

If I decline a relation to a ticket, in the edit list or in the interview, no text you save may
name that ticket's id: name its PR, repo or title instead, and say so in the report.

Propose a rewrite of an activity line only when the result is clear from the ticket. Do not fill
in a who or a date by guessing. Mark anything you add that you could not check with `[assumed]`.

**Approval.** Ask one plain question that names every item number ("Apply items 1 to 9?"). A yes to
a question that names the numbers approves every named item, replacements and removals included.
I may answer with a subset of numbers instead. A bare yes to a question that names no numbers
approves only the items that add.

**Forks-only mode:** do not ask this question. Show the numbered edit list, then apply every item
under "Order of writes" and "Patches" below, which still hold in full; the `groomed` label item is
applied with the rest the same way, under item 5's ready test, also when it is the only item (last
Rules bullet). My answers to
the fork questions, including a split approval, were the approval for what they decided. Do not
offer the whole-description replacement, which needs its own question; use patches. For a
description that has text but no headings, do what "Patches" says: leave it, show the sections you
would add as text in the report, say I will edit it in Linear, and list that item as not landed.
Other items still apply.

**Whole-description replacement.** When the interview answers change three or more sections, you
may offer this instead of patches: show the complete new description, say that the old one stays
in Linear's history, and ask one plain question to replace the whole description. Relations, the
title, the `groomed` label and filings stay numbered items beside it. A no leaves the description
exactly as it was.
Just before saving, read the ticket again; if its description is no longer the one the
replacement was built from, do not save: say what changed and ask again.
Patches stay the default; three changed sections allow the offer and do not decide it.

**Order of writes.**

A new milestone I said yes to is created as the shared rules' "Creating an approved milestone"
says: right before the first save below that sets it (the first child or spin-off filed with it in
item 2, or the groomed ticket's change in item 4), after the re-reads that come before that save
(item 1's re-read of the parent, the duplicate re-run before that filing, item 4's re-read, and the
milestone re-read below). If it cannot be created, or those rules send it back to me, stop: write
nothing more, list under Needs you the tickets already filed and the items not applied, and leave
the `groomed` label off (item 5). If the save that sets it fails, follow those rules' "A failed
save after it" as well as item 2's report for a failed filing: no retry, which overrides item 4's
retry once for that save.

The milestone step 3 settled (the one the groomed ticket will have after the approved edit list:
kept, set or none) is checked again under the shared rules' "Re-read before the save": just before
the first save below that uses it, the first child or spin-off filed with it (item 2), and again
just before item 4's save, each time before any new milestone is created. If that rule sends it
back to me, stop as above: write nothing more, list under Needs you the tickets already filed and
the items not applied, and leave the `groomed` label off (item 5).

1. **A split never loses work.** Linear cannot create several tickets and edit another in one
   step, so a split can fail part way. Order it so that a failure can only leave work in two
   places, never in none: file the children first, and change the parent last. Before filing the
   first child, read the parent again and compare its description with the one the split was
   approved on; if it changed, file nothing, say what changed and ask again.
2. **File approved children and spin-offs.** Read `dv:ticket`'s `SKILL.md` (`../ticket/SKILL.md`
   from this skill's directory), section "File", and create each with its rules: project found live
   (a child takes the parent's project), the milestone (a child takes the parent's, and a spin-off
   filed in the groomed ticket's project takes the groomed ticket's, as the approved edit list
   leaves it, a new one included, with none when that is none or finished; a spin-off filed in
   another project takes the existing milestone File step 2b picks there, or none; this item
   creates no milestone itself, and an approved new one is created as the paragraph above says;
   this overrides File step 2b), labels from the team, the format, facts checked or marked
   `[assumed]`, Backlog with a pull condition unless it can start now, the re-run of the duplicate
   searches just before creating, and `save_issue`. My interview answer stands in for File step 6's
   draft and question. Set each one's relations in the `save_issue` call that creates it:
   `parentId` for a child under a parent that stays, `blockedBy` for a child that waits on another
   child or for any ticket whose pull condition names an open ticket (unless File mode already sets
   it), and `relatedTo` the groomed ticket for a spin-off, unless the spin-off is blocked by it
   (shared rules, "Prerequisites": one relation per pair). Set each child's approved points with
   `estimate` in that same call, and write its size and points in its Size section (File step 4
   leaves Size for grooming, and this is its grooming); this overrides File's rule against setting
   an estimate unasked. A spin-off gets no estimate: it is pointed when it is groomed. Do not put
   `groomed` on any filing here: a split's child may get it in item 5, under its ready test, and a
   spin-off never does, since it is drafted, not groomed, and `dv:director-mode` skips grooming a
   ticket that has the label. If a filing fails or returns an error, stop: leave the parent as it
   is (it still holds all the work) and do not adopt any ticket id you did not get back from
   `save_issue`. The create may have landed, so search the project for the title and list what you
   find beside the tickets that exist and the draft of each that may not, under Needs you, for me
   to settle. Delete nothing.
   **Forks-only mode:** the routine call to file a spin-off stands in for my interview answer.
3. **Never write a ticket id that does not exist yet.** Write a child's or spin-off's id into the
   groomed ticket only after the `save_issue` call that created it, using the id it returned.
4. **Then change the groomed ticket.** For a split, the parent's approved change (the reduced
   description with Scope naming the children by id, or its reduction to the first child's scope)
   goes in one `save_issue` call with all its patches and its estimate (step 4), which Linear
   applies all or none; this is the one exception to applying patches one at a time. Just before building it, read the ticket
   again and compare its description with the one the split was approved on: if it changed, do not
   save and change nothing more. Say what changed, and list the tickets already filed with their
   ids and relations under Needs you. Any change to them, or a revised split, is a new request. If the call returns an error, read the ticket before
   doing anything else, because a save can land even when the reply is an error: if the change is
   there, go on; if not, retry once; if it still is not there, stop and say under Needs you that
   the children exist and the parent still carries their work. Then apply the rest of the approved
   items.
5. **The `groomed` label goes on last, and only on a ticket grooming left ready.** If step 7 stopped
   before this item for any reason (items 1, 2 including a failed estimate clear, or 4, or a patch
   that could not be placed), leave the label off every ticket and say so in the report. Otherwise
   read the groomed ticket again with `get_issue`, and each child this run filed, and give each the
   ready test: step 8 item 1 would call it ready, setting aside its workflow state, what it waits on
   (blockers, a pull condition) and, for a parent that stays as the parent, that its work sits in
   its children. A ticket fails the test when grooming left a gap: a needed fix I declined or that
   did not land (such as an item left for me to edit in Linear), an overlap or duplicate search that
   did not finish, a Done means line that cannot be proved, a target not confirmed, or points Linear
   did not store. Add `groomed` with `addLabels` (File step 2 allows it on a child) to each ticket
   that passes, when its team has an active `groomed` label, and to the groomed ticket only when its
   edit-list item was approved (in forks-only mode, applied). A ticket that fails keeps no new
   label, and the report names its gap. The label writes are separate calls, so they can stop part
   way, and a call can land even when it returns an error. So after the label writes, or after an
   error during them, read back with `get_issue` the groomed ticket and every child this run filed,
   and report each one's labels as read (step 8). Name under Needs you each ticket this item meant
   to label that lacks `groomed` after the read-back: `dv:director-mode` skips grooming a ticket
   that has the label.

**Patches.** Edit with `patch` operations on `save_issue` (`replace`, `insert_before`,
`insert_after`, `replace_range`, and `append` for an empty description), not by sending the whole
description again, unless the whole-description replacement was approved. Apply them one at a time,
except a split's parent change (above). After any error from `save_issue`, read the ticket before
retrying: the edit may have landed.
To add a section, use `insert_after` on the last line of the section above it, so it lands before
the Agent notes; a missing first section goes in with `insert_before` on the first heading line.
Copy each anchor from the text `get_issue` just returned, from inside a section or a heading line
and not from the `>>>` lines; it must match exactly once. If one fails, read the ticket again and
rebuild the patch. If a patch cannot be placed, stop, say which items landed and which did not, and
leave the rest.

An empty description takes the new sections with `append`. A description that has text but no
headings (plain text, or only an Agent notes block) has no safe place to anchor a patch: leave it,
show me the sections you would add as text, and say I will edit it in Linear (or offer the
whole-description replacement). Other approved edits, such as the title, still apply.

Relations go on `save_issue` with `blockedBy`, `relatedTo` and `removeBlockedBy`. Do not change the
state, labels, project, milestone, priority or assignee unless I ask, or unless I chose that change
in an interview answer. The milestone also changes as its approved edit-list item (in forks-only
mode, the routine call to put a ticket that has none in one that fits). The one exception among
labels is `groomed`: on the groomed ticket as its edit-list item, approved with the others (in
forks-only mode, applied with them), and on a split's children, in both cases only as "Order of
writes" item 5's ready test allows; every other label change still needs my request or an interview
answer. Set the estimate only to the points in the edit list (step 4) or as the approved split sets
it, and clear it only when Linear stored a different number (the edit list). Change labels with
`addLabels` and `removeLabels`, since `labels` replaces the whole set.

## 8. Report

Run this step whatever the answer to the edit list was. Judge the ticket as it now stands; read it
again with `get_issue`, relations included, if anything was written. Report relations as they now
stand, not as the edit list planned them, and name any that Linear added because the text names
an id. Keep it short and in this order, following my own
reply-format rules when the session's instructions give any:

1. **Ready or not.** Name the ticket as a markdown link (the url from `get_issue`; the bare id if
   none came back). Ready means no gaps, Done means lines that can be proved, nothing it waits on,
   every overlap search finished (step 1), no needed fix declined or not landed, no duplicate search
   left unfinished, no target unconfirmed (with a Head, a fork on its way forward counts as
   settled, except anything under `dv:director-mode`'s "What no default decides": "From a worktree
   session"), and the team's backlog or ready-to-start state as
   `list_issue_statuses` names them. A started, finished or canceled ticket is not ready to start.
   After a split, name the child that is ready and the one that comes first, as links; do not call
   the parent ready when the work is in its children. A ticket whose points Linear did not store
   (step 7) is not ready. When not ready, name what it lacks or waits on. The same judgment, setting
   aside state and what the ticket waits on, is the ready test that decides the `groomed` label
   (step 7, "Order of writes" item 5).
2. **Needs you:** what only I can do or decide: a target proposed and not confirmed, an item I did
   not approve that still matters, a repo the session could not read, an overlap or duplicate search
   that did not finish (with its words, so it can be run again), a ticket item 5 meant to label that
   lacks `groomed` after the read-back, a ticket that already had `groomed` but is not ready now
   (step 7, "Order of writes" item 5). Left out when empty. With a Head, in forks-only mode from
   a worktree session, this list reports only: what needs a decision goes to the Director, as
   "From a worktree session" says.
3. One line each: size and points, with the estimate `get_issue` now shows; the milestone as
   `get_issue` now shows it, or "no milestone" with why; split verdict; what
   changed in the ticket ("text unchanged" when only the label landed, "nothing changed" when
   nothing did); the `groomed` label as read back: added, already there, or not added and why (not
   approved, the team has no active `groomed` label, step 7 stopped before it, the ticket is not
   ready and the gap that keeps it so, or the write failed); spin-offs and children filed, as links,
   each child with the estimate its `save_issue` returned and its labels as read back, or "not
   labelled" with the same reasons; what was not checked; the branch to work it on.

Do not ask whether to start the work and do not start it: starting is a separate request from me.

**Forks-only mode:** under item 3, "what changed in the ticket" lists each edit-list item that
landed, one line each, and any that did not (step 7 stops on a failed write). End the report
with a short list headed "Decided without asking", one line per routine call that "Recording"
says to record ("<decision>: <option taken>"), the same calls recorded under Decisions (when the
ticket's text is left unchanged under the last Rules bullet, they are listed and not recorded);
when there were none, "Decided without asking: none."

## Rules

- This skill is for Linear. Do not open GitHub issues.
- Nothing is created or edited in Linear before I approve it. **Forks-only mode** is the exception:
  step 7 applies its edit list without an approval question, and a routine call to file a
  spin-off counts as my approval of it.
- Edit only the groomed ticket, and a child this run filed only to clear an estimate Linear stored
  wrong (step 7) or to add its `groomed` label ("Order of writes" item 5). Create only the children
  and spin-offs I approved, and a milestone only on my yes to it. Do not edit or comment on any
  other ticket; a follow-up on a neighbor goes under "After the merge" or becomes a spin-off.
- No file edits, branches or commits: grooming reads repos and writes only to Linear.
- Do not put secrets or credentials in a ticket.
- A ticket with nothing stale, open or missing, that already has its Size with points and an
  estimate that matches them (a parent whose points sit on its children has none, and is not
  pointed), and is not pointed 13 without a recorded yes to keeping it unsplit, keeps its text as it
  is: say in one line that its text needs no edits, and propose an edit list that holds only the
  `groomed` label item (step 7) and, when step 3 sets one, the milestone item, asked and applied as
  step 7 says, the label under item 5's ready test (in forks-only mode, applied without the
  question). When that leaves the list empty (the ticket has the label or the team has none, and
  step 3 sets no milestone), propose no edits and go to step 8. The no-split line and the
  grooming line in Agent notes are added only alongside other edits to the text; the label and
  milestone items alone do not bring them in.
