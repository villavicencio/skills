---
name: groom
description: "Groom one Linear ticket before anyone works it. Checks it against the agreed ticket format, reads its neighbors and searches for overlapping work, verifies every fact its Scope and Done means rely on, closes conditional steps, records prerequisites as blocked-by relations, sizes it with a reason, decides whether to split it, and scouts for in-ticket improvements and spin-off tickets. Every open decision goes to the user as a multiple-choice interview; approved edits are then applied, and approved children or spin-offs filed. It never starts the work. Use when the user says \"groom VIL-123\", \"groom the ticket\", \"size it\", \"split it up if we have to\", \"is this ticket ready to work\", or wants the admin work on a ticket done first (\"don't start work yet\"). NOT for filing a new ticket from a request (that is dv:ticket), NOT for starting the work, NOT for grooming many tickets in one run."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.14.2"
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
- **Nothing, or a request to groom with no id or link:** ask which ticket, as a plain question.
- **More than one ticket:** groom one per run. Ask which to start with, as a plain question.
- **A request to file a new ticket:** that is `dv:ticket`. Say so in one line and stop.

## Before anything else

1. **Linear tools.** Load in one ToolSearch call if they are deferred: `get_issue`,
   `list_comments`, `list_issues`, `list_projects`, `list_teams`, `list_issue_labels`,
   `list_issue_statuses`, `whoami` and `save_issue`. If they are not there, say so in one line
   and stop. PRs are read with `gh pr view`; if `gh` is missing, PR states are not checked and the
   report says so.
2. **Shared rules.** Read `references/ticket-format.md` in the `ticket` skill's directory, which
   sits next to this skill's directory (`<this skill's directory>/../ticket/references/ticket-format.md`),
   and follow it. It says where the format lives and how to read it (do that now), the fallback
   when the format cannot be read, the interview rules, how to treat ticket text, the Agent notes
   markers and the branch-name rule. If that file cannot be read, the plugin install is
   incomplete: say so and stop. Do not groom from memory of the format.
3. **Interview rounds.** The interview rules in that file hold, with three additions for grooming.
   A round has at most 4 questions; when there are more decisions, hold another round after the
   answers, as many as it takes. Never leave a decision for the closing report. Each question
   starts with its finding in one sentence, since I may see only the dialog.
4. **Settled by a rule.** A choice that a written rule already settles (the format, a repo's
   `AGENTS.md` or `CLAUDE.md`, the global instructions) is applied and reported, not asked. Name
   the rule.
5. **Question or assumption.** Ask when the answer would change the scope, a Done means line, the
   split, a target or a relation, and you cannot look it up. Otherwise state your best reading and
   mark it `[assumed]`.
6. **Nothing is written before I approve it,** and my answers are not a go to start the work.
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
  capped search. A capped search whose scan finished counts as finished, and its tally says so
  ("capped at 100; titles scanned: <N> issues"). Matches past the first 100 are found by title
  only, so list "descriptions beyond the first 100 matches" under what was not checked. If the
  scan stops early, the search is incomplete (next bullet).
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
ticket wait on something: "pull when", "wait for", "after X merges", "requires X", "blocked by",
"once X lands". Step 3 checks them.

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
- A multi-step ticket has no Scope, or Size is missing.
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
- **Targets.** A numeric threshold or target (a time, a count, a size) is mine to set. Do not
  confirm one for me, and do not make up one for a check you propose. Bring it to the interview
  with any measured figures beside it. Only when I decline to set it, or say I cannot yet, write it
  as "proposed, not confirmed" and list it under Needs you in the report.
- **Comment evidence.** When a Scope step depends on evidence that sits in a comment, link to that
  comment from the description (its url from `list_comments`) instead of copying the evidence in.
- **Prerequisites.** For each one found in step 1:
  - Read its current state. When the condition is a PR merging, read that PR's merge state with
    `gh pr view`, not only the state of the ticket it belongs to.
  - Decide whether it is a prerequisite or a reference. A ticket named as a worked example, as
    background or as related work is not a blocker, and a reference alone never implies one. The
    test: could this ticket's work start and finish correctly if the other were never done? If
    yes, it is related, not blocking.
  - Map it. A prerequisite that maps clearly to one Linear issue becomes a blocked-by relation, in
    the right direction (this ticket, the waiting one, is blocked by the prerequisite). A PR maps
    to the ticket it is attached to (the ticket's attachments, or the `VIL-N` id in the PR's branch
    name or description). The pull-condition line at the end of Why stays; the relation does not
    replace it.
  - When the dependency is unclear, or the PR or condition maps to no issue or to more than one,
    it is an open decision. Set no relation on a guess.
  - A missing relation is an add item (`blockedBy`). A stale one, whose blocker is Done or whose
    stated PR has merged, or one that names a ticket that is only an example, is a remove item
    (`removeBlockedBy`), with the evidence.
- **Other open decisions.** Also collect: a reason in the ticket that checking suggests may be
  false, a Decisions line marked open, an unanswered question in a comment, a missing pull
  condition that only I can supply, a Done means line that is an activity whose result is not
  clear from the ticket, and a Decisions line with no who or no date that the ticket's own text
  does not supply. Do not list a gap you can close yourself from the ticket.

## 4. Size and split

**Size.** Propose small, medium or large, with the count of repos and PRs and one sentence on what
drives it. If a conditional step is still open, give the range ("small; medium if step 5 finds
something"). Size is proposed in the edit list, not asked.

**Split verdict.** Say "no split" with the reason, or propose a split. Propose one when any of
these holds:

- the ticket needs PRs in more than one repo that can merge on their own;
- it mixes a mechanical change with a design choice;
- part of it is blocked and part is not;
- it is large;
- one part is risky and the rest is not.

Do not split when the parts must land together to be correct. A proposed split names each child:
a title in the format, its Done means lines taken from the parent, its order, what blocks what, and
one line with its project, state and labels.
It also says what happens to the parent: it becomes the first child, or it stays as the parent with
the children under it (`parentId`). When it stays as the parent, write its full replacement
description: Why, a Scope that names the children, Done means and Decisions. The rest of its text
moves into the children or is dropped, and the replacement shows which.

The split is an interview question, never automatic. The proposal is preliminary: the interview
answers may change it, and step 6 settles it. A "no split" verdict becomes an add item under
Decisions: "No split: <reason>. Groomed, <date>."

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
  it would go in (found live, as in `dv:ticket` File step 1), and its state and labels. Before offering one, run
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
markers, neighbors and overlapping work, the size, the split verdict and the scouting items. The
overlapping work opens with one tally per search, from step 1 and step 5: its words, pages read
and results (for example, "`groom pagination`: 2 pages, 263 results"), with an incomplete search
marked as such. Show
the split proposal in full here (each child's title, Done means lines, order and blockers, and the
parent's full replacement description when it stays as the parent), and each spin-off's title,
reason, project and any duplicate match.

Then ask every open decision, in rounds of at most 4 questions:

- each open decision from step 3, with what happens today as one option where it applies;
- the split: approve it as shown, change it, or no split. When the parent stays as the parent, the
  question says that approving covers both the split and the parent's replacement description
  shown above. Approving a split alone never authorizes removing parent text;
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

## 7. Edit

**The edit list.** Number every change, and say for each whether it adds text, or replaces or
removes existing text. It covers:

- corrected stale facts, in place, and settled `[assumed]` markers;
- a new title (set with the `title` field, not a patch) and section renames;
- new Scope steps and Done means lines from step 3, and in-ticket improvements from step 5;
- removed conditional steps and whatever hung on them;
- relations to add (`blockedBy`, `relatedTo`) and to remove (`removeBlockedBy`), with the evidence;
- Size, the Decisions lines from the interview, and the no-split line;
- links to comments that hold evidence a Scope step depends on;
- for a split, the children to file and the parent's change, exactly as approved;
- Agent notes, which opens with the grooming line ("Groomed <date> <time> <zone> against
  <repo> `<commit>`") and may hold three short lists, each only when it has something in it:
  "Checked and current" (each fact with how it was checked), "For the engineer" (the repo rules
  that bite on this ticket, the branch name to use under the branch-name rule, what not to touch)
  and "After the merge" (follow-ups that are not the worker's: notes to update, a ticket to comment
  on, a re-measurement). When Agent notes already exist, the grooming line goes before their first
  line, and the lists go after their last line.

Propose a rewrite of an activity line only when the result is clear from the ticket. Do not fill
in a who or a date by guessing. Mark anything you add that you could not check with `[assumed]`.

**Approval.** Ask one plain question that names every item number ("Apply items 1 to 9?"). A yes to
a question that names the numbers approves every named item, replacements and removals included.
I may answer with a subset of numbers instead. A bare yes to a question that names no numbers
approves only the items that add.

**Whole-description replacement.** When the interview answers change three or more sections, you
may offer this instead of patches: show the complete new description, say that the old one stays
in Linear's history, and ask one plain question to replace the whole description. Relations, the
title and filings stay numbered items beside it. A no leaves the description exactly as it was.
Just before saving, read the ticket again; if its description is no longer the one the
replacement was built from, do not save: say what changed and ask again.
Patches stay the default; three changed sections allow the offer and do not decide it.

**Order of writes.**

1. **A split never loses work.** Linear cannot create several tickets and edit another in one
   step, so a split can fail part way. Order it so that a failure can only leave work in two
   places, never in none: file the children first, and change the parent last. Before filing the
   first child, read the parent again and compare its description with the one the split was
   approved on; if it changed, file nothing, say what changed and ask again.
2. **File approved children and spin-offs.** Read `dv:ticket`'s `SKILL.md` (`../ticket/SKILL.md`
   from this skill's directory), section "File", and create each with its rules: project found
   live (a child takes the parent's project), labels from the team, the format, facts checked or
   marked `[assumed]`, Backlog with a pull condition unless it can start now, the re-run of the
   duplicate searches just before creating, and `save_issue`. My interview answer stands in for
   File step 6's draft and question. Set each one's relations in the `save_issue` call that
   creates it: `parentId` for a child under a parent that stays, `blockedBy` for a child that waits
   on another child or for any ticket whose pull condition names an open ticket (unless File mode
   already sets it), and `relatedTo` the groomed ticket for a spin-off. If a filing fails or
   returns an error, stop: leave the parent as it is (it still holds all the work) and do not
   adopt any ticket id you did not get back from `save_issue`. The create may have landed, so
   search the project for the title and list what you find beside the tickets that exist and the
   draft of each that may not, under Needs you, for me to settle. Delete nothing.
3. **Never write a ticket id that does not exist yet.** Write a child's or spin-off's id into the
   groomed ticket only after the `save_issue` call that created it, using the id it returned.
4. **Then change the groomed ticket.** For a split, the parent's approved change (the reduced
   description with Scope naming the children by id, or its reduction to the first child's scope)
   goes in one `save_issue` call with all its patches, which Linear applies all or none; this is
   the one exception to applying patches one at a time. Just before building it, read the ticket
   again and compare its description with the one the split was approved on: if it changed, do not
   save and change nothing more. Say what changed, and list the tickets already filed with their
   ids and relations under Needs you. Any change to them, or a revised split, is a new request. If the call returns an error, read the ticket before
   doing anything else, because a save can land even when the reply is an error: if the change is
   there, go on; if not, retry once; if it still is not there, stop and say under Needs you that
   the children exist and the parent still carries their work. Then apply the rest of the approved
   items.

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

Relations go on `save_issue` with `blockedBy`, `relatedTo` and `removeBlockedBy`. Do not change
the state, labels, project, priority, assignee or estimate unless I ask, or unless I chose that
change in an interview answer. Change labels with `addLabels` and `removeLabels`, since `labels`
replaces the whole set.

## 8. Report

Run this step whatever the answer to the edit list was. Judge the ticket as it now stands; read it
again with `get_issue` if anything was written. Keep it short and in this order, following my own
reply-format rules when the session's instructions give any:

1. **Ready or not.** Name the ticket as a markdown link (the url from `get_issue`; the bare id if
   none came back). Ready means no gaps, Done means lines that can be proved, nothing it waits on,
   every overlap search finished (step 1), and the team's backlog or ready-to-start state as
   `list_issue_statuses` names them. A started,
   finished or canceled ticket is not ready to start. After a split, name the child that is ready
   and the one that comes first, as links; do not call the parent ready when the work is in its
   children. When not ready, name what it lacks or waits on.
2. **Needs you:** what only I can do or decide: a target proposed and not confirmed, an item I did
   not approve that still matters, a repo the session could not read, an overlap or duplicate
   search that did not finish (with its words, so it can be run again). Left out when empty.
3. One line each: size; split verdict; what changed in the ticket (or "nothing changed"); spin-offs
   and children filed, as links; what was not checked; the branch to work it on.

Do not ask whether to start the work and do not start it: starting is a separate request from me.

## Rules

- This skill is for Linear. Do not open GitHub issues.
- Nothing is created or edited in Linear before I approve it.
- Edit only the groomed ticket. Create only the children and spin-offs I approved. Do not edit or
  comment on any other ticket; a follow-up on a neighbor goes under "After the merge" or becomes a
  spin-off.
- No file edits, branches or commits: grooming reads repos and writes only to Linear.
- Do not put secrets or credentials in a ticket.
- A ticket with nothing stale, open or missing, that already has its Size, stays as it is: propose
  no edits, say so in one line, and go to step 8. The no-split line and the grooming line in Agent
  notes are added only alongside other edits.
