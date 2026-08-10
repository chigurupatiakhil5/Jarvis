# May

May is a multi-agent AI assistant. You give it a command — an **Orchestrator**
agent figures out what kind of task it is and hands it off to a specialized
**worker agent**, which does the work and reports back. Every decision and
tool call is logged to a database, so nothing May does is a black box.

May now has five worker agents — Research, Writer, Email, Code, and Monitor —
and the Orchestrator routes your command to whichever one fits, based on what
you're asking for. Voice input/output, a live dashboard, and wake-word
activation are coming in later versions — see [Version History](#version-history).

## Architecture

```
                    ┌────────────────┐
   you type a   ──► │  Orchestrator   │
   command          │ (Groq/LLaMA 3)  │
                    └────────┬────────┘
                             │ picks one agent + logs the decision
                             ▼
        ┌───────────┬────────────┬───────────┬────────────┬────────────┐
        │ Research  │  Writer    │  Email    │   Code      │  Monitor    │
        │  Agent    │  Agent     │  Agent    │   Agent     │  Agent      │
        └─────┬─────┴─────┬──────┴─────┬─────┴──────┬──────┴─────┬──────┘
              │           │            │            │            │
        web_search    file_manager file_manager  file_manager +  web_search
         (Tavily)      (saves doc)  (saves draft)  subprocess     (Tavily,
                                                    (runs code)   news-biased)
              │           │            │            │            │
              ▼           ▼            ▼            ▼            ▼
                    result printed back to you

              All decisions/tool calls ──► PostgreSQL (agent_logs table)
```

**Agent summary:**
- **Research** — searches the web, summarizes findings
- **Writer** — writes documents/reports, saves to `output/documents/`
- **Email** — drafts subject + body, saves to `output/drafts/` (does not send/read real email)
- **Code** — writes Python, runs it in a subprocess with a 10s timeout, returns output
- **Monitor** — checks for recent news/developments on a topic, on demand (not continuous background watching yet)

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
6. Type a command — try any of these to see all five agents:
   - `what are the latest developments in AI agents` → Research
   - `write me a short report on the benefits of Docker` → Writer
   - `draft an email asking my manager for a day off next Friday` → Email
   - `write and run a script that prints the first 10 fibonacci numbers` → Code
   - `check for recent news on OpenAI` → Monitor

   Type `exit` to quit.

## Version history

| Version | What it added |
|---------|----------------|
| v0      | Text-only orchestrator + Research Agent, PostgreSQL logging, Docker Compose |
| v1      | Writer, Email, Code, and Monitor agents; Orchestrator routes across all 5; `tools/file_manager.py` |

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
