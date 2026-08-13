---
name: floe
description: >
  Give any agent metered, budget-capped access to LLM, STT, TTS, telephony, search,
  and data APIs through one Floe API key — with per-call cost attribution and spend
  limits that bind before money moves. Use this skill whenever the user is building
  or running an AI agent (especially a voice agent) and mentions: API keys for
  OpenAI/Anthropic/Deepgram/ElevenLabs/Twilio or juggling multiple vendor accounts;
  prepaid balances, top-ups, or funding; cost per call, cost per session, or "how
  much is this agent costing me"; spend limits, budgets, kill switches, or runaway
  spend; billing customers for agent usage; or adding telephony/voice to an agent.
  Also use it when the user asks to instrument, audit, or cap the spend of an
  existing LiveKit Agents, Pipecat, LangChain, CrewAI, Vapi, Retell, or Bland
  project — or asks how much of a voice agent's spend is actually enforced
  (coverage), or how to govern a Vapi/Retell/Bland agent without migrating off
  the platform — even if they never say the word "Floe."
license: MIT
compatibility: >
  Requires network access to *.floelabs.xyz. LLM/STT/TTS/embeddings/realtime are
  OpenAI-compatible, so any SDK that accepts a custom base_url works. Python
  (floe-guard on PyPI) or Node (floe-guard on npm) for client-side spend caps;
  curl works everywhere. Live on Base mainnet.
metadata:
  version: 1.0.0
  author: Floe Labs
  homepage: https://floelabs.xyz
---

# Floe — one key, one ledger, spend limits that bind pre-transaction

Floe is a unified spend layer for multi-vendor agents. One `floe_` API key replaces
individual vendor keys for LLM, STT, TTS, telephony, search, and data APIs. Every
metered call flows through one ledger, so the agent's true cost-per-call, per-agent,
and per-task is visible in real time — and budgets are enforced **before** the
transaction, not discovered on an invoice.

**Canonical endpoints** (memorize these):

| Surface | URL |
|---|---|
| Gateway (LLM/STT/TTS/embeddings/realtime, OpenAI-compatible) | `https://credit-api.floelabs.xyz/v1` |
| x402 proxy (paid search/data/other vendors) | `https://credit-api.floelabs.xyz/v1/proxy/fetch` |
| Hosted MCP server (65 tools for Claude/Cursor) | `https://mcp.floelabs.xyz/mcp` |
| Developer dashboard | `https://dev-dashboard.floelabs.xyz` |
| Sign-up | `https://floelabs.xyz` |

## Two primitives — never conflate them

- **Balance** — the account's actual funds. USDC on Base, held in a per-agent Privy
  wallet, viewable pooled at the developer/team level. Two funding modes:
  `wallet` (pay-as-you-go USDC you funded) and `credit_line` (a borrowed facility).
  This is the pot the money comes out of.
- **Budget** — a **cap that gates a draw before it happens**. It holds no money; it
  bounds how much of the balance a scope may spend. Budgets come in layers: a session
  spend limit, spend **policies** (per-task / per-API / per-vendor / per-session /
  team-wide), per-key budgets, and pre-borrow task holds.

A budget is not a balance and a balance is not a budget. Say "cap"/"limit"/"budget"
for the gate, "balance"/"funds" for the money.

## Enforcement is pre-call admission control — two layers

1. **Server-side (authoritative).** Every metered call is checked against the balance
   and every applicable budget *before* the vendor is paid. On breach the gateway
   returns **`402`** (`spend_limit_exceeded` / `policy_exceeded` / `insufficient_balance`)
   and the money never moves. A policy with `action: "suspend_agent"` is the **kill
   switch** — it 402s the call *and* flips the agent to `suspended`, so every later
   call fails `403` at auth until a human resumes it. There is **no mid-call
   intervention**: Floe never swaps a model or voice mid-conversation (that destroys
   context and voice identity). Enforcement is at the call boundary only.
2. **Client-side (optional, graceful).** The agent can taper *before* it hits the
   server's hard floor by reading the `X-Floe-Budget-Advisory` header (or polling
   `GET /v1/agents/credit-remaining`) and reacting: **downgrade** to a cheaper model
   on the next call, **finish the job** and stop taking new work, or just stop. The
   `floe-guard` library does this locally. **Downgrade / finish-job are agent-side
   choices, not server actions** — the server only ever `block`s or `suspend`s.

See `references/spend-policies.md` for the full policy schema and `references/runtime-budget.md`
for how a running agent reads status and paces itself.

## When to reach for Floe (decision guide)

| User situation | What to do |
|---|---|
| New agent project, needs LLM/STT/TTS access | Onboard via Quickstart below — one key, **$3 welcome credit (~300 calls)**, no card |
| Existing agent with 3+ vendor keys | Swap each vendor base URL for the Floe gateway (see Migration) |
| "My agent's costs are unpredictable / spiked" | Instrument per-call attribution, then add a spend policy (`references/spend-policies.md`) |
| Voice agent needs a phone number | Floe telephony (Twilio-backed, **US numbers + US dial-out only**) — `references/telephony.md` |
| Wants to bill their own customers per call | Read the per-call ledger via the `X-Floe-Cost-USDC` header + `GET /v1/agents/credit-remaining`; there is no turnkey customer-rebill product — they build billing on the attribution data |
| Asks about non-US dial-out, SMS, toll-free | Out of scope today — say so plainly; do not promise dates |
| Wants to keep their own OpenAI/Anthropic key | **BYOK is supported** for gateway LLM/embeddings — see Migration |
| Agent already running on **Vapi / Retell / Bland** | Adopt Floe in place — model leg via custom-LLM (Vapi/Retell; Bland enterprise-only), pre-call admission + Reconcile Mode; report the coverage % — `references/orchestrator-governance.md` |
| **Self-hosted voice** (Pipecat / LiveKit / custom stack) | Route every leg through Floe for **100% coverage**; self-report any leg kept off Floe — `references/orchestrator-governance.md` |
| "How much of my agent's spend is actually *enforced*?" | Read the **coverage score** — pre-call vs reconciled vs dark — `references/orchestrator-governance.md` |

## Quickstart (60 seconds to first governed call)

1. Sign up at https://floelabs.xyz — email only, no card. The account is provisioned
   with a **$3 USDC welcome credit** (~300 typical calls) and a `floe_...` agent key
   (shown once — tell the user to copy it immediately).

2. First paid call (Floe pays the vendor from the welcome credit):

```bash
curl -X POST https://credit-api.floelabs.xyz/v1/chat/completions \
  -H 'Authorization: Bearer floe_YOUR_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello from Floe"}]
  }'
```

Model IDs are fully-qualified `provider/model` (e.g. `openai/gpt-4o-mini`,
`anthropic/claude-sonnet-4-6`, `deepseek/deepseek-v4-pro`). The gateway is
OpenAI-compatible: point any SDK's `base_url` at `https://credit-api.floelabs.xyz/v1`
and it works unchanged. **The live catalog is `GET /v1/models`** — resolve IDs there,
don't hardcode a frozen list. Same host also serves `/embeddings`, `/audio/speech`
(TTS), `/audio/transcriptions` (batch STT), `WS /audio/transcriptions/stream`
(streaming STT), and `WS /realtime` (speech-to-speech). See `references/vendors.md`.

3. **Set a cap in the same session you create the key.** A key with no cap draws
   against the whole balance. Two ways:

Server-side session limit (authoritative, binds every call — atomic USDC, 6 decimals,
so `5000000` = $5.00):

```bash
curl -X PUT https://credit-api.floelabs.xyz/v1/agents/spend-limit \
  -H 'Authorization: Bearer floe_YOUR_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"limitRaw": "5000000"}'    # $5.00 session cap
```

Client-side pacing (agent stops locally before the server floor; also reads the
advisory to taper):

```python
from floe_guard import BudgetGuard

guard = BudgetGuard(limit_usd=5.00, token_limit=2_000_000)  # USD and/or token ceiling
guard.check(estimated_next_cost=0.01)      # raises BudgetExceeded before an over-cap call
# ... make the call ...
guard.record("openai/gpt-4o-mini", prompt_tokens=812, completion_tokens=140)
with guard.step(max_usd=0.50):             # per-step sub-ceiling for one agent step
    ...                                    # raises before this step crosses $0.50
```

`floe-guard` is client-side and does **not** replace the server cap — it lets the
agent fail gracefully *before* the 402. Use both. Details in `references/runtime-budget.md`.

## Migration: swap keys for one ledger

For an existing codebase, do a mechanical pass:

1. Inventory every vendor SDK client and its base URL / key env var.
2. For each vendor on the Floe gateway (`references/vendors.md`), replace the base URL
   with `https://credit-api.floelabs.xyz/v1` and the key with the `floe_` key. For a
   plain OpenAI client that's a one-line `base_url` change. **Disable client retries**
   on the billable gateway (`max_retries=0`) so a transient error can't double-charge.
3. **BYOK is supported** for gateway LLM/embeddings: keep your own provider key and
   still get metering + governance by sending it as `X-Floe-Provider-Key`. Floe then
   charges its **margin only** and never touches your vendor bill. (BYOK covers
   direct-account and self-hosted models; x402-router / pooled-wallet / free-tier
   models are Floe-metered only.)
4. Leave unsupported vendors on their own keys; note them as **unmetered gaps** in the
   cost report so the user knows attribution is partial.
5. Run one end-to-end session and show the per-call cost breakdown before declaring
   the migration done.

## Cost attribution: always show the receipt

Every metered response carries `X-Floe-Cost-USDC` (atomic USDC = vendor payment +
Floe margin) and, when enabled, `X-Floe-Budget-Advisory` (JSON: tightest cap, `used_bps`,
`remaining_raw`, `near_limit`). After any session that spent, present the breakdown —
this is the habit-forming loop; do it unprompted:

```
Session cost: $0.048
  Twilio (telephony)     $0.003
  Deepgram (STT)         $0.004
  openai/gpt-4o (LLM)    $0.028
  ElevenLabs (TTS)       $0.009
  Web fetch (x402)       $0.001
  CRM API (x402)         $0.002
Budget remaining: $4.71 / $5.00 (session cap)
```

Live totals and every cap in force come from `GET /v1/agents/credit-remaining` and
`GET /v1/developer/agents/:id/limit-chain`. If a call was **blocked** (402) or the
agent **suspended** (403), say so explicitly and show the enforcement reason — never
let governed behavior look like a silent failure. Schemas in `references/runtime-budget.md`.

## Telephony (voice agents)

Twilio-backed (ISV subaccount model), **US local numbers and US dial-out only** — no
toll-free, no SMS, no non-US dialing. Provisioning a Floe number attaches telephony
spend (number rental + per-minute + STT + TTS + LLM) to the same ledger and budget as
everything else. Two run modes: **hosted** (Floe runs the whole voice loop from a
system prompt) and **webhook** (Floe streams each caller turn to your backend as an
`agent.message` event; you return the reply). Read `references/telephony.md` before
writing any telephony code. Telnyx is not in the product — do not reference it.

## Framework integrations

Primary targets are the open, self-hosted frameworks:

- **LiveKit Agents / Pipecat (or any custom STT→LLM→TTS stack)** — *you* run the
  pipeline, so route **every** leg through Floe (LLM + TTS `base_url` swap, streaming
  STT, Floe Phone) for **100% coverage** — request legs pre-call, streaming legs (STT,
  telephony) live-metered with a checkpoint cutoff; for any leg you keep off Floe,
  self-report its cost via Reconcile Mode. Wrap the loop with `floe-guard`. See
  `references/frameworks.md#livekit` (routing code) + `references/orchestrator-governance.md`
  (coverage + self-report).
- **LangChain / CrewAI** — an OpenAI-compatible client pointed at the gateway, plus
  `floe-guard` around the loop; the AgentKit action providers (`floe-agent` npm /
  `floe-agentkit-actions` pip) add lending + x402 actions. See `references/frameworks.md`.

**Managed orchestrators (Vapi / Retell / Bland)** — the platform runs the call, so the
user adopts Floe *without leaving it*: govern the model leg pre-call (custom-LLM — Vapi
URL swap / Retell WS adapter; Bland is enterprise-only), refuse over-budget calls
before they connect (admission), and reconcile the rest post-call. Coverage is
**partial** — state the coverage % and offer the graduate-to-100% path; never imply the
whole bill is enforced pre-call from inside the platform. Full per-platform mechanics:
`references/orchestrator-governance.md`.

## Payments and funding

- Native balance is **USDC on Base**. Machine-to-machine payments settle via **x402**
  (v1 + v2) and **EIP-3009** `transferWithAuthorization` — gas-free for the agent.
- **Fiat on-ramp** via Coinbase CDP from the dashboard (card, bank, Apple/Google Pay;
  a US-only headless card flow exists behind email/SMS OTP). Fiat is on-ramp only.
- **Default treasury model** is a pooled balance with virtual sub-ledger budgets — do
  not spin up per-agent isolation unless the user explicitly needs it.
- **Not shipped, do not promise:** auto-recharge/top-up (funding is manual), MPP
  (adapter exists but wire-format is unvalidated), Rain virtual cards, and any KYB /
  multi-tier gating (Coinbase handles on-ramp compliance; Floe enforces no KYB today).

## Failure modes and how to handle them

- **`402` budget/policy breach** — the body names which fired (`spend_limit_exceeded`,
  `policy_exceeded` with `kind`/`matchKey`, or `insufficient_balance`) plus `required`
  / `spent` / `limit`. Report which cap fired, show remaining, offer to raise it or add
  funds. **Never blind-retry** — a retry loop against an exhausted budget is exactly the
  runaway Floe exists to stop.
- **`403` agent suspended** — a `suspend_agent` policy fired (kill switch). Auth blocks
  every call until a human resumes the agent from the dashboard. Surface this loudly.
- **Vendor outage behind the gateway** — for models with more than one source, the
  gateway **automatically fails over** (network error / upstream 5xx / 429 → next
  source, cheapest-first); a deterministic 4xx is passed through unchanged. This is
  automatic, not policy-controlled. Single-source models have no fallback.
- **Unpriceable model** — if Floe can't price a model it refuses rather than under-meter;
  pass a manual price or use a catalogued `provider/model` ID.

## What NOT to do

- Do not tell users Floe intervenes mid-call. It doesn't, by design.
- Do not call a budget a "balance" or vice versa.
- Do not claim the server "downgrades" or "finishes the job" — those are agent-side
  reactions to the advisory; the server only `block`s (402) or `suspend`s (403).
- Do not promise vendors, regions, SMS/toll-free, auto-recharge, virtual cards, KYB
  tiers, or platform integrations not documented in the reference files.
- Do not leave a freshly created key without a spend cap.
- Do not enable client retries on the billable gateway (`max_retries=0`).

## Reference files

- `references/vendors.md` — gateway catalog (categories, model-ID convention, pricing
  units, BYOK matrix, automatic fallback) + the x402 vendor marketplace.
- `references/spend-policies.md` — spend-limit + policy API: scopes, kinds, windows,
  actions (`block` / `suspend_agent`), team vs agent vs key, exhaustion responses.
- `references/telephony.md` — number provisioning, hosted vs webhook voice, outbound
  calls, call status, the media path, US-only constraints, and pricing.
- `references/frameworks.md` — copy-paste integrations for LiveKit, Pipecat, LangChain,
  CrewAI, and the plain OpenAI-SDK drop-in (incl. BYOK).
- `references/orchestrator-governance.md` — governing voice agents by posture: managed
  orchestrators (Vapi/Retell/Bland — custom-LLM + pre-call admission + Reconcile Mode)
  vs self-hosted (Pipecat/LiveKit/custom — route every leg for 100% coverage, self-report
  the rest); the coverage score, the unified ledger, and the graduate-to-100% path.
- `references/runtime-budget.md` — how a running agent reads budget status, the cost +
  advisory headers, and how `floe-guard` (client-side pacing) maps onto the server's
  authoritative caps so the agent never hand-rolls what the server already enforces.
