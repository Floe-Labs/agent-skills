# Telephony (voice agents)

Twilio-backed (ISV subaccount per developer). **US local numbers and US dial-out
only** — no toll-free, no SMS/10DLC, no non-US dialing, no E911. Every leg (number
rental, per-minute transport, STT, TTS, LLM) meters on the same ledger and budget as
the rest of the stack. Telnyx is **not** in the product; do not reference it.

Auth: developer session or `floe_live_…` key for provisioning/config; the agent's own
`floe_…` key for placing calls. Amounts are atomic USDC (6 decimals).

## 1. Provision a number

```
GET  /v1/numbers/search?areaCode=415        // preview available (optional)
POST /v1/numbers            body { areaCode?: "415", phoneNumber?: "+14155550123" }
     // developer surface: POST /v1/developer/agents/:agentId/numbers  (identical billing)
```

- `areaCode` — 3-digit US NANP (first digit 2–9); omit for any US local number.
- `phoneNumber` — exact E.164 from a prior search; takes precedence over `areaCode`.

Response `201`:

```jsonc
{ "number": { "id": 42, "phoneNumber": "+14155550123", "status": "active",
              "monthlyRentalRaw": "2000000", "nextRenewalAt": "...",
              "graceUntil": null, "createdAt": "..." } }
```

One live number per agent (buying a second returns `409 number_exists`). Release:
`DELETE /v1/developer/agents/:agentId/numbers/:numberId` (idempotent).

## 2. Voice config — hosted vs webhook

```
GET   /v1/developer/agents/:agentId/voice
PATCH /v1/developer/agents/:agentId/voice
  body {
    voiceMode?: "hosted" | "webhook",
    systemPrompt?: string(≤4000),   // hosted mode
    beginMessage?: string(≤500),    // opening line spoken to the caller
    voice?: string(≤120),           // e.g. "nova"
    model?: string(≤120),           // e.g. "openai/gpt-5.4-mini" (hosted default)
    webhookUrl?: string(≤500, https) // required for webhook mode
  }
```

- **hosted** (default) — Floe runs the entire loop (STT → LLM via the keyless gateway
  → TTS) from `systemPrompt` / `model` / `voice`. No backend of your own.
- **webhook** — Floe runs STT + TTS and POSTs each finished caller turn to `webhookUrl`;
  your backend returns the reply. `webhookUrl` must be set (validation error otherwise).

A PATCH takes effect on the **next** call — no re-provisioning, no downtime.

### Webhook turn contract

Floe POSTs (no auth header — authenticate via a secret in the URL you configure):

```jsonc
{ "type": "agent.message", "channel": "voice", "callId": "CA…",
  "from": "+1…", "to": "+1…", "text": "the caller's transcribed utterance",
  "recentHistory": [ { "role": "user"|"assistant", "content": "…" } ] }  // last ~10 turns
```

Reply with **NDJSON**, one JSON object per line, that Floe speaks:

```
{"text": "Sure — what day works?"}
```

Limits: reply ≤ 1,500 chars, body ≤ 256 KB, default timeout 30 s
(`TELEPHONY_WEBHOOK_TIMEOUT_MS`). Stream interim chunks (`{"text":"…","interim":true}`)
for lower perceived latency; a single final chunk is fine for a demo.

## 3. Place an outbound call (agent key)

```
POST /v1/calls           body { toNumber: "+14155550123" }   // must be +1 (US)
  → 201 { callId, from, to, status: "queued" }
```

Poll status (added recently):

```
GET /v1/calls/:callId    → { callId, status: "pending"|"in_progress"|"completed", terminal }
```

`pending` = queued/ringing/never-answered · `in_progress` = live · `completed` =
ended. Scoped to the calling agent (other agents' calls are invisible). A dialer can
poll `terminal` to place one call at a time.

## 4. Media path

Live voice is **webhook/gateway-based, not SIP**. Inbound: caller → Twilio Programmable
Voice → a Floe media-gateway WebSocket that runs **Deepgram streaming STT**,
**ElevenLabs TTS**, and the **LLM leg** (hosted = keyless gateway; webhook = your
backend). There is no LiveKit/Pipecat SIP trunk — if a user wants LiveKit/Pipecat, they
run that stack themselves and route its LLM/TTS/STT legs through the Floe gateway (see
`frameworks.md`), which is a different integration from Floe telephony.

## 5. Constraints & pricing

- US local numbers + US dial-out only; one live number per agent.
- Per call, Floe reserves an upper bound (default $2.00, `TELEPHONY_CALL_MAX_RESERVE_RAW`),
  meters the live cost, and settles to actual at call end (unused reserve released).

Rack pricing (Twilio + ~5% Floe margin; verify live via `GET /v1/models`):

| Unit | Price |
|---|---|
| Phone number (monthly rental) | ~$2.00 / mo |
| Inbound minute | ~$0.0089 / min |
| Outbound minute (US) | ~$0.0147 / min |
| STT (Deepgram streaming) | ~$0.0045 / audio-second |
| TTS (ElevenLabs) | ~$0.0000525 / character |
| LLM (hosted mode) | metered per turn, same as `/v1/chat/completions` |

A call bills as separate line items (transport, STT, TTS, LLM); zero-usage lines are
skipped. The number renews monthly via a cron debit; nonpayment moves it to `grace`
then `released`.
