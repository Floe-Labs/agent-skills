# Floe agent skills

Agent skills for [**Floe**](https://floelabs.xyz) — spend controls for Voice AI.
One `floe_` key for LLM, STT, TTS, telephony, search, and data APIs, with per-call
cost attribution and spend limits that bind **before** money moves.

This repo is the canonical home for Floe's agent skills. Today it ships one:

| Skill | What it does |
|---|---|
| [`skills/floe`](skills/floe/SKILL.md) | Give any agent metered, budget-capped multi-vendor API access through one Floe key. Onboarding, migration, spend policies, voice-orchestrator governance (Vapi/Retell/Bland + self-hosted 100% coverage), telephony, framework integrations, and runtime budgeting. |

Works with Claude Code, the Claude Agent SDK, Cursor, and any client that loads
[Agent Skills](https://www.anthropic.com/news/skills).

## Start building with Floe

One key for your agent's whole vendor bill — LLM, voice, telephony, search, data — metered per call and budget-capped. Let your coding agent set it up, or wire it yourself:

| Path | One line |
|---|---|
| **Agent** — Claude Code / Cursor does the setup | paste: `Read https://dev-dashboard.floelabs.xyz/agents.md and set up Floe for this project.` |
| **Skill** — install the Floe agent skill | `npx skills add floe-labs/agent-skills` |
| **MCP** — hosted MCP server (65 tools) | `npx -y add-mcp https://mcp.floelabs.xyz/mcp` |
| **NPM** — the CLI + SDK | `npm i -g floe-agent` |

New accounts get a **$3 Welcome Credit (300 API credits)** — no card. [Set up with your AI tools →](https://floe-labs.gitbook.io/docs/getting-started/setup-with-ai-tools) · [Get a key →](https://dev-dashboard.floelabs.xyz)

## Install

**skills.sh CLI** (recommended):

```bash
npx skills add floe-labs/agent-skills
```

**Manual — global** (available in every project):

```bash
git clone https://github.com/floe-labs/agent-skills
cp -r agent-skills/skills/floe ~/.claude/skills/
```

**Manual — per-project** (checked into one repo):

```bash
git clone https://github.com/floe-labs/agent-skills
cp -r agent-skills/skills/floe .claude/skills/
```

Pin to a release for reproducibility: `npx skills add floe-labs/agent-skills@v1.0.0`
(see [Releases](https://github.com/floe-labs/agent-skills/releases)).

## What it does

The skill teaches an agent to run the whole vendor stack on one key and **show the
receipt** after every session — real cost per leg, real budget remaining:

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

<!-- TODO(launch): replace the block above with a 30s GIF of the receipt output in a
     real Claude Code session (docs/receipt.gif). This is the hero asset. -->

Budgets are enforced server-side before each call (a breach returns `402`, or a
kill-switch policy `suspend`s the agent) and the agent can taper gracefully with the
local [`floe-guard`](https://github.com/Floe-Labs/floe-guard) guardrail
(`pip install floe-guard` / `npm i floe-guard`) before it ever hits that floor —
the in-process, client-side complement to this skill's server-side controls. See
[`skills/floe/SKILL.md`](skills/floe/SKILL.md) and its
[`references/`](skills/floe/references/).

## Get a key

Sign up at **[floelabs.xyz/signup?src=skill](https://floelabs.xyz/signup?src=skill)** —
email only, no card. New accounts get a **$3 USDC welcome credit (~300 calls)** to run
the skill end-to-end immediately.

<!-- TODO(launch): the ?src=skill attribution param is NOT captured by the signup flow
     today (no attribution handler exists in the app). Wire it on the marketing/signup
     side before launch, or the skill-install cohort can't be measured. -->

## More

- **Cookbook** — runnable example agents (voice, x402, LangChain, CrewAI):
  [github.com/Floe-Labs/floe-cookbook](https://github.com/Floe-Labs/floe-cookbook)
- **Docs** — [floe-labs.gitbook.io/docs](https://floe-labs.gitbook.io/docs)
- **MCP server** — hosted at `https://mcp.floelabs.xyz/mcp` (65 tools)

## Contributing

New skills and fixes welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Each skill lives
in `skills/<name>/SKILL.md` with a valid frontmatter `name` + `description` and any
supporting files under `skills/<name>/references/`.

## License

[MIT](LICENSE) © Floe Labs.
