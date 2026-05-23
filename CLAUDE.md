# villavicencio/skills

Personal Agent Skills library, spec-conformant per `agentskills.io/specification`.
Implementing v0.1.0 per the plan at:

  /Users/dvillavicencio/Projects/openclaw/docs/plans/2026-05-22-001-feat-skills-library-foundation-plan.md

Source requirements doc (Proof):
  https://www.proofeditor.ai/d/7bcoylxb?token=60d0bd1b-17ba-42fb-abaa-78ac0603efca

## Workflow
- Branch-first for substantive work; small doc/typo updates may commit directly to main
- Each unit (U1-U7) from the plan ideally becomes one PR
- CI gate: `agentskills validate skills/*` + suite-version-parity check (added in U4)

## Conventions
- Push to main is NOT pre-authorized on this repo — confirm before `git push origin main`
- All file paths in docs are repo-relative
- Apache-2.0 root LICENSE; no per-skill LICENSE/CHANGELOG in v0.1.0

## Resolved pre-flight (2026-05-22)
- Hermes install identifier shape: `villavicencio/skills/<skill-name>` after
  `hermes skills tap add villavicencio/skills`. The tap mechanism implicitly
  looks at `Path: skills/` in the repo. Confirmed via spike against
  `anthropics/skills` — see openclaw conversation for details.
- Fallback (no tap): direct-GitHub shape is `villavicencio/skills/skills/<skill-name>`.
