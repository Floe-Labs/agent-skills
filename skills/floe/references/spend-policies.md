# Spend policies & limits

Floe enforces spend **before** each call (admission control). All amounts are atomic
USDC (6 decimals): `1000000` = $1.00. All endpoints are under
`https://credit-api.floelabs.xyz`.

Two auth surfaces:
- **Agent key** (`floe_…`, `Authorization: Bearer`) — the agent governs itself.
- **Developer** (dashboard session or `floe_live_…` key) — governs any agent in the team.

## Layers of cap (tightest wins)

Every call is checked against **all** applicable caps + the balance; a breach of any
one returns `402`. From narrowest to broadest:

1. **Per-key budget** — a spend budget on one API key.
2. **Spend policy** — `task` / `api` / `vendor` scoped caps, `once` or `rolling` window.
3. **Session spend limit** — one cap for the agent's current session.
4. **Team (developer) policy** — a `session` / `task` / `api` / `vendor` cap across
   *all* the developer's agents.
5. **Balance** — funds actually available (`wallet` funded USDC and/or `credit_line`).

## Session spend limit

The simplest cap — one number for the whole session.

```
GET    /v1/agents/spend-limit      → { active, limitRaw, sessionSpentRaw?, sessionRemainingRaw? }
PUT    /v1/agents/spend-limit      body { limitRaw: "5000000" }  → { active:true, limitRaw, sessionStartedAt }
DELETE /v1/agents/spend-limit      → { active:false }
```

Developer mirror (governs a named agent): `…/v1/developer/agents/:agentId/spend-limit`
(GET/PUT/DELETE). Note: if an agent is `selfServiceLocked`, an agent-key PUT may only
*lower* the cap, not raise or restart it; the developer endpoint bypasses that.

## Spend policies (scoped caps)

Agent-key CRUD:

```
GET    /v1/agents/policies[?includeRevoked=true]   → { policies: [...] }
POST   /v1/agents/policies                          → { policy }, 201
PATCH  /v1/agents/policies/:policyId                → { policy }
DELETE /v1/agents/policies/:policyId                → revoke
```

Create body:

```jsonc
{
  "kind": "task" | "api" | "vendor",   // what the matchKey means
  "matchKey": "invoice-8842",          // task: X-Floe-Task-Id · api: hostname · vendor: payee wallet
  "limitRaw": "2000000",               // $2.00 cap for this scope
  "windowKind": "rolling",             // "once" (default is rolling) — rolling needs windowSeconds
  "windowSeconds": 3600,               // ≥60, for rolling windows
  "action": "block",                   // "block" (default) | "suspend_agent"
  "label": "per-invoice cap",          // optional, shows in reports
  "expiresAt": 1735689600              // optional unix seconds
}
```

Match semantics:
- `task` — matched by the `X-Floe-Task-Id` header the agent sends on each call.
- `api` — matched by the destination **hostname** (x402 vendor host).
- `vendor` — matched by the **payee wallet** address.

## Team (developer-wide) policies

Apply across every agent in the developer account. Only here can `kind` be `session`.

```
GET    /v1/developer/policies
POST   /v1/developer/policies         // kind: session | task | api | vendor
PATCH  /v1/developer/policies/:policyId
DELETE /v1/developer/policies/:policyId
```

## Per-key budget

```
PUT    /v1/developer/agents/:agentId/keys/:keyId/budget   body { budgetRaw, windowSeconds? }
DELETE /v1/developer/agents/:agentId/keys/:keyId/budget
```

## Pre-borrow (reserve a task envelope)

Fence money for a task *before* it runs — creates a `once` task policy that expires:

```
POST /v1/agents/pre-borrow
  body { taskId, amountRaw, ttlSeconds?: 3600–86400, label? }
  → { policyId, taskId, limitRaw, expiresAt, expiresAtIso }
```

The reserved amount shows as `heldUnspent` in balance reads until settled or expired.

## Actions (what a breach does)

Only two server actions exist — do **not** describe others:

- **`block`** (default) — the call returns `402` and the spend never happens. The agent
  can retry a *different* (cheaper/smaller) call, add funds, or raise the cap.
- **`suspend_agent`** (kill switch) — the call `402`s **and** the agent is flipped to
  `status: "suspended"`. Every subsequent call fails `403` at auth until a human
  resumes the agent from the dashboard. Use for hard runaway containment.

"Downgrade to a cheaper model" and "finish the current job then stop" are **agent-side**
reactions to the advisory signal (see `runtime-budget.md`), not server behaviors.

## Exhaustion responses

**`402`** with a body naming the cause:

```jsonc
// session limit
{ "error": "spend_limit_exceeded", "required": "...", "spent": "...", "limit": "..." }
// scoped policy
{ "error": "policy_exceeded", "kind": "task", "matchKey": "...", "policyId": 123,
  "label": "...", "required": "...", "spent": "...", "limit": "...",
  "auto_suspended": false }              // true when action was suspend_agent
// no funds / no credit
{ "error": "insufficient_balance", "required": "...", ... }
```

**`403`** — agent suspended (a `suspend_agent` policy fired earlier). Blocked at auth.

A `spend_declined` event is emitted on policy breach. Never blind-retry a 402 against
the same cap — that is the runaway pattern Floe exists to stop.
