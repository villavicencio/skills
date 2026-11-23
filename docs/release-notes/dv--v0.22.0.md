# dv — v0.22.0

Minor release. `dv:closeout` can deliver its note to a Director that runs as an Orca chat, and
`dv:manager-mode` finds the Director for its highlights the same way. Closeout's chat path and
manager-mode's highlights both send only to a session that has answered a probe with the main
checkout's path; closeout's agent-terminal path is unchanged. The other fourteen skills have no
behaviour changes; their version moves to `0.22.0` only because the suite is released as one
plugin.

Numbering: 0.22.0 follows 0.21.0, which gave `dv:groom` a forks-only mode (VIL-915).

Why: the home session now runs as an Orca chat. `dv:closeout` sent its note only to an agent
terminal in the main checkout, so it never reached the Director and the note was carried over by
hand (VIL-918).

## Changed

- **`dv:closeout`, "Deliver the note".** The terminal path is unchanged and still comes first.
  When no agent terminal qualifies, closeout looks for the Director with ListAgents and sends the
  note only after the Director has answered a probe:
  - **Candidates:** peer sessions in ListAgents (not this one) whose name is the main checkout
    folder's basename, then `-`, then a suffix, for example `skills-03`. A name proves nothing,
    since ListAgents shows no working directory. With none, or more than three, nothing is sent.
  - **The probe:** each candidate gets one message with no note content:
    `Director check, <ticket id, or the branch>: which directory are you running in? Reply with one line, its absolute path.`
  - **The answer:** it counts only when it comes from a probed candidate's name and gives, as
    text, the main checkout's path as `git worktree list` prints it or its real path. It is
    compared as text and never run in a shell. A passing answer shows where that session says it
    runs, not that it runs `dv:director-mode`.
  - **One Director, or none:** with one candidate, its passing answer is enough. With two or
    three, exactly one answer must pass and every other probed candidate must have answered with
    a different path; a silent candidate is waited for, never counted as a "no". Two or more
    passing answers are ambiguous, and nothing is sent. Who answered what is reported whenever
    no Director is found.
  - **The note:** sent once, with SendMessage, to the `from` address of the Director's answer.
    Its first line reads `Closeout note, <ticket id, or the branch>: <verdict line>`, so the
    receiver can tell what it is before expanding it. The message then gives the note's saved path and the
    note's text, and asks for a one-line reply. Neither the probe nor the note is resent.
  - **Timing:** answers come in a later turn, so closeout's reply first says the probe was sent
    and the note waits for the answers. Before sending the note, closeout runs its checks again
    and writes the note again from the current facts, saved and copied to the clipboard. Until it
    is sent, the note stays on the clipboard and at its saved path. A removal while the note
    waits ends the session, so the removal question says so.
  - **Outcomes reported:** not sent (naming what failed or could not run); probe sent, the note
    waiting for the answers; answered but not verified (a wrong path, or ambiguous; who answered
    what); note sent with no reply yet; note sent and replied. "Delivered" is not claimed without a reply.
  - **Codex:** there is no ListAgents view of other sessions, so this path cannot run and the
    note stays on the clipboard and at its saved path. The sentence saying a chat parent cannot
    be reached is gone.
  - The block that resolves the Orca CLI now also prints the main checkout's path.
- **`dv:closeout` reply format** names the Director outcome from the list above, and the removal
  offer says when the note is still waiting. The "What a test showed" paragraph matches.
- **`dv:manager-mode` "Highlights".** The Director is verified once per session with the same
  candidates, probe and one-Director rule, pointing at closeout's section by name. It needs
  ListAgents, not Orca, so a Director in an agent terminal or on a machine without Orca gets
  highlights too. The rule covers the candidates probed until a Director is verified (at most
  three), including ones ListAgents lists later; once a Director is verified, that result holds for the session and
  a candidate that appears later is not probed. The verified name and its answer's `from` address
  go in the written state; verification runs again from scratch if a send fails or ListAgents no
  longer lists that name. Highlights that come up while the probe waits
  go in one message once the Director is verified; until then none is sent. Nothing else in
  manager-mode changed.
- **README**, the `dv:closeout` and `dv:manager-mode` entries describe the probe.

## Known limit

The answer is the session's own claim. A session that misstates its directory, or a
non-Director session in the main checkout that is the only one to answer with its path, is taken
for the Director. David accepted this on 2026-11-23: every session is one of his own agents on
one machine, and the note holds nothing secret. There is no independent session lookup:
ListAgents shows no working directory, and Orca's ids do not match ListAgents names.

## Not tested

Tested on 2026-11-23, on hal: the chat path with the probe, run by hand from a worktree. The one
candidate, `skills-03`, answered the probe with one line, the main checkout's absolute path; the
answer's `from-name` matched the ListAgents name; SendMessage accepted the answer's `from`
address for the note, and the Director replied.

Not tested: a Director that is mid-turn when a message arrives (this one was idle), a wrong or
ambiguous answer, several candidates, a full `dv:closeout` run end to end, and manager-mode's
once-per-session verification.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
