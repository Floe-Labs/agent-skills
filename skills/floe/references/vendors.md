# Vendors & catalog

Two surfaces:
1. **Gateway** — first-class, OpenAI-compatible models (LLM, embeddings, TTS, STT,
   realtime) at `https://credit-api.floelabs.xyz/v1`, addressed as `provider/model`.
2. **x402 marketplace** — third-party paid APIs (search, data, compute, voice vendors)
   reached with the same key via `POST /v1/proxy/fetch`.

**The live catalog is `GET /v1/models`** (keyless — call it with your Floe key). Resolve
IDs there at runtime; the lists below are representative, not frozen. IDs are always
fully qualified `provider/model` — a bare name (`gpt-4o`) is rejected.

## Gateway categories (representative IDs)

- **Text / reasoning** — `openai/gpt-4o`, `openai/gpt-4o-mini`, `openai/gpt-5.4-mini`,
  `anthropic/claude-sonnet-4-6`, `anthropic/claude-opus-4-8`, `google/gemini-3.1-pro-preview`,
  `deepseek/deepseek-v4-pro`, `qwen/qwen3.5-397b`, `mistral/mistral-large`,
  `moonshot/kimi-k2.6`, `xai/grok-4.5`, `meta/llama-3.3-70b`, `perplexity/sonar-pro`
  (web search), plus Venice, Sarvam (Indic), Cohere, NVIDIA, MiniMax, Microsoft.
- **Embeddings** — `openai/text-embedding-3-large`, `baai/bge-m3`, `qwen/qwen3-embedding-8b`.
- **TTS** — `openai/tts-1`, `openai/gpt-4o-mini-tts`, `cartesia/sonic-3`, `kokoro/kokoro-82m`,
  `canopy/orpheus-3b`, and more. Endpoint: `POST /v1/audio/speech`.
- **STT** — batch (`POST /v1/audio/transcriptions`): `openai/whisper-1`,
  `openai/gpt-4o-transcribe`, `mistral/voxtral-small`, `nvidia/parakeet-tdt-0.6b-v3`.
  Streaming (`WS /v1/audio/transcriptions/stream`): `deepgram/nova-3`.
- **Realtime (speech-to-speech)** — `WS /v1/realtime?model=…`: `openai/gpt-realtime`,
  `google/gemini-live-3.1`, `xai/grok-voice`. This is speech↔speech, **not** a
  standalone streaming-STT feed (use the STT stream for that).

## Pricing convention

Catalog rates are **cost per 1,000,000 units** (tokens, audio-seconds, characters, or
calls). Cost of a call = `quantity × rate ÷ 1_000_000`. Every metered response returns
the actual charge in `X-Floe-Cost-USDC` (atomic USDC) — trust that over any estimate.
`estimate_x402_cost` / `x402_forecast` (MCP) preflight a cost before you pay.

## BYOK matrix

Send your own provider key as `X-Floe-Provider-Key`; Floe charges its **margin only**.

| Model source | BYOK? |
|---|---|
| Direct-account (OpenAI, Anthropic, Google, xAI, Mistral, Cohere, DeepSeek, …) | ✅ |
| Self-hosted (DeepInfra, Together, Groq) | ✅ (supply the host's key) |
| x402-router (keyless pay-per-call upstream) | ❌ Floe signs the payment |
| Pooled-wallet rails (e.g. Venice) | ❌ Floe holds the account |
| Free tier | ❌ implicit Floe credential |

## Automatic fallback

For models with **more than one source**, the gateway fails over automatically,
cheapest-source-first: a network error, upstream **5xx**, or **429** rolls to the next
source; a deterministic **4xx** is passed through unchanged (no retry); a 2xx wins.
This is automatic and **not** policy-controlled. Single-source models have no fallback.
Multi-source examples: `deepseek/deepseek-v4-pro` (DeepInfra + Together),
`openai/gpt-oss-120b` (DeepInfra + Groq + Together), `meta/llama-3.3-70b`
(DeepInfra + Together). For streaming, fallback stops once the first byte flows.

## x402 marketplace (via `/v1/proxy/fetch`)

Third-party paid APIs payable in USDC with the same key — search, data, compute, image,
and voice vendors (e.g. Venice image/TTS, Sarvam voice/language, dTelecom/GEDX402/Spraay
voice). The agent POSTs the target request to `/v1/proxy/fetch`; Floe pays the vendor
(x402/EIP-3009), meters it on your ledger, and returns the response — no vendor account.
The machine-readable directory is served from the docs (`x402-directory/directory.json`).
Anything not on the gateway or in the marketplace stays on the vendor's own key and is an
**unmetered gap** in attribution — call that out.
