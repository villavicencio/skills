# dv — v0.39.1

Patch release. `dv:groom` keeps a wanted related link when it clears a stale Linear blocker.
Linear can leave the pair with no relation after the removal, even when the ticket still names
the former blocker. Grooming reads the pair back and adds a wanted `relatedTo` link only if absent.

An unclear prerequisite, such as a Canceled or Duplicate ticket or a PR closed without merging,
stays a question in both grooming modes. The existing blocker stays until the answer drops or
moves the wait. When the wait moves, grooming confirms the replacement blocker before removing
the old one.
