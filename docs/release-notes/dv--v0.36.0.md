# dv — v0.36.0

Minor release. A Director that turns on announces itself to the live worktree sessions, and each
session re-verifies the Director on that announcement; `dv:closeout` probes again after a failed
note send. `dv:director-mode`, `dv:manager-mode` and `dv:closeout` change. The other thirteen
skills have no behaviour changes; their version moves to `0.36.0` only because the suite is
released as one plugin.

Numbering: 0.36.0 follows 0.35.0, which let the Director sweep stale In Progress and In Review
tickets at session start.

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
- **`dv:manager-mode`, "Highlights".** A new paragraph: on a `Director announcement,` message,
  the session probes its sender, even when a Director is already verified, an earlier result was
  ambiguous or found none, or that sender was probed before. Only a sender whose name fits the
  candidate name (the main checkout folder's basename, then `-`, then a suffix) is probed. When
  its answer passes, it becomes the Director even if the one verified before still answers: the
  latest announcer wins, and two passing answers are not ambiguous in that case. The held
  highlights, each message whose send failed, and each held question then go to it (not a
  question already asked of David), and so does each message the old Director still owes a reply
  to: a question waiting for its answer (same Qk and `Sent:` time, so its 10-minute wait is
  unchanged) and a PR handoff with no reply yet. An announcer
  that answers with another path or stays silent changes nothing and holds up no other check.
  The verification rules point at the announcement as their one exception. A message whose send
  failed is now held for the next Director verified; a failed question counts its 10 minutes from
  the failed send. Highlights are held, except under Codex, while no Director can be verified; questions are not.
  Last reviewed 2026-11-25.
- **`dv:closeout`, "Deliver the note", step 5.** If the note's send fails (SendMessage returns an
  error), the session probes again from scratch, steps 1 to 4, and sends the note to the Director
  that passes. A second failed send stops: the note is reported not sent. After a send that
  succeeded, neither the probe nor the note is resent. The outcomes list after step 5, and its copy in
  "Step 5 — Reply", gain "send failed and probe sent again". The test notes record the two SendMessage
  errors seen on 2026-11-25.
- **README.** The version, and the `dv:manager-mode` and `dv:closeout` entries, which described
  the old verification and outcome rules.

## Decisions

- No ListAgents check before every send to the Director: a send to a stale address already fails
  (David Villavicencio, 2026-11-25).
- After an announcement, the latest announcer whose probe answer passes is the Director, even if
  the one verified before still answers (David Villavicencio, 2026-11-25).
