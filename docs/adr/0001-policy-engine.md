# ADR-0001 — Policy engine: deterministic Python evaluator as the source of truth

- **Status:** Accepted (2026-11-06, Wave 0 / task S-05)
- **Deciders:** BE + FE lanes (shared Wave 0 sign-off)
- **Related:** `contract/CONTRACT.md` §6, tasks.md §1.3, §2.3; BE-07 (evaluator), BE-14 (optional OPA/Rego parity mirror)

## Context

The demo's core claim is that a **deterministic policy gate outside the model** stops an unauthorized
tool chain. Authorization therefore cannot depend on any stochastic or hosted component: every policy
decision in a run must be reproducible byte-for-byte (`same input ⇒ byte-identical decision`, tasks.md §2.3).

## Decision

The **source of truth** for authorization is a deterministic, table-driven **Python evaluator** in
`backend/app/policy/`: a pure function

```
evaluate(call_ctx, policy, grants) -> PolicyDecision
```

with default-deny semantics, all matched denials returned ordered by precedence `R1 > R3 > R2` (first is the
primary reason), and **no I/O, no LLM, no randomness, no wall-clock reads** on the evaluation path.

An **optional OPA/Rego mirror** of the same rules may exist for parity checking (task BE-14), but it is
**parity-gated**: those tests are skipped automatically when the `opa` binary is absent, and the Rego
mirror can never be the source of truth for a decision.

## Alternatives considered

| Alternative | Why rejected for the MVP |
| --- | --- |
| **OPA/Rego only** (external binary as the engine) | Adds a binary dependency that breaks the fully-offline-after-bootstrap guarantee and complicates `make verify` in minimal sandboxes; parity tests would need the binary present. Kept only as an optional, parity-gated mirror (BE-14). |
| **Hosted LLM judge** ("ask a model whether this call is allowed") | Non-deterministic, not offline, and puts the model *on* the authorization path — exactly the failure mode the demo exists to demonstrate. Rejected absolutely: **no LLM ever appears on the authorization path**; an LLM may only be added later for prose, never for decisions. |
| **Hand-rolled ad-hoc checks scattered in tool code** | Not auditable, not testable as a unit, and impossible to diff (`policy_diff`) or retest deterministically. Rejected in favor of one table-driven evaluator. |

## Consequences

- Positive: decisions are deterministic, offline, unit-testable, and hashable into `input_digest`/evidence; the verifier role can wrap a pure function (see `docs/roles.md`).
- Positive: least-privilege recommendations and retests (RT-1..RT-3) are computed against the same evaluator, so "blocked stays blocked, legitimate stays allowed" is provable, not asserted.
- Negative: rule changes require code/data changes in the repo (mitigated: rules are data — `policies/*.yaml` — evaluated by the fixed engine).
- Negative: the optional Rego mirror can drift (mitigated: BE-14 parity tests compare every rule's decision tables, gated on the `opa` binary).
