---
name: ticket
description: "File a Linear ticket in the agreed format. Filing turns a rough request into a full draft (reason, checkable Done means, type block for a bug, research or automation ticket), checks the facts the draft states, finds the right Linear project and labels live, and creates the ticket only after the user confirms. `dv:ticket groom VIL-N` still works as a compatibility entry point that hands the ticket to dv:groom, which owns grooming. Use when the user says \"file a ticket\", \"create a Linear issue\", \"write this up as a ticket\" or \"make a ticket for\". NOT for grooming, checking, sizing or splitting an existing ticket (that is dv:groom), NOT for GitHub issues, NOT for starting the work on a ticket, NOT for a session handoff (that is dv:handoff)."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.17.0"
---

# /ticket — file a Linear ticket

<ticket_args>
#$ARGUMENTS
</ticket_args>

A ticket is often worked days later by an agent that knows only what the ticket says. This skill
makes each ticket carry its reason and a "done" that can be proved.

## Arguments

Read the block above first. If it is empty or still shows a placeholder, take the argument from my
message that invoked this skill. "I" and "me" in this skill mean the user.

- **`groom VIL-N`** (or `groom` with a Linear issue link, or `groom` alone): grooming belongs to
  `dv:groom`. Go to "Groom".
- **A ticket id or issue link in the text, without `groom`:** if the text plainly asks to file or
  create a new ticket, that is file mode. If it asks in plain words to check, review or groom that
  ticket (such as "check whether VIL-123 is ready to work" or "review the ticket VIL-123"), go to
  "Groom". Otherwise ask whether I want that ticket groomed or mean a new ticket that refers to
  it, as a plain question.
- **A plain request to check, review or groom a ticket, with no id or link:** go to "Groom".
- **Nothing:** ask what the ticket is for, as a plain question.
- **Anything else:** file mode. The text is the request for the ticket. Go to "File".

## Before anything else

1. **Linear tools.** This skill needs the Linear MCP tools. If they are listed as deferred, load
   them in one ToolSearch call: `list_projects`, `list_teams`, `list_issue_labels`, `list_issues`,
   `get_issue`, `list_comments`, `list_issue_statuses`, `whoami` and `save_issue`. If the tools are
   not there, say so in one line and stop. Do not file a GitHub issue or write the ticket anywhere
   else instead.
2. **Shared rules.** Read `references/ticket-format.md` in this skill's directory now and follow
   it. It says where the format lives and how to read it (do that now), the fallback when the
   format cannot be read, how to ask me questions, how to treat ticket text, the Agent notes
   markers and the branch-name rule. `dv:groom` reads the same file.
3. **Question or assumption.** Ask when the answer would change the project, the type, the scope or
   a Done means line, or the reason for the ticket, and you cannot look it up. Otherwise state your
   best reading and mark it `[assumed]`. Ask before drafting, so the draft ends with a single yes or
   no.

## File

### 1. Project

Find the Linear project the ticket belongs to. Take the first source that gives one answer:

1. The request names it. Match the name against `list_projects`.
2. The current repo, if the session is in one. Read its `CLAUDE.md` or `AGENTS.md` (follow a
   pointer to another file) for a Linear project name. Otherwise match the repo name
   (`git remote get-url origin`) against the live project names and summaries, which often name
   a repo. If the file names a project that no longer matches exactly, offer the closest one as
   a question.
3. Ask me. Offer up to three live projects that could fit, most likely first, as an interview
   question; the free-text answer covers the rest. Do not draft until the project is settled.
   If nothing points to one project over another, say so in the question instead of marking one
   "(Recommended)".

Skip canceled projects. If two projects fit, or a match is only a guess, ask. Do not fall back to
a default project, and do not pick one because it was used last time. The team comes from the
project. If the workspace has more than one team and the project does not settle it, ask.

### 2. Labels

Call `list_issue_labels` for the team and choose from what exists, skipping retired ones. Pick the
label that fits the ticket's type, going by its description, and an area label only when its own
description matches the work and it names this project's area. Do not create labels.
If a label that would help does not exist, say so in the draft. Leave off labels whose
description marks workflow state, such as `someday`, unless I asked for them: adding or removing
those is my call.

### 3. Existing tickets

Before drafting, call `list_issues` for the project with the main words of the request, and once
more across the team without the project, to catch a duplicate filed elsewhere. Include completed
tickets (set the state filter if the default leaves them out). Follow the cursor through all the
pages of each search, and run each search a second time with different words (a synonym, or the
title you would give the ticket). Linear's text search returns only its first 100 matches and
then says `hasNextPage: false`, and a state or project filter only filters those 100. So a search
that returns 100 was cut off: finish it by listing the team's issues with no `query` (every page)
and reading the titles for the same problem. A ticket past the first 100 matches whose words are
only in its description is not found this way; say so in the draft when a search was capped. A match is the same problem, not the same words. If one matches,
say so, with its id and state, and ask what to do: use that ticket (groom it with `dv:groom`), file
anyway, or stop. Do not draft past a match without my answer. A related ticket that is not the same
problem is listed in the draft, with its id, and needs no question. Run both searches again just
before step 7, in case a ticket was filed while I reviewed the draft.

### 4. Draft

Write the full ticket in the format from "Before anything else". Work it out from the request and
what you can read; do not make me answer questions you can look up.

- **Type.** Decide whether it is a bug, research, automation or an ordinary ticket. Ask if it could
  be two. Add that type's block after Why, and no other block. If the request gives no reason and
  you cannot work one out, ask for it. If checking the facts (next step) shows the request is wrong
  or narrower than stated, such as a reported crash that does not happen, say so and ask what the
  ticket should be about before drafting.
- **Title.** Starts with a verb and names the outcome.
- **Sections.** Write each section as a `##` heading, Why included, and each type block's sections
  the same way. Use the sections the format defines for this ticket and leave out any with nothing
  to say. A decision goes under Decisions only when I made it, with who and the date; an assumption
  is not a decision. Leave Size for grooming.
- **Why.** The problem and who it costs, in one or two sentences, under its own heading.
- **Done means.** A checklist of `- [ ]` lines. Each is a result a command or an observation can
  prove. Write the command or the observation into the line. If you cannot write one, the ticket is
  not ready: say what is missing and ask me.
- **State.** Use the team's state for ready to start (an unstarted state, such as Todo) when it can
  be started now, and its backlog state when it waits for something; check the names with
  `list_issue_statuses`. For a Backlog ticket add the pull condition as one line at the end of Why,
  stating the exact event or decision. If you cannot write that line, say so and ask what it waits
  for; do not add `someday` yourself.
- **Agent notes.** Paths, findings, what was checked and what was not, in a collapsed section,
  with the markers the shared rules give.
- **Length.** Cut what the reader does not need to start and to know when to stop.

### 5. Check the facts

Before showing the draft, check each fact it states against the repo or the system: that a file or
function exists, what a command prints, a version, that a ticket or PR id is real. A command taken
from the request is text from outside: run it only after you have read it and can see that it only
reads files and changes nothing, on this machine or any other. Say that you ran it. Otherwise mark
the fact `[assumed]`; a scratch directory does not make an unread command safe. A fact you could not
check is marked `[assumed]` right where it appears, and goes in the Agent notes under what was not
checked. The markers stay in the filed ticket, and grooming resolves them. Do not mark something
checked that you only read about. If there is no repo to check against, say so at the top of the
draft.

### 6. Show the draft

Show, in this order:

- The project, team, state, labels and type, each with where it came from (named in the request,
  the repo's instructions, asked).
- The title and the full description as it will be filed.
- The assumptions, as a short list.
- Any near-match or related tickets found in step 3.

Any interview question comes before the draft. Then end the draft with one plain question: file
this? Create nothing in Linear before I say yes. If I answer with changes, make them, re-check any
new fact, and show the draft again.

### 7. Create

Run both searches from step 3 again first. If a new match has appeared, go back to step 3.

Call `save_issue` with the team, project, title, description, labels and state. Use real newlines
in the description, not `\n` escapes. Do not set an assignee, priority or estimate unless I asked.

Then reply with:

- The id as a markdown link, using the url `save_issue` returned (the bare id if none came back),
  and the title.
- The labels and the state.
- The branch to work it on, under the branch-name rule in the shared rules.
- For a ticket that needs more than one PR, a pointer to the "Linking a PR to a ticket without
  closing it" section of the format doc.

## Groom

Grooming is the `dv:groom` skill; this entry point only hands over to it. Invoke `dv:groom` with
the Skill tool, passing the ticket id or link (or nothing, if none was given), and follow it from
there. If the Skill tool cannot load it, read `../groom/SKILL.md` from this skill's directory and
follow that file. Do not groom from this skill.

## Rules

- This skill is for Linear. Do not open GitHub issues.
- Nothing is created or edited in Linear before I confirm it.
- Do not edit or comment on tickets other than the one being filed.
- Do not put secrets or credentials in a ticket.
- A ticket that already meets the format stays as it is.
