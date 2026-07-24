# Stop rules, budget, and the standoff protocol

The loop is an **economy**: paid model rounds are the scarce resource, and this file is the
contract that keeps the loop from spending them forever. `approve` is not always reachable — and
when it is only reachable by widening scope, the correct outcome is a documented `standoff`, not
another round.

## What counts as a paid model-review round

`S1` (first FIND), `S5` (closure), `S6` (final), and each extension leg's `S5`/`S6`. Host-side
work — S2 REFUTE (Claude), S3 FIX, S4 GATES — does **not** count. The REFUTE, batch-fix, and
free-gate stages exist precisely so that the paid rounds stay few and each one is decisive.

- **Base pass: 3 paid rounds** — S1 + S5 + S6.
- **Default soft budget: 4.** The first four paid rounds run on their own; every round past the
  fourth must be earned by a fingerprint-new P0/P1 with concrete evidence (the novelty gate) — an
  extension leg adds its S5 + S6, pushing the counter to 5 and beyond, where the novelty gate
  always applies.
- **`rounds:<n>`** moves the soft budget — but **never** the hard ceiling.
- **Hard ceiling: 10.** Nothing overrides it. Reaching it is a terminal condition.

## The only thing that buys an extension

After S6, a finding may extend the loop (one more S3–S6 leg) **only if all** hold:

1. It **survives S2 REFUTE** (all three questions pass).
2. It is **fingerprint-new** — never seen in this run's ledger.
3. It is **P0 or P1** with concrete evidence (a verbatim quoted line, per the 75/100 gate).

A wording change, a re-phrasing of a known finding, a ≤P2 finding, or anything already ledgered is
**not** grounds for an extension. Severity inflation ("now I think this medium is really high")
without a new concrete failure path does not qualify.

## Terminal conditions (stop when ANY holds)

| Terminal | Trigger | Verdict |
|---|---|---|
| **Clean** | S6 approves / returns `NO_NEW_MATERIAL_FINDINGS`; no surviving finding | `ready` |
| **Budget hit** | soft budget (or `rounds:<n>`) reached with work still open | `not-ready` or `standoff` — stated honestly |
| **Ceiling hit** | 10 paid rounds reached | `not-ready` or `standoff` |
| **Re-raise** | a `refuted` / `deferred` / `out-of-scope` fingerprint comes back | `standoff` + routing |
| **Marginal tail** | the only remaining news is a same-theme ≤P2 tail | `ready-with-fixes` — fix trivially-correct ones, present |
| **Unfixable-in-scope** | a real P0/P1 survives that cannot be fixed without widening scope | `standoff` (routed) or `not-ready` |

**Never** silently continue past a budget or ceiling. If the loop stops because it ran out of
budget rather than because the change is clean, the report says so in plain words, and the ledger
records the budget stop.

## The three folklore stop rules, codified

These are the sharp, hard-won rules that a naive loop rediscovers the expensive way:

1. **Out-of-scope re-raise → stop and present.** Fix every in-scope finding; document the
   scoped-out ones against the ticket that owns them; let the operator decide ship-vs-expand.
   *"Drive to approve" yields to "verify, don't blind-accept" the moment `approve` is only
   reachable by scope-creep.* A finding re-raised after being deliberately scoped out does not get
   re-argued — it is a standoff signal.

2. **Same-theme marginal tail → stop.** When rounds have driven the real severity to zero and the
   only thing left is marginal-precision nitpicking on the same theme, stop at that line: fix the
   trivially-correct remainder, document the inherent limits, and present. Do not let a P1→0
   convergence turn into an infinite P3 tail.

3. **Theme audit beats rediscovery.** When a round surfaces a *class* of defect, sweep every
   sibling surface for it **once**, in the same S3 fix pass — grep every failure/return/error path,
   not just the one the reviewer happened to cite. One sweep is far cheaper than letting rounds
   3, 4, 5 each rediscover one more instance of the same class.

Rounds are still valuable — long loops have caught real defects that inline verification missed.
The discipline is to **budget** them, not to skip them.

## The standoff protocol

`standoff` is a **first-class terminal**, not a failure. It means: every in-scope finding is fixed,
and what remains is documented for a human decision. A standoff report carries:

- **Verdict `standoff`** and the one-line reason `approve` was not reached.
- **The routed findings** — each unfixed/deferred/out-of-scope finding with its owning ticket or
  the explicit ship-vs-expand decision it needs.
- **The ledger** — so a future run seeded with these fingerprints does not re-litigate them.

The operator decides: ship as-is, expand scope to address the standoffs, or route them onward.
The skill presents; it never merges, never pushes, and never widens scope on its own to force an
approval.
