# dv 0.40.1

`dv:closeout` no longer claims a note reached the clipboard merely because a clipboard command
exited successfully. It reports command acceptance with the copy unconfirmed, distinguishes a
failed command from no available helper, and always includes the full note in a fenced code
block. Only David verifying a paste in his UI confirms the copy; a same-shell readback does not.

The saved note, clipboard helper selection and arguments, worktree safety checks, build-output
fingerprints and supervised Director delivery stay as before. The README describes copying as
an attempt.

## Verification

- The exact Step 3 shell block passed 14 disposable mocked cases: exit 0 and exit 7 for each of
  five helpers, no helper, save failure, no git repository and helper precedence. Saved note
  bytes and helper arguments were checked without using the real clipboard.
- A headless Claude reporting fixture inside an Orca PTY saved the exact note through mock
  `pbcopy` and returned an unconfirmed status with the complete fenced note. It exercised
  reporting only, not an interactive full closeout, safety checks, archival, Director delivery
  or removal.

Refs VIL-891.
