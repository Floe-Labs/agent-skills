# Voice orchestrators & self-hosted pipelines — govern every leg

A voice call has four legs — **LLM, STT, TTS, telephony**. Where Floe can gate each
*before* the money moves depends on **who runs the call**:

- **You run the pipeline** (self-hosted: Pipecat, LiveKit, or any custom STT→LLM→TTS
  agent) → route **every** leg through Floe = **100% pre-call coverage**.
- **The platform runs the call** (managed: Vapi, Retell, Bland) → govern only what the
  platform lets you inject; the rest is **reconciled** after the call.

Never tell the user a leg is enforced pre-call when it's actually reconciled — that's
exactly what the coverage score exists to keep honest.

## Coverage score — the honest taxonomy

`GET /v1/developer/agents/:agentId/coverage` returns, per agent, the share of known
spend that was **pre-call enforceable** (Floe gated it before the spend) vs
**reconciled** (counted after the call, enforced *next* session) vs **dark** (on a
platform never connected to Floe — invisible). Use it to state what's governed and to
show the upgrade path. Every **Floe-metered or reconciled** leg lands on one ledger
(`GET /v1/developer/ledger?groupBy=source|customer|campaign|agent`); **dark** spend —
legs on platforms never connected to Floe — stays off the ledger by definition (you
can't ledger what you never see).

## Self-hosted / custom (Pipecat, LiveKit, any BYO stack) — the 100% path

You control the pipeline, so route each leg through Floe and it's gated pre-call:

| Leg | Floe rail |
|---|---|
| LLM | gateway `base_url = https://credit-api.floelabs.xyz/v1` (code in `frameworks.md#livekit`) |
| STT | streaming WS `wss://credit-api.floelabs.xyz/v1/audio/transcriptions/stream?model=deepgram/nova-3&encoding=linear16&sample_rate=16000` |
| TTS | `POST /v1/audio/speech` (OpenAI-compatible, e.g. `openai/tts-1`) |
| Telephony | Floe Phone — `POST /v1/developer/agents/{id}/numbers` + `POST /v1/calls` (`telephony.md`) |

Every leg on Floe = 100% coverage and no platform fee. (Request legs — LLM, TTS — gate
**pre-call**; streaming legs — STT, telephony — are **live-metered** and cut at ~60s
checkpoints, so a small bounded partial can land after admission.) **For any leg you
keep off Floe**, close the gap with **Reconcile Mode self-report** (recipe:
`pipecat-livekit-reconcile/`): connect the agent (`POST /v1/developer/orchestrators`,
provider `pipecat` or `livekit`) and have your code

- POST each call's cost to the returned **call-end URL** at session end, signed
  `X-Floe-Signature = hex HMAC-SHA256(secret, rawBody)` → Floe enforces the budget on
  the next session; a tripped `suspend_agent` policy blocks it, and
- (optional) call the **pre-call URL** before dialing and honor `{ allowed, reason }` —
  a cooperative check your agent must respect (skip / don't dial when `allowed` is false).

Self-report **only** the legs you keep off Floe — a leg routed through Floe is already
metered pre-call; reporting it too would double-count.

## Managed orchestrators (Vapi / Retell / Bland) — adopt Floe without leaving the platform

You don't run the pipeline, so you can't put Floe in every leg. Govern what the platform
exposes — three mechanisms, layered from strongest to catch-all:

1. **Model leg, pre-call — custom-LLM.** Point the platform's custom-LLM slot at Floe so
   the biggest, most variable leg is gated per turn.
   - **Vapi** — a real URL swap: `model.provider="custom-llm"`,
     `model.url="https://credit-api.floelabs.xyz/v1"`, `model.model="openai/gpt-4o-mini"`.
   - **Retell** — NOT a URL swap; a hosted WebSocket adapter (recipe: `retell-custom-llm/`).
   - **Bland** — **no self-serve custom-LLM** (enterprise-only). Skip this step; govern
     via Reconcile + admission below.
2. **Admission, pre-call — refuse an over-budget call before it connects.** Connect the
   agent (`POST /v1/developer/orchestrators`) and point the returned **pre-call URL** at
   the platform's hook:
   - **Vapi** — the phone number's Server URL (assistant-request); Floe denies with an
     error the caller hears.
   - **Retell** — the number's inbound webhook (`call_inbound`); Floe returns
     `{"call_inbound":{"reject":true}}`.
   - **Bland** — no native pre-call hook, but its **Pathway Webhook node** works: make
     the first node POST the pre-call URL and branch to an **End Call** node on a
     non-`200` (Floe returns `200 {allowed:true}` / `402 {allowed:false}`). That URL
     authenticates on its capability token alone — no signature, since a static node
     can't HMAC. Treat that URL as a secret (rotate to revoke); the token performs
     **admission checks only** — it can't read balances or write spend.
3. **Everything else, post-call — Reconcile Mode.** Point the platform's end-of-call
   webhook at the returned **call-end URL**; the whole call's cost lands on the ledger,
   counts against policies, and a `suspend_agent` breach blocks the next call.

### Recipe — local admission with `floe-guard` (no account, same contract)

The admission shapes above aren't hosted-only. `floe-guard`'s `gates` module emits
the **identical** reject/admit JSON from a local budget, so a free user rejects an
over-budget call today, and the paid upgrade is a URL swap — point the webhook at the
hosted pre-call URL instead of your own handler. Same contract, local vs hosted.

```python
from floe_guard import BudgetGuard, gates

guard = BudgetGuard(limit_usd=5.00)         # local; or BudgetGuard.from_floe(api_key="floe_…")

# Retell inbound webhook handler:
def on_call_inbound(payload):
    return gates.retell(guard)              # exhausted → {"call_inbound": {"reject": True}}
                                            # else       → {"call_inbound": {}}
# Vapi assistant-request handler (respond within ~7.5s):
def on_assistant_request(payload):
    return gates.vapi(guard, assistant_id="asst_…")
                                            # exhausted → {"error": "…"}  (spoken, then ends)
                                            # else       → {"assistantId": "asst_…"}
# Pipecat / Bland / custom — the provider-agnostic decision:
#   if not gates.pre_call(guard): reject at your call boundary
```

Honest scope: these gates are a **non-binding preflight** — they read the local budget
but don't reserve it, so under concurrency they can over-admit; the binding money-gate
is still the in-call guard (`check`/`reserve`) or the hosted server cap. **Pre-call
admission only — no mid-call cutoff.** `gates.retell` fires for inbound phone/SMS.
Bland's *Send Call* metadata field name is unconfirmed, so there's no `gates.bland()` —
use `gates.pre_call`. Requires `floe-guard >= 0.16.0`.

| | Model leg (pre-call) | Admission (pre-call) | Reconcile (post-call) |
|---|---|---|---|
| **Vapi** | custom-llm URL swap | assistant-request | ✓ |
| **Retell** | WS adapter | `call_inbound` reject | ✓ |
| **Bland** | ✗ (enterprise-only) | Pathway Webhook node | ✓ |

Coverage on a managed orchestrator is **partial**. The coverage % is the share of
*spend* that's pre-call enforceable — on Vapi/Retell that's the model leg (STT/TTS/
telephony reconcile); on Bland it's ~0 (every leg reconciles). Report the number from
the coverage endpoint. **Admission is a separate call-level gate, not a metered leg** —
it refuses over-budget calls but does not add to the coverage %. Never imply the whole
bill is enforced pre-call from inside the platform; it isn't.

## Graduate to 100% coverage

When the user wants every leg pre-call, move off the orchestrator onto a self-hosted
stack (Pipecat/LiveKit) with every leg on Floe rails (the table above). Docs:
`https://floe-labs.gitbook.io/docs/build/migrate-to-full-coverage`. Runnable references
where every leg is already on Floe: `livekit-voice-agent/`, `floe-phone-sales-agent/`.

## Experimental — Floe as Vapi's STT/TTS provider

Vapi (only) exposes custom-transcriber / custom-voice server hooks, so Floe *can* sit in
Vapi's STT/TTS media path (`wss://…/v1/orchestrator/transcriber`,
`https://…/v1/orchestrator/voice`). This is **flag-gated (`ORCHESTRATOR_VOICE_ENABLED`)
and off by default**, pending a published media-path latency benchmark — do **not** wire
it unless it's enabled for the account. Retell and Bland don't expose these hooks.

## Setup path & the credential note

Fastest: the dashboard **Orchestrators** card on the agent page — connect, copy the
call-end + pre-call URLs, rotate. For automation, the same via
`POST /v1/developer/orchestrators` (developer-scoped). A key pasted into a platform's
config (custom-LLM / custom-voice) must be **`read_write`** (those calls are POSTs); a
leaked key is bounded by the agent's **wallet balance + spend policies + rotation** —
note that a per-key budget does not yet gate the voice media legs.
