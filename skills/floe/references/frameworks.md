# Framework integrations

The gateway is OpenAI-compatible, so most integrations are a **`base_url` swap**:
point the framework's OpenAI client at `https://credit-api.floelabs.xyz/v1` with a
`floe_` key, keep `provider/model` IDs, disable client retries, and wrap the loop with
`floe-guard`. Runnable recipes live in the `floe-cookbook` repo.

## Plain OpenAI SDK — the drop-in (recipe: `drop-in-existing-agent/`)

**Python**

```python
from openai import OpenAI
client = OpenAI(
    base_url="https://credit-api.floelabs.xyz/v1",
    api_key=require_env("FLOE_API_KEY"),   # floe_…
    max_retries=0,                         # billable gateway: don't double-charge on transient errors
)
resp = client.chat.completions.create(model="openai/gpt-4o", messages=[...])
```

**TypeScript**

```ts
const client = new OpenAI({
  baseURL: "https://credit-api.floelabs.xyz/v1",  // client appends /chat/completions
  apiKey: requireEnv("FLOE_API_KEY"),
  maxRetries: 0,
});
const model = "openai/gpt-4o";
```

## BYOK — keep your own vendor key (recipe: `metered-llm/`)

Send your provider key as `X-Floe-Provider-Key`. Floe meters + governs the call but
charges its **margin only** and never touches your vendor bill. Works for gateway
LLM/embeddings on direct-account and self-hosted models (not for x402-router,
pooled-wallet, or free-tier models).

```ts
const client = new OpenAI({
  baseURL: "https://credit-api.floelabs.xyz/v1",
  apiKey: requireEnv("FLOE_API_KEY"),                 // still a floe_ key (for governance)
  defaultHeaders: { "X-Floe-Provider-Key": requireEnv("PROVIDER_API_KEY") },  // your OpenAI/etc. key
});
```

## LiveKit Agents / Pipecat (base_url swap on the OpenAI plugins)

Point the OpenAI LLM + TTS plugins at Floe; for STT use Floe's streaming endpoint or a
BYO Deepgram key. Same one-key pattern; cap the run with a session spend limit + `floe-guard`.

```python
from livekit.plugins import openai, deepgram, silero
session = AgentSession(
    # STT — Floe streaming STT, or BYO Deepgram (both meter/are-metered):
    stt=deepgram.STT(model="nova-3"),
    llm=openai.LLM(model="openai/gpt-4o-mini",
                   base_url="https://credit-api.floelabs.xyz/v1", api_key=FLOE_API_KEY),
    tts=openai.TTS(model="openai/tts-1", voice="alloy",
                   base_url="https://credit-api.floelabs.xyz/v1", api_key=FLOE_API_KEY),
    vad=silero.VAD.load(),
)
```

Floe streaming STT (feeds a LiveKit/Pipecat STT plugin's interim/final events):

```
wss://credit-api.floelabs.xyz/v1/audio/transcriptions/stream?model=deepgram/nova-3&encoding=linear16&sample_rate=16000&language=en
```

PCM frames up; `{ "type":"transcript", "text", "is_final", "speech_final" }` down
(`is_final:false` = interim, `true` = final). Auth with the `Authorization: Bearer`
header (prefer it over `?api_key=`, which can leak into logs).

> This is different from **Floe telephony** (`telephony.md`), where Floe owns the phone
> number and runs the voice loop. Here *you* run LiveKit/Pipecat and route its legs
> through Floe's gateway.

## LangChain / CrewAI

Use an OpenAI-compatible client (as above) for the model, plus the Floe **AgentKit**
action providers for lending + x402 actions:

- TypeScript: `floe-agent` (npm) → `floeActionProvider()`, `x402ActionProvider()`.
- Python: `floe-agentkit-actions` (pip) → `floe_action_provider()`, `x402_action_provider()`.

**CrewAI** (recipe: `crewai-demo/`) — x402 provider for paid tool calls:

```python
from floe_agentkit_actions.x402_action_provider import x402_action_provider, X402Config
x402_action_provider(X402Config(
    facilitator_url="https://credit-api.floelabs.xyz",
    facilitator_api_key=FLOE_API_KEY,
    agent_name="procurement",
))
# env: FLOE_API_BASE_URL=https://credit-api.floelabs.xyz · FLOE_LLM_MODEL=openai/gpt-4o · CHAIN_ID=8453
```

**LangChain** (recipe: `langchain-agent/`) — AgentKit tools:

```python
from coinbase_agentkit import AgentKit, AgentKitConfig
from coinbase_agentkit_langchain import get_langchain_tools
agentkit = AgentKit(AgentKitConfig(wallet_provider=wp, action_providers=[floe_action_provider()]))
tools = get_langchain_tools(agentkit)
```

## MCP (Claude Code, Cursor, claude.ai)

Hosted at `https://mcp.floelabs.xyz/mcp` (streamable-HTTP; 65 tools). Add to Claude Code:

```
claude mcp add --transport http floe https://mcp.floelabs.xyz/mcp \
  --header "Authorization: Bearer floe_YOUR_KEY"
```

Budget-relevant tools: `get_credit_remaining`, `get_spend_limit`, `set_spend_limit`,
`estimate_x402_cost`, `x402_forecast`, `x402_pay`, `get_balances`, `get_activity`,
`search_floe_docs`. The companion `floe-budget` skill is a spend playbook for these.

## Managed voice platforms (Vapi / Retell / Bland)

Adopt Floe *inside* the platform — no migration. Three layered mechanisms: the **model
leg** pre-call via custom-LLM (Vapi URL swap; Retell WS adapter; Bland is enterprise-only
— skip), **admission** to refuse an over-budget call before it connects (Vapi
assistant-request, Retell `call_inbound`, Bland Pathway Webhook node → End Call on a
non-`200`), and **Reconcile Mode** for the rest (point the end-of-call webhook at Floe →
whole-call spend on the ledger, enforced next session, `suspend_agent` trips the breaker).
Coverage is **partial** — STT/TTS/telephony reconcile — so state the coverage % and, for
100%, graduate onto a self-hosted stack. Full per-platform mechanics + endpoints:
`orchestrator-governance.md`.

## Every integration, same three habits

1. `base_url` → `https://credit-api.floelabs.xyz/v1`, key → `floe_…`, `max_retries=0`.
2. Set a server cap (`PUT /v1/agents/spend-limit`) before the first run.
3. Wrap the loop with `floe-guard` and show the per-call receipt (`X-Floe-Cost-USDC`).
