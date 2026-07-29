# Runtime budget: reading status & pacing a running agent

Two enforcement layers cooperate. The **server** is authoritative and binds every call
(`402`/`403`, see `spend-policies.md`). The **agent** paces itself *before* that hard
floor by reading two signals and, optionally, running `floe-guard` locally. Never
hand-roll server enforcement on the client — use the client only to fail *gracefully*
earlier.

## Signal 1 — response headers (per call, zero extra requests)

Every metered response carries:

| Header | Value |
|---|---|
| `X-Floe-Cost-USDC` | atomic USDC charged for this call (vendor payment + Floe margin) |
| `X-Floe-Payment-Amount` | same amount, human-decimal |
| `X-Floe-Payment` | `paid` \| `passthrough` (passthrough = upstream error, not charged) |
| `X-Floe-Budget-Advisory` | JSON advisory (when enabled) — the taper signal |

Advisory JSON:

```jsonc
{
  "near_limit": true,                    // present when within the near-limit threshold
  "tightest": {                          // the cap closest to breaching
    "scope": "session",                  // credit_line | session | task | api | vendor | key
    "match": "invoice-8842",             // taskId / hostname / payee / null
    "used_bps": 8600,                    // 0..10000 (86%)
    "remaining_raw": "700000",           // atomic USDC left under that cap
    "window_kind": "rolling",
    "window_resets_at": "2026-01-01T00:00:00Z"  // rolling windows only
  }
}
```

React to `near_limit` / `used_bps`: **downgrade** the next call to a cheaper model,
**finish** the current task and stop taking new work, or stop. These are your choices;
the server won't do them for you.

## Signal 2 — status endpoints (poll before an expensive step)

```
GET /v1/agents/credit-remaining
  → { available, walletFundedRaw, fundingMode: "wallet"|"credit_line",
      creditLimit, headroomToAutoBorrow, utilizationBps,
      sessionSpendLimit, sessionSpent, sessionSpendRemaining, heldUnspent, asOf }

GET /v1/agents/balance          // fuller view incl. on-chain wallet read + facility/loan state
GET /v1/agents/spend-limit      // just the session cap

GET /v1/developer/agents/:id/limit-chain   // developer view: EVERY live cap + spent/remaining,
  → { chain: [ { scope, kind, label, limitRaw, spentRaw, remainingRaw, windowResetsAt }, ... ] }
    // last entry is always scope:"balance"
```

`credit-remaining` is the decision-grade read for an agent: `sessionSpendRemaining` and
`utilizationBps` tell it how much room is left under the tightest session cap;
`available` is spendable funds after holds.

Via the MCP server (Claude/Cursor) the same data is `get_credit_remaining`,
`get_spend_limit`, `get_balances`, `estimate_x402_cost`, `x402_forecast`.

## Client-side pacing with `floe-guard`

`floe-guard` (PyPI `floe-guard`, npm `floe-guard`) is a local ceiling: it stops paid
work *before* the server would 402, so the agent degrades cleanly instead of hitting a
hard error mid-loop. It does **not** replace the server cap — run both.

```python
from floe_guard import BudgetGuard

guard = BudgetGuard(limit_usd=5.00, token_limit=2_000_000)  # USD and/or token ceiling

# Before each call — raises BudgetExceeded / TokenBudgetExceeded if it would cross:
guard.check(estimated_next_cost=0.02, estimated_tokens=1500)
# ... make the call ...
guard.record("openai/gpt-4o-mini", prompt_tokens=812, completion_tokens=140)

# Per agent-step sub-ceiling (resets each step); block a step before it overspends:
with guard.step(max_usd=0.50, max_tokens=200_000):
    guard.check(estimated_tokens=...)     # may raise scope="step"
    ...

adv = guard.advisory()   # near_limit, used_bps, remaining_usd/tokens, per-step headroom
```

Concurrency-safe variant for parallel fan-out: `reserve()` before the call, `settle()`
after (`reserve()` holds the estimate so N parallel callers can't all clear the same
stale total). `reserve()` returns a plain number when no tokens/step are involved
(backward compatible). TypeScript API mirrors this (`tokenLimit`, `guard.step({...}, g => …)`,
camelCase advisory fields).

## The rule

- **Server caps** = the hard floor (money, kill switch). Always set at least one.
- **Advisory + status reads** = when to taper (downgrade / finish / stop).
- **`floe-guard`** = enforce the taper locally so you never *hit* the 402 in a hot loop.

Map every agent-side "should I keep spending?" decision onto a read of the advisory or
`credit-remaining` — do not reimplement the ceiling the server already owns.
