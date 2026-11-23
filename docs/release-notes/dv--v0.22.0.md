# dv — v0.22.0

Minor release. `dv:closeout` can deliver its note to a Director that runs as an Orca chat, and
`dv:manager-mode` finds the Director for its highlights the same way. The other fourteen skills
have no behaviour changes; their version moves to `0.22.0` only because the suite is released as
one plugin.

Numbering: 0.22.0 follows 0.20.1. Version 0.21.0 is taken by another open PR.

Why: the home session now runs as an Orca chat. `dv:closeout` sent its note only to an agent
terminal in the main checkout, so it never reached the Director and the note was carried over by
hand (VIL-918).

## Changed

- **`dv:closeout`, "Deliver the note".** The terminal path is unchanged and still comes first.
  When no agent terminal qualifies, closeout looks for a chat Director with two checks that must
  each find exactly one candidate:
  - `orca agent list --worktree "path:<main checkout>" --json` lists exactly one entry whose
    `kind` is `chat`. The `state` is not used: a live, idle chat can show `done`.
  - ListAgents lists exactly one peer session (not this one) whose name is the main checkout
    folder's basename, then `-`, then a suffix, for example `skills-03`. This is matched by name
    only, because ListAgents shows no working directory.
  The checks share no identifier, so they do not prove the two are the same session; the reply is
  asked to name its working directory, and a reply from elsewhere is reported as a wrong delivery.
  When both find one candidate, closeout sends the note to it once with SendMessage. The first
  line reads `Closeout note, <ticket id>: <verdict line>`, so the receiver can tell what it is
  before expanding it. The message then gives the note's saved path and the note's text, and
  asks for a one-line reply. It is not resent.
  - **Three outcomes are reported:** sent and replied; sent with no reply yet; not sent, naming
    the check that failed or could not run. "Delivered" is not claimed without a reply.
  - **Fallback:** if either check finds none or more than one, or cannot run (always the case for
    the second check under Codex), nothing is sent. The note stays on the clipboard and at its
    saved path, and the reply names the check. The sentence saying a chat parent cannot be reached
    is gone.
  - The block that resolves the Orca CLI now also prints the main checkout's path.
- **`dv:closeout` reply format** says whether the note was sent to the Director and whether the
  Director replied. The `description` and the "What a test showed" paragraph match.
- **`dv:manager-mode` "Highlights".** The Director is found with the same two checks, pointing at
  closeout's section by name. A highlight is not sent when the two checks do not each find exactly
  one session, or cannot run. Nothing else in manager-mode changed.
- **README, `dv:closeout` entry** describes the chat delivery.

## Not tested

Tested on 2026-11-23, on hal: the chat path's delivery step, run by hand from a worktree. Both
checks found one candidate (one `kind: chat` entry in Orca's agent list, one `skills-*` peer in
ListAgents), the note was sent once with SendMessage, and the Director replied.

Not tested: a Director that is mid-turn when the note arrives (this one was idle), and a full
`dv:closeout` run end to end.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
