# May

May is a multi-agent AI assistant. You give it a command — an **Orchestrator**
agent figures out what kind of task it is and hands it off to a specialized
**worker agent**, which does the work and reports back. Every decision and
tool call is logged to a database, so nothing May does is a black box.

May now has five worker agents — Research, Writer, Email, Code, and Monitor —
and the Orchestrator routes your command to whichever one fits, based on what
you're asking for. You can speak your commands instead of typing them
(local, free Whisper transcription), and as of v3, May speaks her answers
back to you too (local, free text-to-speech). A live dashboard and wake-word
activation are coming in later versions — see [Version History](#version-history).

## Architecture

```
                    ┌────────────────┐
  you speak (or  ──►│  Whisper (local)│──► transcribed text
  type) a command    └────────┬────────┘
                             ▼
                    ┌────────────────┐
                    │  Orchestrator   │
                    │ (Groq/LLaMA 3)  │
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
                    result printed AND spoken back to you
                       (pyttsx3, local text-to-speech)

              All decisions/tool calls ──► PostgreSQL (agent_logs table)
```

**Agent summary:**
- **Research** — searches the web, summarizes findings
- **Writer** — writes documents/reports, saves to `output/documents/`
- **Email** — drafts subject + body, saves to `output/drafts/` (does not send/read real email)
- **Code** — writes Python, runs it in a subprocess with a 10s timeout, returns output
- **Monitor** — checks for recent news/developments on a topic, on demand (not continuous background watching yet)

## Tech stack

| Layer            | Technology                     |
|-------------------|--------------------------------|
| Orchestrator brain | Groq API + LLaMA 3             |
| Worker agents      | Groq API + LLaMA 3             |
| Web search tool    | Tavily                         |
| Speech-to-text     | Whisper (faster-whisper, local) |
| Text-to-speech     | macOS `say` command (built-in, local) |
| Logging / memory   | PostgreSQL                     |
| Containerization   | Docker Compose                 |
| Language           | Python 3.12                    |

## Setup

**Note on running mode:** as of v2, May runs **natively** on your Mac (not
fully inside Docker) so she can access your microphone — Docker Desktop on
macOS can't reliably forward audio devices into a container. PostgreSQL still
runs in Docker.

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
4. Start just the database:
   ```
   docker compose up -d db
   ```
5. Set up a local Python environment and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
6. Run May:
   ```
   python main.py
   ```
   The first run downloads the Whisper "tiny" model (~75MB) once — it's
   cached after that.
7. Press Enter, speak a command, press Enter again when done — May will
   print AND speak her answer back to you. Try any of these:
   - `what are the latest developments in AI agents` → Research
   - `write me a short report on the benefits of Docker` → Writer
   - `draft an email asking my manager for a day off next Friday` → Email
   - `write and run a script that prints the first 10 fibonacci numbers` → Code
   - `check for recent news on OpenAI` → Monitor

   Say (or type, if `INPUT_MODE=text`) `exit` to quit.

**Prefer typing/reading only, or running fully in Docker without a mic?** Set
`INPUT_MODE=text` and/or `OUTPUT_MODE=text` in `.env` independently — e.g.
type your commands but still hear May's replies, or vice versa. For fully
Docker-based text mode via `docker compose up app`, also set
`POSTGRES_HOST=db` and `POSTGRES_PORT=5432` first (see the comments in
`.env.example`).

## Version history

| Version | What it added |
|---------|----------------|
| v0      | Text-only orchestrator + Research Agent, PostgreSQL logging, Docker Compose |
| v1      | Writer, Email, Code, and Monitor agents; Orchestrator routes across all 5; `tools/file_manager.py` |
| v2      | Voice input via local Whisper; runs natively for mic access, Postgres stays in Docker |
| v3      | Voice output via pyttsx3; May speaks her responses back to you |

## Project structure

```
may/
├── agents/          # orchestrator + worker agent logic
├── tools/           # functions agents use to act (web search, ...)
├── memory/          # PostgreSQL logging
├── voice/           # speech-to-text (v2) / text-to-speech (v3)
├── frontend/        # React dashboard (added in v4)
├── main.py          # entry point
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
