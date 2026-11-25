# dv — v0.37.0

Minor release. A Director that turns on announces itself to the live worktree sessions, and each
session re-verifies the Director on that announcement; `dv:closeout` probes again after a failed
note send. `dv:director-mode`, `dv:manager-mode` and `dv:closeout` change. The other thirteen
skills have no behaviour changes; their version moves to `0.37.0` only because the suite is
released as one plugin.

Numbering: 0.37.0 follows 0.36.0, in which the Director decides routine calls for you, holds
yours for the end of the work, and every ask stands on its own. 0.37.0 keeps that change and
0.35.1's (the Director asks you to close a finished chat instead of sending a SIGTERM). This
release's cross-references use 0.36.0's section names: `dv:director-mode` "Answer a worktree
session's question" and `dv:manager-mode` "Questions go to the Director first".

Why: a restarted Director comes back under a new name and address, and a worktree session learned
of it only when its next send to the old address failed. On 2026-11-25 in review-stack, one
session's highlights went to a stale address, and another's PR hand-back waited about 5 minutes,
held, with David unaware (VIL-1141).

## Changed

- **`dv:director-mode`, new "Announce yourself to the worktree sessions".** When the mode turns
  on (not when it was already on), and only in the main checkout, the Director sends each live
  worktree session one line that starts `Director announcement,` and asks for no reply. A live
  worktree session is a ListAgents peer named after a linked worktree's folder, then `-`, then a
  suffix with no `-` in it (the same test "Merge and clean up" uses). The on reply gains an
  `Announced to:` line that names the sessions, any failed send, or why nothing was announced
  (ListAgents or `git worktree list` failed, or Codex).
- **`dv:director-mode`, "On, off, and standing" and "Answer a 'Director check' probe".** The on
  bullet points at the announcement. The probe section says a probe follows each announcement and
  that held highlights, questions and notes may follow the answer.
- **`dv:manager-mode`, "Highlights".** A new paragraph: on a `Director announcement,` message, the
  session probes its sender, even when a Director is already verified, an earlier result was
  ambiguous or found none, or that sender was probed before. Only a sender whose name fits the
  candidate name (the main checkout folder's basename, then `-`, then a suffix) is probed. When
  its answer passes, it becomes the Director even if the one verified before still answers: the
  latest announcer wins, and two passing answers are not ambiguous in that case. The held
  highlights, each message whose send failed, and each question held while the probe waited then go to it (not a
  question already asked of David, nor one the Director held for David). What the old Director still owes a reply to moves at the same time: a
  question waiting for its answer, unless it has gone to David (same Qk, a new `Sent:` time and a
  new 10-minute wait), and a PR handoff sent to it with no reply yet. From the switch on, the old
  Director's answers no longer count. An announcer that answers with another path or stays silent
  changes nothing and holds up no other check. The verification rules point at the announcement as
  their one exception. A message whose send failed is now held for the next Director verified; a
  failed question counts its 10 minutes from the failed send. Highlights are held, except under
  Codex, while no Director can be verified; questions are not, and go as "Questions go to the
  Director first" says with no Director that can be verified.
  Last reviewed 2026-11-25.
- **`dv:closeout`, "Deliver the note", step 5.** If the note's send fails (SendMessage returns an
  error), the session probes again from scratch, steps 1 to 4, and sends the note to the Director
  that passes. A second failed send stops: the note is reported not sent. After a send that
  succeeded, neither the probe nor the note is resent. The outcomes list after step 5, and its copy in
  "Step 5 — Reply", gain "send failed and probe sent again". The test notes record the two SendMessage
  errors seen on 2026-11-25.
- **A failed send is a failure, never silence** (all three skills). The rule is stated once, in
  `dv:closeout`'s "Deliver the note", step 2: a SendMessage that returns an error was not
  delivered, and a probe with no answer 10 minutes after it was sent has failed too. A candidate
  whose probe failed leaves the candidates for that round, as if ListAgents had not listed it: it
  doesn't count toward the three and isn't probed again in that round; with none left, nothing is
  sent, and an answer that comes after its probe failed changes nothing. A background timer (such as `sleep 600`) brings a turn back after the 10 minutes, and is
  stopped once every probe sent has an answer. Step 4's silence lasts at most 10 minutes. When
  every probe's send failed, the reply says the note is not sent, with each error; otherwise it
  names the probes sent and each failed send. A new round starts only after the note's send
  fails. `dv:manager-mode` points at that rule for its probes (a round there is one
  verification). A failed probe starts no new verification at once; when a verification ends
  with no Director and at least one probe failed, a question held while it ran goes then as "Questions go
  to the Director first" says with no Director that can be verified,
  and the next highlight or question starts a new verification, during which a question is held
  as it is while any probe waits. No
  candidate left counts as "no candidate", and an announcer whose probe fails changes nothing.
  `dv:director-mode` names a failed announcement send without resending it and lists only the
  sessions it reached on its `Announced to:` line. When a probe answer's send fails, it sends the
  answer once more to the address ListAgents lists now for that session, then tells you in one
  line if that fails too or the session isn't listed.
- **README.** The version, and the `dv:manager-mode` and `dv:closeout` entries, which described
  the old verification, waiting and outcome rules.

## Decisions

- No ListAgents check before every send to the Director: a send to a stale address already fails
  (David Villavicencio, 2026-11-25).
- After an announcement, the latest announcer whose probe answer passes is the Director, even if
  the one verified before still answers (David Villavicencio, 2026-11-25).
