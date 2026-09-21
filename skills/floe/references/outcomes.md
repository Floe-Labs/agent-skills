# Outcomes — what a task produced

Floe costs every task. An **outcome** is the other half of that sentence: what the task
actually *produced* — a booked meeting, a qualified lead, a resolved ticket. Report it
against the task id you already have and Floe binds it to the call, so cost and outcome
sit on one row. That is what turns cost-per-outcome into a number instead of an estimate.

## Two different things called "outcome"

They share a word and nothing else. Getting them mixed up is the most common mistake here.

| | `reportOutcome` / `report_outcome` | `emitOutcome` / `emit_outcome` |
|---|---|---|
| What it is | Your own eval signal for a tagged **action** | The **billable claim** for a **task** |
| Keyed on | `actionId` | `taskId` |
| Shape | `status` + `scoreBps` + `note` | `outcomeKind` + `quantity` + evidence |
| Reaches an invoice | Never | Yes — this is what gets rated |
| Re-reporting | Overwrites the previous signal | Appends a new event; nothing is updated |

If you are answering *"did this decision work?"* use `reportOutcome`. If you are answering
*"what did this task produce that we bill for?"* use `emitOutcome`.

## Emitting

**TypeScript** (`floe-agent`)

```ts
await agent.fetch({ url, taskId: "call-8821" });

await agent.emitOutcome({
  taskId: "call-8821",
  outcomeKind: "meeting_booked",
  idempotencyKey: "call-8821:meeting_booked",
});
```

**Python** (`floe-agentkit-actions`)

```python
agent.fetch(url, task_id="call-8821")

agent.emit_outcome(
    "call-8821", "meeting_booked",
    idempotency_key="call-8821:meeting_booked",
)
```

**MCP** — the `emit_outcome` tool, in the `outcomes` capability group. Same fields,
snake_case (`task_id`, `outcome_kind`, `idempotency_key`).

**HTTP** — `POST /v1/agents/outcomes` with an agent key (`floe_…`).

## The rules that will bite you

**A task id that names no call is refused (404), not stored.** An outcome nothing can
bill is worse than no outcome, because it looks like one. Tag the call first, emit after.

**`outcomeKind` is opaque to Floe.** Lowercased, ≤64 chars, never interpreted — the
vocabulary is the operator's. Pick stable names (`meeting_booked`, not `meeting booked
(sept)`) and keep them stable once you start emitting, because anything that later prices
an outcome will key on the kind.

**Pricing per outcome kind does not exist yet.** Rate cards today meter per request, per
audio minute, per task and per voice call — there is no outcome unit. Emitting a claim,
having it confirmed, and reading it back all work now; rating a kind against a price comes
with the rating work. Emit anyway — the claims are what that will rate.

**`idempotencyKey` is required.** Emitters retry; a replay of the same key returns the
stored claim instead of creating a second one. Use a key derived from the fact itself
(`<taskId>:<kind>`), not a random one, or a retry becomes a duplicate claim.

Reusing one key under a *different* task id is refused — the claim is already bound to
the first call, and quietly re-pointing it would answer a question you did not ask.

**Two meetings on one call is `quantity: 2` on one claim**, not two claims.

**An agent key may only report.** There is no `status` argument. Confirming a claim,
voiding one and resolving a collision are **operator** acts on the developer-scoped
surface (`floe_live_…`), because they move money and the evidence that justifies them —
a CRM webhook, a calendar invitation — reaches the operator's backend minutes to days
after the call, never your process.

So emitting never sets the billing anchor: `confirmedAt` comes back null, and the claim
becomes billable when an operator confirms it.

## Evidence is an allowlist, not a bag

Three fields, and nothing else is accepted:

- `externalSystem` — the namespace, e.g. `hubspot`. Lowercased.
- `externalRef` — its id, stored **verbatim** (CRM and calendar ids are case-sensitive).
  Requires `externalSystem`.
- `note` — free text, ≤500 chars.

```ts
await agent.emitOutcome({
  taskId: "call-8821",
  outcomeKind: "meeting_booked",
  idempotencyKey: "call-8821:meeting_booked",
  quantity: 2,
  externalSystem: "hubspot",
  externalRef: "DEAL-9",
});
```

Equality on `(externalSystem, externalRef)` is the only thing that **proves** two claims
are one fact, which is why the ref is never normalised. All three fields are erasable: a
subject erasure nulls them and stamps the claim. The claim itself survives — an invoice
line must outlive an erasure, a CRM id need not.

Do not put personal data in `note`. It is erasable, but it is still the wrong place for it.

## When two claims land on one call

A post-call webhook reporting against the orchestrator's call id and your agent reporting
against the task id can both resolve to the same call. That is **one meeting reported
twice**, or **two meetings booked once** — and Floe cannot tell which.

So it does not guess. Both claims are kept, each with its own chain, and an
`outcome_claim_collision` finding names the conflict for a person. The operator resolves
it by voiding one as a proven duplicate, or by confirming both as genuinely distinct.

Nothing your agent does will resolve a collision, and nothing it does should try to
pre-empt one. Emit the fact you observed; let the conflict be visible.

## Errors worth handling

| Status | Code | What it means |
|---|---|---|
| 404 | `task_not_found` | No call in the account carries that task id **yet**. Tag the call first. |
| 409 | `outcome_claim_exists` | A current claim of this kind already exists for the identifier. Correcting one is an operator action. |
| 409 | `outcome_claim_bound_elsewhere` | This idempotency key already names a claim bound to a different call. Use a new key. |
| 400 | — | Local shape problems: `outcomeKind` >64 chars, `quantity` <1, `externalRef` without `externalSystem`. Both SDKs catch these before the request. |
