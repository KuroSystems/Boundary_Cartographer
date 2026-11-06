# ADR-0002 — Tool boundary: in-process MCP-shaped typed boundary, every result simulated

- **Status:** Accepted (2026-11-06, Wave 0 / task S-05)
- **Deciders:** BE + FE lanes (shared Wave 0 sign-off)
- **Related:** tasks.md §1.3, §2.1; BE-04 (mock MCP tools); `contract/openapi.yaml` (`replay_events[].tool_result`)

## Context

The demo must replay a seeded prompt-injection scenario against tools like `finance.export` **without any
real side effect**: no sockets, no MCP SDK, no network, no real finance data (tasks.md §1.4). At the same
time, the design must leave room to swap in a real MCP client later "without touching policy code".

## Decision

All tools live **in-process** behind an **MCP-shaped typed boundary** with `tools/list` / `tools/call`
semantics:

```
{ name, arguments } -> { content: [{ type: "json", data }], is_error, simulated }
```

- Exactly four tools exist: `document.read`, `document.summarize`, `finance.lookup`, `finance.export`.
- **Every** tool result carries **`simulated: true`**; mock tools return canned JSON only.
- No sockets, no MCP SDK, no network on the tool path. The boundary is the only seam: a real MCP client can
  be swapped in later by re-implementing the same typed interface, and policy code never changes.
- The contract enforces the safety property: `replay_events[].executed == false` for every
  `decision != "allowed"`, and `finance.export` has **no** event with `executed == true` (CONTRACT.md §4).

## Alternatives considered

| Alternative | Why rejected for the MVP |
| --- | --- |
| **Real MCP server over stdio/socket** | Violates the offline guarantee and the no-side-effect rule; adds a process-management and sandboxing burden disproportionate to the demo. |
| **MCP SDK client against mock transports** | Pulls a dependency and a protocol layer the MVP does not need; the typed boundary already provides the swap seam. |
| **Tools as plain Python functions called directly** | Removes the boundary, so policy code would touch tool internals and a future MCP swap would ripple through the verifier. Rejected in favor of the typed `tools/call` shape. |
| **HTTP microservices per tool** | Network on the tool path; breaks offline demo and determinism guarantees. Rejected. |

## Consequences

- Positive: the replay engine is fully offline and deterministic; `finance.export` can be "called" in a
  replay yet provably never executed (`executed: false`, `tool_result: null` for blocked calls).
- Positive: swapping in real MCP later touches only `backend/app/tools/` — the policy engine and verifier
  are untouched.
- Negative: the boundary is a convention, not enforced by the type system across processes (mitigated:
  Pydantic models on both sides of the seam + contract tests in BE-12).
