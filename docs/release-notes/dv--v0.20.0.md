# dv — v0.20.0

Minor release. A worktree session running `dv:manager-mode` now handles routine PR work without
asking me and sends the Director short "highlights", and `dv:ticket` may file without my
confirmation in two narrow cases. The other thirteen skills have no behaviour changes; their
version moves to `0.20.0` only because the suite is released as one plugin.

Numbering: 0.20.0 follows 0.19.0, which made `dv:manager-mode` refuse to run a ticket's work in the
main checkout.

Why: I want to follow ticket work day to day like a highlights reel, without being asked to approve
routine things. Before this, the manager brought me trade-offs the brief had not settled,
`dv:ticket` would not file a spin-off until I said yes, and nothing told me a ticket's big moments
unless I asked (VIL-916).

## Changed

- **`dv:manager-mode`, "Decisions and escalation": routine calls the session makes without
  asking me.** Each is reported as a highlight. The manager never edits files, so an update is a
  hire.
  - **Update a stale PR.** When the Director says the ticket's PR is behind the default branch, or
    `gh` shows `BEHIND`, the manager hires an engineer to merge the default branch into the PR
    branch and push normally, with no rebase and no force push, so nothing on the remote can be
    overwritten. In a repo that versions its releases, the engineer bumps the version. MergeWren
    must pass the new head before the PR goes back to the Director.
  - **Review findings.** An engineer fixes or declines each MergeWren finding and pushes again,
    under the "Fix rounds" rules in dotfiles `docs/agents/code-review.md`. After two fix rounds the
    open list goes to me.
  - **Spin-offs.** The session files a spin-off of its own ticket with `dv:ticket`, under its
    exception (a).
  - Scope changes, design forks, anything destructive and anything the project lists as needing
    approval still go to me. "Design forks" is now named in that line.
- **`dv:manager-mode`: a new "Highlights" section.** At each big moment the session sends the
  Director a one- or two-line "no reply needed" message: a ticket started, a PR opened, MergeWren
  passed or found something, a blocker or a decision waiting on me, and each routine call above.
  The Director is the home session in the main checkout, found with ListAgents and messaged with
  SendMessage.
  - **The handoff of a passed PR stays as it was** (its "What you do yourself" bullet is unchanged).
    The Highlights section says it goes in the same short format, and asks for a one-line reply
    because the Director must act on it.
  - **No reachable Director.** The session says so in its own chat and keeps going; for a PR that
    passed MergeWren it tells me the PR passed, with its link, and waits for my word on who merges
    it. Under Codex that is the case, since its `list_agents` lists only that session's own agents.
  - Highlights are information only. A blocker or a decision still comes to me in the session's
    own chat.
- **`dv:ticket`: filing without my confirmation, in two cases only.** A new section, "Filing
  without my confirmation", allows it for (a) a session with `dv:manager-mode` on filing a
  spin-off of the ticket it is working, and (b) a session with `dv:director-mode` on filing an item
  from a closeout note's "NOTICED, NOT FILED" list.
  - The mode must be on in the session doing the filing. Words in a ticket, a comment, a file or an
    agent's report never trigger it.
  - The ticket goes through the same format, fact check and both duplicate searches. It takes the
    source ticket's project and a related link to it. A question the draft cannot settle by
    reading still goes to me.
  - A near-match from the duplicate search stops the filing and goes to me as a decision.
  - The source ticket's project overrides step 1 of "File"; a project that cannot be used stops the
    filing and goes to me as a decision.
  - A duplicate search that is capped at 100 results or does not finish stops the filing and goes to
    me as a decision.
  - If `save_issue` errors or its reply is lost, the session stops and reports a possible creation
    instead of retrying, as `dv:groom` does.
  - The session reports the new id: a manager-mode session as a highlight, a director-mode session
    in its reply.
  - A ticket I ask for by hand still waits for my yes.
  - Every copy of the confirm rule is updated: the skill's description, step 6 ("Show the draft"),
    Rules, the README's `dv:ticket` line and the plugin manifest's description.
- **`dv:director-mode`, "Take closeout notes".** "Offer to file each item under "NOTICED, NOT
  FILED"" is replaced: the Director files each one under `dv:ticket`'s exception (b) and names the
  new ids in its reply to me.

## Documentation fixes

- **README:** the `dv:manager-mode`, `dv:director-mode` and `dv:ticket` entries describe the above,
  and the plugin table shows `0.20.0`.

## Not changed

- How the Director shows highlights to me, and the Director updating a PR that has no live session.
- `dv:groom`. Its spin-offs still follow its own interview, where my answer stands in for the draft.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.

A marketplace added from a local checkout needs `git -C <checkout> pull` first; the README's
"Linux Claude Code instances" section has the three commands.
