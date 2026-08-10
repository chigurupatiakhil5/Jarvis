# May

May is a multi-agent AI assistant. You give it a command — an **Orchestrator**
agent figures out what kind of task it is and hands it off to a specialized
**worker agent**, which does the work and reports back. Every decision and
tool call is logged to a database, so nothing May does is a black box.

Right now (v0), May can only research things on the web for you. More worker
agents, voice input/output, a live dashboard, and wake-word activation are
coming in later versions — see [Version History](#version-history).

## Architecture

```
                    ┌────────────────┐
   you type a   ──► │  Orchestrator   │
   command          │ (Groq/LLaMA 3)  │
                    └────────┬────────┘
                             │ decides which agent + logs the decision
                             ▼
                    ┌────────────────┐        ┌─────────────────┐
                    │ Research Agent │ ──────► │  web_search tool │
                    │ (Groq/LLaMA 3) │ ◄────── │    (Tavily)      │
                    └────────┬────────┘        └─────────────────┘
                             │ summarizes results + logs
                             ▼
                    result printed back to you

              All decisions/tool calls ──► PostgreSQL (agent_logs table)
```

## Tech stack

| Layer            | Technology                     | Cost |
|-------------------|--------------------------------|------|
| Orchestrator brain | Groq API + LLaMA 3             | Free tier |
| Worker agents      | Groq API + LLaMA 3             | Free tier |
| Web search tool    | Tavily                         | Free tier (1,000 searches/mo) |
| Logging / memory   | PostgreSQL                     | Free (self-hosted) |
| Containerization   | Docker Compose                 | Free |
| Language           | Python 3.12                    | Free |

## Setup

1. Copy the environment template and fill in your keys:
   ```
   cp .env.example .env
   ```
2. Get a free Groq API key: go to [console.groq.com](https://console.groq.com),
   sign up, open **API Keys**, click **Create API Key**, and paste it into
   `.env` as `GROQ_API_KEY`.
3. Get a free Tavily API key: go to [tavily.com](https://tavily.com), sign up,
   copy your API key from the dashboard, and paste it into `.env` as
   `TAVILY_API_KEY`.
4. Start everything with Docker Compose:
   ```
   docker compose up --build
   ```
5. Once you see `May is ready.`, attach to the running container to type
   commands:
   ```
   docker attach may-app-1
   ```
6. Type a research question, e.g. `what are the latest developments in AI agents`,
   and press enter. Type `exit` to quit.

## Version history

| Version | What it added |
|---------|----------------|
| v0      | Text-only orchestrator + Research Agent, PostgreSQL logging, Docker Compose |

## Project structure

```
may/
├── agents/          # orchestrator + worker agent logic
├── tools/           # functions agents use to act (web search, ...)
├── memory/          # PostgreSQL logging
├── voice/           # speech-to-text / text-to-speech (added in v2/v3)
├── frontend/        # React dashboard (added in v4)
├── main.py          # entry point
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
